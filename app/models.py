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