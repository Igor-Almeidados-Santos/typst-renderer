import base64
import hashlib
import json
import os
import random
import struct
import zlib
from typing import Iterable, Protocol
from urllib.request import Request, urlopen

from app.models import GenerateCoverImageRequest


Color = tuple[int, int, int]


class CoverImageProvider(Protocol):
    def generate(self, req: GenerateCoverImageRequest, prompt: str) -> tuple[bytes, str]:
        ...


class LocalProceduralCoverImageProvider:
    def generate(self, req: GenerateCoverImageRequest, prompt: str) -> tuple[bytes, str]:
        width, height = _resolve_dimensions(req.aspect_ratio)
        seed = _seed_from_request(req)
        rng = random.Random(seed)

        primary = _parse_hex_color(req.palette.brand_primary)
        secondary = _parse_hex_color(req.palette.brand_secondary)
        accent = _parse_hex_color(req.palette.brand_accent)
        ink = _parse_hex_color(req.palette.brand_ink)
        muted = _parse_hex_color(req.palette.brand_muted)
        line = _parse_hex_color(req.palette.brand_line)
        tint = _parse_hex_color(req.palette.brand_tint)

        circles = _build_circles(rng, width, height, secondary, tint, accent)
        bands = _build_bands(rng, width, height, secondary, tint)
        stripe_y = int(height * 0.78)
        stripe_h = max(10, height // 120)
        grid_step = max(18, width // 22)

        raw = bytearray()
        width_scale = max(1, width - 1)
        height_scale = max(1, height - 1)

        for y in range(height):
            t_y = y / height_scale
            raw.append(0)
            for x in range(width):
                t_x = x / width_scale
                color = _lerp(primary, ink, min(1.0, 0.18 + 0.82 * t_y))
                color = _lerp(color, secondary, 0.08 + 0.08 * (1.0 - t_y))
                color = _lerp(color, tint, 0.03 * (1.0 - t_x))

                for slope, intercept, thickness, band_color, alpha in bands:
                    distance = abs(y - (slope * x + intercept))
                    if distance < thickness:
                        strength = alpha * (1.0 - distance / thickness)
                        color = _blend(color, band_color, strength)

                for cx, cy, radius_sq, circle_color, alpha in circles:
                    dx = x - cx
                    dy = y - cy
                    dist_sq = dx * dx + dy * dy
                    if dist_sq < radius_sq:
                        strength = alpha * (1.0 - dist_sq / radius_sq)
                        color = _blend(color, circle_color, strength)

                if stripe_y <= y < stripe_y + stripe_h:
                    stripe_strength = 0.82 if y < stripe_y + stripe_h // 2 else 0.64
                    color = _blend(color, accent, stripe_strength)

                if x > width // 2 and x % grid_step == 0:
                    color = _blend(color, line, 0.18)
                elif y % (grid_step * 2) == 0 and x > int(width * 0.58):
                    color = _blend(color, muted, 0.08)

                raw.extend(color)

        return _encode_png(width, height, bytes(raw)), "image/png"


class RemoteHTTPImageProvider:
    def __init__(self, endpoint_url: str, api_key: str | None = None, timeout: int = 45):
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.timeout = timeout

    def generate(self, req: GenerateCoverImageRequest, prompt: str) -> tuple[bytes, str]:
        payload = {
            "prompt": prompt,
            "book_title": req.book_title,
            "subtitle": req.subtitle,
            "visual_concept": req.visual_concept,
            "illustration_brief": req.illustration_brief,
            "palette": req.palette.model_dump(),
            "typography": req.typography.model_dump(),
            "style_keywords": req.style_keywords,
            "aspect_ratio": req.aspect_ratio,
            "output_format": req.output_format,
            "render_text_in_image": req.render_text_in_image,
            "safe_mode": req.safe_mode,
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, image/png, image/jpeg, image/webp",
            "User-Agent": "typst-renderer/1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        request = Request(
            self.endpoint_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        with urlopen(request, timeout=self.timeout) as response:
            content = response.read()
            content_type = (response.headers.get("Content-Type") or "").lower()

        if content_type.startswith("image/"):
            return content, content_type

        data = json.loads(content.decode("utf-8"))
        image_b64 = data.get("image_base64")
        image_url = data.get("image_url")
        mime_type = (data.get("mime_type") or content_type or "image/png").lower()

        if image_b64:
            return _decode_base64_image(image_b64), mime_type

        if image_url:
            fetch_request = Request(image_url, headers={"User-Agent": "typst-renderer/1.0"})
            with urlopen(fetch_request, timeout=self.timeout) as response:
                image_content = response.read()
                remote_type = (response.headers.get("Content-Type") or "").lower()
            return image_content, remote_type or mime_type

        raise RuntimeError("Resposta do provider externo sem image_base64 nem image_url.")


class OpenAIImageAPIProvider:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com",
        model: str = "gpt-image-1",
        timeout: int = 60,
        quality: str = "high",
        background: str = "opaque",
        compression: int | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.quality = quality
        self.background = background
        self.compression = compression

    def generate(self, req: GenerateCoverImageRequest, prompt: str) -> tuple[bytes, str]:
        output_format = _normalize_output_format(req.output_format)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "size": _openai_image_size(req.aspect_ratio),
            "quality": self.quality,
            "output_format": output_format,
            "background": self.background,
        }
        if self.compression is not None and output_format in ["jpeg", "webp"]:
            payload["output_compression"] = self.compression

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "typst-renderer/1.0",
        }

        request = Request(
            f"{self.base_url}/v1/images",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        with urlopen(request, timeout=self.timeout) as response:
            content = response.read()

        data = json.loads(content.decode("utf-8"))
        images = data.get("data") or []
        if not images:
            raise RuntimeError("Resposta da OpenAI sem data.")

        first = images[0]
        image_b64 = first.get("b64_json")
        image_url = first.get("url")

        if image_b64:
            mime_type = _mime_type_from_output_format(output_format)
            return _decode_base64_image(image_b64), mime_type

        if image_url:
            fetch_request = Request(image_url, headers={"User-Agent": "typst-renderer/1.0"})
            with urlopen(fetch_request, timeout=self.timeout) as response:
                image_content = response.read()
                remote_type = (response.headers.get("Content-Type") or "").lower()
            return image_content, remote_type or _mime_type_from_output_format(output_format)

        raise RuntimeError("Resposta da OpenAI sem b64_json nem url.")


def build_cover_image_provider() -> CoverImageProvider:
    provider_kind = (os.getenv("COVER_IMAGE_PROVIDER") or "").strip().lower()
    openai_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if provider_kind == "openai" or (not provider_kind and openai_key):
        if openai_key:
            base_url = (os.getenv("OPENAI_API_BASE_URL") or "https://api.openai.com").strip()
            model = (os.getenv("OPENAI_IMAGE_MODEL") or "gpt-image-1").strip()
            timeout = _provider_timeout("OPENAI_IMAGE_TIMEOUT", default=60)
            quality = _pick_allowed_value(
                os.getenv("OPENAI_IMAGE_QUALITY"),
                allowed={"auto", "low", "medium", "high"},
                default="high",
            )
            background = _pick_allowed_value(
                os.getenv("OPENAI_IMAGE_BACKGROUND"),
                allowed={"auto", "opaque", "transparent"},
                default="opaque",
            )
            compression = _parse_optional_int(os.getenv("OPENAI_IMAGE_COMPRESSION"), minimum=0, maximum=100)
            return OpenAIImageAPIProvider(
                api_key=openai_key,
                base_url=base_url,
                model=model,
                timeout=timeout,
                quality=quality,
                background=background,
                compression=compression,
            )

    endpoint = (os.getenv("COVER_IMAGE_PROVIDER_URL") or "").strip()
    if endpoint and (provider_kind in ["http", "remote"] or provider_kind != "local"):
        api_key = (os.getenv("COVER_IMAGE_PROVIDER_API_KEY") or "").strip() or None
        timeout = _provider_timeout("COVER_IMAGE_PROVIDER_TIMEOUT", default=45)
        return RemoteHTTPImageProvider(endpoint, api_key=api_key, timeout=timeout)

    return LocalProceduralCoverImageProvider()


def _provider_timeout(env_name: str, default: int) -> int:
    raw = (os.getenv(env_name) or "").strip()
    try:
        return max(5, int(raw)) if raw else default
    except ValueError:
        return default


def _pick_allowed_value(value: str | None, allowed: set[str], default: str) -> str:
    normalized = (value or "").strip().lower()
    return normalized if normalized in allowed else default


def _parse_optional_int(value: str | None, minimum: int, maximum: int) -> int | None:
    raw = (value or "").strip()
    if not raw:
        return None

    try:
        parsed = int(raw)
    except ValueError:
        return None

    if parsed < minimum:
        return minimum
    if parsed > maximum:
        return maximum
    return parsed


def _decode_base64_image(value: str) -> bytes:
    clean = value.strip()
    if "base64," in clean:
        clean = clean.split("base64,", 1)[1]
    return base64.b64decode(clean, validate=False)


def _normalize_output_format(value: str) -> str:
    normalized = (value or "png").strip().lower()
    if normalized == "jpg":
        return "jpeg"
    if normalized in ["png", "jpeg", "webp"]:
        return normalized
    return "png"


def _mime_type_from_output_format(value: str) -> str:
    normalized = _normalize_output_format(value)
    if normalized == "jpeg":
        return "image/jpeg"
    if normalized == "webp":
        return "image/webp"
    return "image/png"


def _openai_image_size(aspect_ratio: str) -> str:
    try:
        left, right = aspect_ratio.split(":", 1)
        width_ratio = max(1, int(left))
        height_ratio = max(1, int(right))
    except (AttributeError, ValueError):
        return "1024x1536"

    ratio = width_ratio / height_ratio
    if ratio > 1.15:
        return "1536x1024"
    if ratio < 0.85:
        return "1024x1536"
    return "1024x1024"


def _resolve_dimensions(aspect_ratio: str) -> tuple[int, int]:
    try:
        left, right = aspect_ratio.split(":", 1)
        width_ratio = max(1, int(left))
        height_ratio = max(1, int(right))
    except (AttributeError, ValueError):
        width_ratio = 2
        height_ratio = 3

    target_height = 1200
    target_width = max(400, int(target_height * width_ratio / height_ratio))

    if target_width % 2:
        target_width += 1
    if target_height % 2:
        target_height += 1

    return target_width, target_height


def _seed_from_request(req: GenerateCoverImageRequest) -> int:
    payload = "|".join(
        [
            req.book_title,
            req.subtitle or "",
            req.visual_concept,
            req.illustration_brief,
            req.palette.brand_primary,
            req.palette.brand_secondary,
            req.palette.brand_accent,
            ",".join(req.style_keywords),
        ]
    )
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _parse_hex_color(value: str) -> Color:
    return (int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16))


def _lerp(a: Color, b: Color, t: float) -> Color:
    factor = _clamp(t)
    return (
        _to_byte(a[0] + (b[0] - a[0]) * factor),
        _to_byte(a[1] + (b[1] - a[1]) * factor),
        _to_byte(a[2] + (b[2] - a[2]) * factor),
    )


def _blend(base: Color, overlay: Color, alpha: float) -> Color:
    factor = _clamp(alpha)
    return (
        _to_byte(base[0] * (1.0 - factor) + overlay[0] * factor),
        _to_byte(base[1] * (1.0 - factor) + overlay[1] * factor),
        _to_byte(base[2] * (1.0 - factor) + overlay[2] * factor),
    )


def _clamp(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _to_byte(value: float) -> int:
    if value <= 0:
        return 0
    if value >= 255:
        return 255
    return int(value)


def _build_circles(
    rng: random.Random,
    width: int,
    height: int,
    secondary: Color,
    tint: Color,
    accent: Color,
) -> list[tuple[int, int, int, Color, float]]:
    circles: list[tuple[int, int, int, Color, float]] = []
    palette_cycle: Iterable[tuple[Color, float]] = [
        (secondary, 0.18),
        (tint, 0.12),
        (accent, 0.09),
    ]

    for color, alpha in palette_cycle:
        radius = rng.randint(width // 5, width // 3)
        cx = rng.randint(width // 8, width - width // 8)
        cy = rng.randint(height // 10, height - height // 5)
        circles.append((cx, cy, radius * radius, color, alpha))

    return circles


def _build_bands(
    rng: random.Random,
    width: int,
    height: int,
    secondary: Color,
    tint: Color,
) -> list[tuple[float, float, float, Color, float]]:
    first_slope = 0.55 + rng.random() * 0.25
    second_slope = -0.35 - rng.random() * 0.2
    first_intercept = rng.randint(-height // 8, height // 5)
    second_intercept = rng.randint(height // 3, height - height // 6)

    return [
        (
            first_slope,
            float(first_intercept),
            float(max(22, width // 14)),
            secondary,
            0.28,
        ),
        (
            second_slope,
            float(second_intercept),
            float(max(16, width // 18)),
            tint,
            0.16,
        ),
    ]


def _encode_png(width: int, height: int, raw_rgb: bytes) -> bytes:
    header = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0)
    compressed = zlib.compress(raw_rgb, level=9)
    return b"".join(
        [
            header,
            _png_chunk(b"IHDR", ihdr),
            _png_chunk(b"IDAT", compressed),
            _png_chunk(b"IEND", b""),
        ]
    )


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    body = chunk_type + data
    return (
        struct.pack("!I", len(data))
        + body
        + struct.pack("!I", zlib.crc32(body) & 0xFFFFFFFF)
    )
