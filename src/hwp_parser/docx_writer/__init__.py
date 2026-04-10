"""DOCX writer helpers for IR v1."""

from .image_resolver import ImageResolutionContext, resolve_image_path
from .write import write_docx, write_docx_from_ir_json

__all__ = [
    "ImageResolutionContext",
    "resolve_image_path",
    "write_docx",
    "write_docx_from_ir_json",
]
