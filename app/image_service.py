from app.image_provider import (
    LocalProceduralCoverImageProvider,
    build_cover_image_provider,
)
from app.models import GenerateCoverImageRequest


def generate_cover_image_asset(req: GenerateCoverImageRequest) -> tuple[bytes, str, str]:
    prompt_used = build_cover_prompt(req)
    provider = build_cover_image_provider()

    try:
        content, mime_type = provider.generate(req, prompt_used)
        return content, mime_type, prompt_used
    except Exception as exc:
        if isinstance(provider, LocalProceduralCoverImageProvider):
            raise

        fallback_provider = LocalProceduralCoverImageProvider()
        content, mime_type = fallback_provider.generate(req, prompt_used)
        prompt_with_fallback = (
            f"{prompt_used} Provider fallback: local procedural renderer after remote failure: {exc}."
        )
        return content, mime_type, prompt_with_fallback


def build_cover_prompt(req: GenerateCoverImageRequest) -> str:
    keywords = ", ".join(req.style_keywords) if req.style_keywords else "editorial, clean, professional"
    return (
        "Create a professional book cover background illustration only. "
        "No title text, no subtitles, no letters, no logos, no UI, no device mockups. "
        f"Style: {req.visual_concept}. "
        f"Illustration: {req.illustration_brief}. "
        f"Palette: primary {req.palette.brand_primary}, secondary {req.palette.brand_secondary}, "
        f"accent {req.palette.brand_accent}, ink {req.palette.brand_ink}, muted {req.palette.brand_muted}, "
        f"line {req.palette.brand_line}, tint {req.palette.brand_tint}. "
        f"Keywords: {keywords}. "
        f"Aspect ratio: {req.aspect_ratio}. "
        "High quality, editorial, clean composition, suitable as a full-page book cover background."
    )
