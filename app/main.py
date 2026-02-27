import os
import re
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles

from app.models import (
    RenderRequest,
    RenderRequestWrapped,
    RenderResponse,
    TemplatesResponse,
    UploadCoverResponse,
)
from app.renderer import render_typst, list_templates

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
ASSETS_DIR = BASE_DIR / "assets"

app = FastAPI(title="Typst Renderer API", version="1.3.0")

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
async def upload_cover(file: UploadFile = File(...)):
    """
    Upload de capa (PNG/JPG/WEBP). Salva em /assets e retorna cover_image_url pública.
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Arquivo sem filename")

        ext = (Path(file.filename).suffix or "").lower()
        if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
            raise HTTPException(status_code=400, detail="Formato inválido. Use png/jpg/jpeg/webp.")

        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        safe_original = _safe_name(Path(file.filename).stem)
        filename = f"cover_{safe_original}_{ts}{ext}"

        out_path = ASSETS_DIR / filename
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Arquivo vazio")

        out_path.write_bytes(content)

        return UploadCoverResponse(
            success=True,
            cover_image_url=_public_asset_url(filename),
            filename=filename,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha no upload: {e}")


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