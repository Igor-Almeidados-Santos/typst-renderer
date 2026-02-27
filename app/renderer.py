import base64
import json
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
JOBS_DIR = BASE_DIR / "jobs"
STORAGE_DIR = BASE_DIR / "storage"


def ensure_dirs() -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def list_templates() -> list[str]:
    if not TEMPLATES_DIR.exists():
        return []
    return sorted([p.name for p in TEMPLATES_DIR.iterdir() if p.is_dir()])


def _validate_document(doc: dict[str, Any]) -> list[str]:
    warnings: list[str] = []

    metadata = doc.get("metadata", {})
    content = doc.get("content", [])

    if not isinstance(metadata, dict):
        warnings.append("metadata inválido (não é objeto)")
        return warnings

    if not metadata.get("title") and not metadata.get("book_title"):
        warnings.append("metadata.title e metadata.book_title ausentes (um deles é recomendado)")
    if not metadata.get("author"):
        warnings.append("metadata.author ausente")
    if not isinstance(content, list):
        warnings.append("content inválido (não é lista)")

    for i, block in enumerate(content if isinstance(content, list) else []):
        if isinstance(block, dict) and block.get("type") == "table":
            cols = block.get("columns", [])
            rows = block.get("rows", [])
            if not cols:
                warnings.append(f"table[{i}] sem columns")
            for r_idx, row in enumerate(rows):
                if len(row) != len(cols):
                    warnings.append(
                        f"table[{i}] row[{r_idx}] tem {len(row)} colunas, esperado {len(cols)}"
                    )
    return warnings


def _write_cover_image(job_dir: Path, document: dict[str, Any]) -> list[str]:
    """
    Suporta:
      - metadata.cover_image_base64
      - metadata.cover_image_url (http/https)
    Salva a capa como cover.(png|jpg|jpeg|webp) no job_dir e injeta metadata.cover_image_path
    """
    warnings: list[str] = []
    meta = document.get("metadata", {}) if isinstance(document, dict) else {}
    if not isinstance(meta, dict):
        return warnings

    b64 = meta.get("cover_image_base64")
    url = meta.get("cover_image_url")

    # default
    out_path = job_dir / "cover.png"

    if b64:
        try:
            s = b64.strip()
            if "base64," in s:
                s = s.split("base64,", 1)[1]
            data = base64.b64decode(s, validate=False)
            out_path.write_bytes(data)
            meta["cover_image_path"] = out_path.name
        except Exception as e:
            warnings.append(f"Falha ao decodificar cover_image_base64: {e}")

    elif url:
        try:
            req = Request(url, headers={"User-Agent": "typst-renderer/1.0"})
            with urlopen(req, timeout=25) as resp:
                data = resp.read()
                ctype = (resp.headers.get("Content-Type") or "").lower()

            # tenta escolher extensão pelo content-type
            if "jpeg" in ctype or "jpg" in ctype:
                out_path = job_dir / "cover.jpg"
            elif "webp" in ctype:
                out_path = job_dir / "cover.webp"
            else:
                out_path = job_dir / "cover.png"

            out_path.write_bytes(data)
            meta["cover_image_path"] = out_path.name
        except Exception as e:
            warnings.append(f"Falha ao baixar cover_image_url: {e}")

    document["metadata"] = meta
    return warnings


def render_typst(template_id: str, document: dict[str, Any], pdf_standard: str | None = None) -> tuple[str, list[str]]:
    ensure_dirs()

    template_dir = TEMPLATES_DIR / template_id
    if not template_dir.exists():
        raise FileNotFoundError(f"Template não encontrado: {template_id}")

    warnings = _validate_document(document)

    job_id = uuid.uuid4().hex
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Copia template
    for item in template_dir.iterdir():
        target = job_dir / item.name
        if item.is_file():
            shutil.copy2(item, target)

    # Escreve capa (se enviada) antes de salvar input.json
    warnings.extend(_write_cover_image(job_dir, document))

    # Salva input.json
    input_json_path = job_dir / "input.json"
    input_json_path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")

    # Renderiza
    output_pdf_path = job_dir / "output.pdf"
    main_typ_path = job_dir / "main.typ"

    cmd = ["typst", "compile", str(main_typ_path), str(output_pdf_path)]
    if pdf_standard:
        cmd.extend(["--pdf-standard", pdf_standard])

    result = subprocess.run(
        cmd,
        cwd=job_dir,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        raise RuntimeError(f"Erro no Typst:\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}")

    final_name = f"{job_id}.pdf"
    final_path = STORAGE_DIR / final_name
    shutil.copy2(output_pdf_path, final_path)

    return final_name, warnings