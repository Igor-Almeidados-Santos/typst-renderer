import os
import re
from pathlib import Path
from datetime import datetime
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles

from app.models import (
    GenerateCoverImageRequest,
    GenerateCoverImageResponse,
    UploadCoverOpenAIRequest,
    RenderRequest,
    RenderRequestWrapped,
    RenderResponse,
    TemplatesResponse,
    UploadCoverResponse,
)
from app.image_service import generate_cover_image_asset
from app.renderer import render_typst, list_templates

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
ASSETS_DIR = BASE_DIR / "assets"

app = FastAPI(title="Typst Renderer API", version="2.0.0")

STORAGE_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/files", StaticFiles(directory=STORAGE_DIR), name="files")
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


@app.get("/health")
def health():
    return {"status": "ok"}


def _public_base() -> str:
    return os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _public_file_url(file_name: str) -> str:
    return f"{_public_base()}/files/{file_name}"


def _public_asset_url(filename: str) -> str:
    return f"{_public_base()}/assets/{filename}"


def _safe_name(name: str) -> str:
    name = name.strip().replace(" ", "-")
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    return name or "cover.png"


def _pick_upload_file(*candidates: UploadFile | None) -> UploadFile:
    for candidate in candidates:
        if candidate is not None:
            return candidate

    raise HTTPException(
        status_code=400,
        detail="Nenhum arquivo enviado. Use multipart/form-data com um dos campos: file, cover, image ou arquivo.",
    )


def _cover_extension_from_name_or_type(name: str | None, content_type: str | None) -> str:
    ext = (Path(name or "").suffix or "").lower()
    if ext in [".png", ".jpg", ".jpeg", ".webp"]:
        return ext

    value = (content_type or "").lower()
    if "jpeg" in value or "jpg" in value:
        return ".jpg"
    if "png" in value:
        return ".png"
    if "webp" in value:
        return ".webp"
    return ".png"


def _store_cover_bytes(content: bytes, original_name: str, content_type: str | None = None) -> UploadCoverResponse:
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    ext = _cover_extension_from_name_or_type(original_name, content_type)
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        raise HTTPException(status_code=400, detail="Formato inválido. Use png/jpg/jpeg/webp.")

    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    safe_original = _safe_name(Path(original_name).stem or "cover")
    filename = f"cover_{safe_original}_{ts}{ext}"

    out_path = ASSETS_DIR / filename
    out_path.write_bytes(content)

    return UploadCoverResponse(
        success=True,
        cover_image_url=_public_asset_url(filename),
        filename=filename,
    )


@app.get("/templates", response_model=TemplatesResponse)
def get_templates():
    templates = list_templates()
    if "livro_tecnico_v2" in templates:
        default = "livro_tecnico_v2"
    elif "livro_tecnico_v1" in templates:
        default = "livro_tecnico_v1"
    else:
        default = templates[0] if templates else ""
    return TemplatesResponse(templates=templates, default=default)


@app.post("/upload-cover", response_model=UploadCoverResponse)
async def upload_cover(
    file: UploadFile | None = File(default=None),
    cover: UploadFile | None = File(default=None),
    image: UploadFile | None = File(default=None),
    arquivo: UploadFile | None = File(default=None),
):
    """
    Upload de capa (PNG/JPG/WEBP). Salva em /assets e retorna cover_image_url pública.
    """
    try:
        upload = _pick_upload_file(file, cover, image, arquivo)

        if not upload.filename:
            raise HTTPException(status_code=400, detail="Arquivo sem filename")
        content = await upload.read()
        return _store_cover_bytes(content, upload.filename, upload.content_type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha no upload: {e}")


@app.post("/upload-cover-openai", response_model=UploadCoverResponse)
async def upload_cover_openai(req: UploadCoverOpenAIRequest):
    """
    Upload de capa a partir de openaiFileIdRefs enviados pelo ChatGPT Actions.
    """
    try:
        if not req.openaiFileIdRefs:
            raise HTTPException(
                status_code=400,
                detail=(
                    "openaiFileIdRefs veio vazio. Chame este endpoint apenas quando houver uma imagem "
                    "real anexada pela conversa e envie essa imagem no parametro openaiFileIdRefs."
                ),
            )

        image_ref = next(
            (
                item
                for item in req.openaiFileIdRefs
                if item.mime_type.lower() in ["image/png", "image/jpeg", "image/jpg", "image/webp"]
            ),
            None,
        )
        if image_ref is None:
            raise HTTPException(status_code=400, detail="Nenhuma imagem válida em openaiFileIdRefs.")

        remote_name = image_ref.name or "cover"
        req_remote = Request(image_ref.download_link, headers={"User-Agent": "typst-renderer/1.0"})
        with urlopen(req_remote, timeout=25) as resp:
            content = resp.read()
            content_type = resp.headers.get("Content-Type") or image_ref.mime_type

        return _store_cover_bytes(content, remote_name, content_type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha no upload via openaiFileIdRefs: {e}")


@app.post("/generate-cover-image", response_model=GenerateCoverImageResponse)
def generate_cover_image(req: GenerateCoverImageRequest):
    try:
        if req.output_format.lower() not in ["png", "jpg", "jpeg", "webp"]:
            raise HTTPException(status_code=400, detail="output_format invalido. Use png, jpg, jpeg ou webp.")

        content, mime_type, prompt_used = generate_cover_image_asset(req)
        stored = _store_cover_bytes(
            content,
            f"generated-{_safe_name(req.book_title)}",
            mime_type,
        )

        return GenerateCoverImageResponse(
            success=True,
            image_url=stored.cover_image_url,
            mime_type=mime_type,
            prompt_used=prompt_used,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao gerar imagem: {e}")


@app.post("/render-pdf", response_model=RenderResponse)
def render_pdf(payload: RenderRequest):
    try:
        pdf_standard = payload.options.pdf_standard if payload.options else None
        file_name, warnings = render_typst(payload.template_id, payload.document, pdf_standard)
        return RenderResponse(success=True, file_url=_public_file_url(file_name), warnings=warnings)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/render-pdf-wrapped", response_model=RenderResponse)
def render_pdf_wrapped(req: RenderRequestWrapped):
    try:
        pdf_standard = req.payload.options.pdf_standard if req.payload.options else None
        file_name, warnings = render_typst(req.template_id, req.payload.document, pdf_standard)
        return RenderResponse(success=True, file_url=_public_file_url(file_name), warnings=warnings)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
