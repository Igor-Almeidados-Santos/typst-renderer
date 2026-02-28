from typing import Any, List, Optional
from pydantic import BaseModel, Field


class RenderOptions(BaseModel):
    paper_size: str = Field(default="A4")
    pdf_standard: Optional[str] = Field(default=None)


class RenderRequest(BaseModel):
    template_id: str = Field(..., examples=["livro_tecnico_v2"])
    document: dict[str, Any]
    options: Optional[RenderOptions] = None


class RenderWrappedPayload(BaseModel):
    document: dict[str, Any]
    options: Optional[RenderOptions] = None


class RenderRequestWrapped(BaseModel):
    template_id: str = Field(..., examples=["livro_tecnico_v2"])
    payload: RenderWrappedPayload


class RenderResponse(BaseModel):
    success: bool
    file_url: str
    warnings: List[str] = []


class TemplatesResponse(BaseModel):
    templates: List[str]
    default: str


class UploadCoverResponse(BaseModel):
    success: bool
    cover_image_url: str
    filename: str


class OpenAIFileRef(BaseModel):
    name: str
    id: str
    mime_type: str
    download_link: str


class UploadCoverOpenAIRequest(BaseModel):
    openaiFileIdRefs: List[OpenAIFileRef] = Field(default_factory=list)


class BrandPalette(BaseModel):
    brand_primary: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    brand_secondary: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    brand_accent: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    brand_ink: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    brand_muted: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    brand_line: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    brand_tint: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")


class Typography(BaseModel):
    font_title: str
    font_body: str
    font_mono: str


class GenerateCoverImageRequest(BaseModel):
    book_title: str
    subtitle: Optional[str] = None
    visual_concept: str
    illustration_brief: str
    palette: BrandPalette
    typography: Typography
    style_keywords: List[str] = Field(default_factory=list)
    aspect_ratio: str = Field(default="2:3", pattern=r"^\d+:\d+$")
    output_format: str = Field(default="png")
    render_text_in_image: bool = Field(default=False)
    safe_mode: bool = Field(default=True)


class GenerateCoverImageResponse(BaseModel):
    success: bool
    image_url: str
    mime_type: str
    prompt_used: str
