from __future__ import annotations

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from hwp_parser.ir.models import CharacterStyle, Paragraph, ParagraphStyle


def map_alignment(style: ParagraphStyle) -> WD_ALIGN_PARAGRAPH | None:
    alignment = style.alignment
    if alignment == "left":
        return WD_ALIGN_PARAGRAPH.LEFT
    if alignment == "center":
        return WD_ALIGN_PARAGRAPH.CENTER
    if alignment == "right":
        return WD_ALIGN_PARAGRAPH.RIGHT
    if alignment == "justify":
        return WD_ALIGN_PARAGRAPH.JUSTIFY
    return None


def apply_character_style(run: object, style: CharacterStyle) -> None:
    if style.bold is not None:
        run.bold = style.bold
    if style.font_size_pt is not None:
        run.font.size = Pt(style.font_size_pt)


def map_list_style_name(paragraph: Paragraph) -> str | None:
    list_info = paragraph.list_info
    if list_info is None:
        return None
    if list_info.level not in {None, 0}:
        return None
    if list_info.kind == "numbered":
        return "List Number"
    if list_info.kind == "bulleted":
        return "List Bullet"
    return None
