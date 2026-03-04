import base64
import json
import os
import re
import shutil
import subprocess
import unicodedata
import uuid
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
JOBS_DIR = BASE_DIR / "jobs"
STORAGE_DIR = BASE_DIR / "storage"
SUPPORTED_TEMPLATE_ID = "livro_tecnico_v2"
DEFAULT_TYPST_TIMEOUT_SECONDS = 35
MAX_ERROR_TEXT_CHARS = 4000
HEX_COLOR_RE = re.compile(r"^#?([0-9A-Fa-f]{6})$")

PYTHON_KEYWORDS = {
    "and", "as", "assert", "async", "await", "break", "class", "continue", "def", "del",
    "elif", "else", "except", "False", "finally", "for", "from", "global", "if", "import",
    "in", "is", "lambda", "None", "nonlocal", "not", "or", "pass", "raise", "return",
    "True", "try", "while", "with", "yield", "match", "case",
}
JS_KEYWORDS = {
    "break", "case", "catch", "class", "const", "continue", "debugger", "default", "delete",
    "do", "else", "export", "extends", "false", "finally", "for", "function", "if", "import",
    "in", "instanceof", "let", "new", "null", "return", "super", "switch", "this", "throw",
    "true", "try", "typeof", "var", "void", "while", "with", "yield", "await", "async",
}


def _lang_family(lang: Any) -> str:
    value = str(lang or "").strip().lower()
    if value in {"py", "python", "python3"}:
        return "python"
    if value in {"js", "javascript", "node", "nodejs", "ts", "typescript", "tsx", "jsx"}:
        return "javascript"
    return "generic"


def _token_regex_for_lang(lang_family: str) -> re.Pattern[str]:
    if lang_family == "python":
        keywords = "|".join(sorted(re.escape(k) for k in PYTHON_KEYWORDS))
        return re.compile(
            rf"""
            (?P<string>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)
            |(?P<comment>\#.*$)
            |(?P<number>\b\d+(?:\.\d+)?\b)
            |(?P<keyword>\b(?:{keywords})\b)
            |(?P<function>\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\())
            |(?P<operator>[+\-*/%=<>!&|^~?:]+)
            """,
            re.VERBOSE,
        )

    if lang_family == "javascript":
        keywords = "|".join(sorted(re.escape(k) for k in JS_KEYWORDS))
        return re.compile(
            rf"""
            (?P<string>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)
            |(?P<comment>//.*$)
            |(?P<number>\b\d+(?:\.\d+)?\b)
            |(?P<keyword>\b(?:{keywords})\b)
            |(?P<function>\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\())
            |(?P<operator>[+\-*/%=<>!&|^~?:]+)
            """,
            re.VERBOSE,
        )

    return re.compile(
        r"""
        (?P<string>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)
        |(?P<comment>(//.*$)|(\#.*$))
        |(?P<number>\b\d+(?:\.\d+)?\b)
        |(?P<function>\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\())
        |(?P<operator>[+\-*/%=<>!&|^~?:]+)
        """,
        re.VERBOSE,
    )


def _build_code_segments(lang: Any, content: Any) -> list[list[dict[str, str]]]:
    text = content if isinstance(content, str) else str(content or "")
    lang_family = _lang_family(lang)
    pattern = _token_regex_for_lang(lang_family)

    output: list[list[dict[str, str]]] = []
    for line in text.split("\n"):
        line_segments: list[dict[str, str]] = []
        cursor = 0
        for match in pattern.finditer(line):
            start, end = match.span()
            if start > cursor:
                plain = line[cursor:start]
                if plain:
                    line_segments.append({"kind": "plain", "text": plain})

            kind = match.lastgroup or "plain"
            token_text = match.group(0)
            if token_text:
                line_segments.append({"kind": kind, "text": token_text})
            cursor = end

        if cursor < len(line):
            tail = line[cursor:]
            if tail:
                line_segments.append({"kind": "plain", "text": tail})

        if not line_segments:
            line_segments.append({"kind": "plain", "text": ""})
        output.append(line_segments)

    return output


def _clip_error_text(value: str, limit: int = MAX_ERROR_TEXT_CHARS) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + f"\n... (truncado, total={len(value)} chars)"


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        raw = value.strip()
        if raw.isdigit():
            return int(raw)
    return None


def _safe_pdf_filename_part(value: Any, fallback: str) -> str:
    if not isinstance(value, str):
        value = str(value or "")
    raw = unicodedata.normalize("NFKD", value)
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    raw = re.sub(r'[<>:"/\\|?*]', " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    raw = raw.rstrip(". ")
    return raw if raw else fallback


def _build_pdf_filename(document: dict[str, Any], job_id: str) -> str:
    metadata = document.get("metadata", {}) if isinstance(document, dict) else {}
    if not isinstance(metadata, dict):
        return f"{job_id}.pdf"

    book_title = _safe_pdf_filename_part(
        metadata.get("book_title") or metadata.get("title") or "Livro",
        "Livro",
    )
    mode = str(metadata.get("mode", "")).strip().lower()

    chapter_number = _int_or_none(metadata.get("chapter_number"))
    part_number = _int_or_none(metadata.get("part_number"))

    # Mantem padrao previsivel mesmo para TOC/cover.
    if chapter_number is None:
        chapter_number = 0 if mode in {"toc", "cover"} else 0
    if part_number is None:
        part_number = 0 if mode in {"toc", "cover"} else 0

    return f"{book_title} - Capitulo {chapter_number:02d} - Parte {part_number}.pdf"


def _external_fetch_headers() -> dict[str, str]:
    return {
        "User-Agent": "typst-renderer/1.0",
        "ngrok-skip-browser-warning": "1",
    }


def ensure_dirs() -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def list_templates() -> list[str]:
    if not TEMPLATES_DIR.exists():
        return []

    only = TEMPLATES_DIR / SUPPORTED_TEMPLATE_ID
    return [SUPPORTED_TEMPLATE_ID] if only.exists() and only.is_dir() else []


def _extension_from_content_type(content_type: str | None) -> str | None:
    if not content_type:
        return None

    value = content_type.lower()
    if "jpeg" in value or "jpg" in value:
        return ".jpg"
    if "png" in value:
        return ".png"
    if "webp" in value:
        return ".webp"
    return None


def _extension_from_image_bytes(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    return None


def _pick_cover_extension(data: bytes, content_type: str | None = None) -> str:
    return _extension_from_content_type(content_type) or _extension_from_image_bytes(data) or ".png"


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


def _normalize_font_family(name: Any, fallback: str) -> str:
    if not isinstance(name, str):
        return fallback

    value = name.strip()
    if not value:
        return fallback

    alias = value.casefold()

    sans_aliases = {
        "inter",
        "montserrat",
        "poppins",
        "roboto",
        "open sans",
        "source sans 3",
        "source sans pro",
        "aptos",
        "arial",
        "helvetica",
        "noto sans",
        "lato",
        "nunito",
        "work sans",
        "fira sans",
    }
    serif_aliases = {
        "source serif 4",
        "source serif pro",
        "merriweather",
        "georgia",
        "times new roman",
        "noto serif",
        "pt serif",
        "liberation serif",
    }
    mono_aliases = {
        "jetbrains mono",
        "fira code",
        "cascadia code",
        "consolas",
        "source code pro",
        "ibm plex mono",
        "courier new",
        "noto sans mono",
        "liberation mono",
    }

    if alias in sans_aliases:
        return "New Computer Modern"
    if alias in serif_aliases:
        return "New Computer Modern"
    if alias in mono_aliases:
        return "New Computer Modern"

    return value


def _normalize_visual_metadata(doc: dict[str, Any]) -> None:
    metadata = doc.get("metadata", {})
    if not isinstance(metadata, dict):
        return

    metadata["font_title"] = _normalize_font_family(
        metadata.get("font_title"),
        "New Computer Modern",
    )
    metadata["font_heading"] = _normalize_font_family(
        metadata.get("font_heading", metadata.get("font_title")),
        metadata["font_title"],
    )
    metadata["font_body"] = _normalize_font_family(
        metadata.get("font_body"),
        "New Computer Modern",
    )
    metadata["font_mono"] = _normalize_font_family(
        metadata.get("font_mono"),
        "New Computer Modern",
    )

    doc["metadata"] = metadata


def _hex_to_rgb_triplet(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    match = HEX_COLOR_RE.match(value.strip())
    if not match:
        return value

    hex_part = match.group(1)
    return [
        int(hex_part[0:2], 16),
        int(hex_part[2:4], 16),
        int(hex_part[4:6], 16),
    ]


def _normalize_color_payload(doc: dict[str, Any]) -> None:
    metadata = doc.get("metadata", {})
    if isinstance(metadata, dict):
        metadata_color_keys = [
            "brand_primary",
            "brand_secondary",
            "brand_accent",
            "brand_ink",
            "brand_muted",
            "brand_line",
            "brand_tint",
            "brand_paper",
            "color_body",
            "color_heading",
            "color_heading_muted",
            "color_heading_rule",
            "color_code_bg",
            "color_code_text",
            "color_code_border",
            "color_code_header_bg",
            "color_code_header_text",
            "color_table_header_bg",
            "color_table_header_text",
            "color_table_body_bg",
            "color_table_body_text",
        ]
        for key in metadata_color_keys:
            metadata[key] = _hex_to_rgb_triplet(metadata.get(key))
        doc["metadata"] = metadata

    content = doc.get("content")
    if not isinstance(content, list):
        return

    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "code":
            continue

        for theme_key in ["theme", "tema"]:
            theme_obj = block.get(theme_key)
            if not isinstance(theme_obj, dict):
                continue
            for color_key in [
                "bg",
                "border",
                "header_bg",
                "header_text",
                "text",
                "line_number",
                "keyword",
                "string",
                "comment",
                "number",
                "function",
                "operator",
                "plain",
            ]:
                theme_obj[color_key] = _hex_to_rgb_triplet(theme_obj.get(color_key))


def _normalize_content_blocks(doc: dict[str, Any]) -> None:
    content = doc.get("content")
    if not isinstance(content, list):
        return

    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "code":
            continue

        # Compatibilidade com payloads em PT-BR: aceita "tema" como alias de "theme".
        if "theme" not in block and "tema" in block:
            block["theme"] = block.get("tema")

        if "segments" not in block:
            block["segments"] = _build_code_segments(block.get("lang"), block.get("content", ""))


def _cover_usage_warnings(template_id: str, doc: dict[str, Any]) -> list[str]:
    metadata = doc.get("metadata", {}) if isinstance(doc, dict) else {}
    if not isinstance(metadata, dict):
        return []

    has_cover_image = bool(metadata.get("cover_image_base64") or metadata.get("cover_image_url"))
    if not has_cover_image:
        return []

    if template_id == "livro_tecnico_v2" and metadata.get("mode", "part") != "cover":
        return ["Imagem de capa enviada, mas metadata.mode nao e 'cover'; a imagem nao aparecera nesta renderizacao."]

    return []


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
            content_type = None
            if "base64," in s:
                prefix, s = s.split("base64,", 1)
                if prefix.startswith("data:"):
                    content_type = prefix[5:].split(";", 1)[0].strip().lower()
            data = base64.b64decode(s, validate=False)
            out_path = job_dir / f"cover{_pick_cover_extension(data, content_type)}"
            out_path.write_bytes(data)
            meta["cover_image_path"] = out_path.name
        except Exception as e:
            warnings.append(f"Falha ao decodificar cover_image_base64: {e}")

    elif url:
        try:
            req = Request(url, headers=_external_fetch_headers())
            with urlopen(req, timeout=25) as resp:
                data = resp.read()
                ctype = (resp.headers.get("Content-Type") or "").lower()
            out_path = job_dir / f"cover{_pick_cover_extension(data, ctype)}"

            out_path.write_bytes(data)
            meta["cover_image_path"] = out_path.name
        except Exception as e:
            warnings.append(f"Falha ao baixar cover_image_url: {e}")

    document["metadata"] = meta
    return warnings


def render_typst(template_id: str, document: dict[str, Any], pdf_standard: str | None = None) -> tuple[str, list[str]]:
    ensure_dirs()

    effective_template = SUPPORTED_TEMPLATE_ID
    template_dir = TEMPLATES_DIR / effective_template
    if not template_dir.exists():
        raise FileNotFoundError(f"Template não encontrado: {effective_template}")

    warnings = _validate_document(document)
    if template_id != effective_template:
        warnings.append(
            f"template_id '{template_id}' ignorado; renderizacao forçada para '{effective_template}'."
        )
    warnings.extend(_cover_usage_warnings(effective_template, document))
    _normalize_color_payload(document)
    _normalize_visual_metadata(document)
    _normalize_content_blocks(document)

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

    timeout_seconds = DEFAULT_TYPST_TIMEOUT_SECONDS
    raw_timeout = os.getenv("TYPST_TIMEOUT_SECONDS", "").strip()
    if raw_timeout:
        try:
            timeout_seconds = max(5, int(raw_timeout))
        except ValueError:
            warnings.append(
                f"TYPST_TIMEOUT_SECONDS invalido ('{raw_timeout}'); usando {DEFAULT_TYPST_TIMEOUT_SECONDS}s."
            )

    try:
        result = subprocess.run(
            cmd,
            cwd=job_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            "Timeout no Typst: compilacao excedeu "
            f"{timeout_seconds}s (template={effective_template}, job_id={job_id})."
        ) from e

    if result.returncode != 0:
        stderr = _clip_error_text((result.stderr or "").strip())
        stdout = _clip_error_text((result.stdout or "").strip())
        raise RuntimeError(f"Erro no Typst:\nSTDOUT:\n{stdout}\n\nSTDERR:\n{stderr}")

    final_name = _build_pdf_filename(document, job_id)
    final_path = STORAGE_DIR / final_name
    shutil.copy2(output_pdf_path, final_path)

    return final_name, warnings
