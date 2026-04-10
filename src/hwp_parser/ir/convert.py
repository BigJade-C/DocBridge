from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .models import (
    CharacterStyle,
    Document,
    DocumentSection,
    ImageBlock,
    ListInfo,
    Paragraph,
    ParagraphStyle,
    Table,
    TableCell,
    TableRow,
    TextRun,
)


def document_from_style_analysis(data: Mapping[str, Any]) -> Document:
    paragraphs: list[Paragraph] = []
    source_path = _optional_str(data.get("source_path"))

    for paragraph_data in data.get("paragraphs", []):
        text_runs_data = paragraph_data.get("text_runs", [])
        text_runs = [_text_run_from_data(item) for item in text_runs_data]
        if not text_runs and _optional_str(paragraph_data.get("text_decoded")):
            text_runs = [
                TextRun(
                    text=_optional_str(paragraph_data.get("text_decoded")) or "",
                    kind="text",
                    character_style=CharacterStyle(
                        bold=None,
                        font_size_pt=None,
                        style_ref=_optional_int(paragraph_data.get("char_style_ref")),
                    ),
                )
            ]

        paragraph = Paragraph(
            text_runs=text_runs,
            paragraph_style=ParagraphStyle(
                alignment=_optional_str(
                    _mapping(paragraph_data.get("paragraph_style")).get("alignment")
                ),
                style_ref=_style_ref_from_data(paragraph_data),
            ),
            list_info=_list_info_from_data(paragraph_data.get("list_info")),
            is_empty=not any(run.text for run in text_runs),
            paragraph_type=_optional_str(paragraph_data.get("paragraph_type")) or "unknown_paragraph",
            source_path=source_path,
            source_index=_optional_int(paragraph_data.get("index")),
        )
        paragraphs.append(paragraph)

    return Document(
        source_path=source_path,
        blocks=paragraphs,
    )


def document_from_blocks(data: Mapping[str, Any]) -> Document:
    source_path = _optional_str(data.get("source_path"))
    blocks = []
    for block_data in data.get("blocks", []):
        block_type = _optional_str(block_data.get("block_type"))
        if block_type == "paragraph":
            blocks.append(_paragraph_from_block_data(block_data, source_path))
        elif block_type == "table":
            blocks.append(_table_from_block_data(block_data, source_path))
        elif block_type == "image":
            blocks.append(_image_from_block_data(block_data, source_path))
    return Document(
        source_path=source_path,
        blocks=blocks,
        header=_section_from_data(data.get("header"), source_path),
        footer=_section_from_data(data.get("footer"), source_path),
    )


def document_from_style_analysis_file(path: Path) -> Document:
    return document_from_style_analysis(json.loads(path.read_text(encoding="utf-8")))


def document_from_debug_dir(debug_dir: Path) -> Document:
    blocks_json_path = debug_dir / "BodyText" / "Section0.blocks.json"
    if blocks_json_path.exists():
        return document_from_blocks(json.loads(blocks_json_path.read_text(encoding="utf-8")))
    style_json_path = debug_dir / "BodyText" / "Section0.styles.json"
    return document_from_style_analysis_file(style_json_path)


def document_from_ir_dict(data: Mapping[str, Any]) -> Document:
    return document_from_blocks(data)


def document_from_ir_json_file(path: Path) -> Document:
    return document_from_ir_dict(json.loads(path.read_text(encoding="utf-8")))


def _paragraph_from_block_data(data: Mapping[str, Any], source_path: str | None) -> Paragraph:
    text_runs_data = data.get("text_runs", [])
    text_runs = [_text_run_from_data(item) for item in text_runs_data]
    if not text_runs and _optional_str(data.get("text_decoded")):
        text_runs = [TextRun(text=_optional_str(data.get("text_decoded")) or "", kind="text")]

    return Paragraph(
        text_runs=text_runs,
        paragraph_style=ParagraphStyle(
            alignment=_optional_str(_mapping(data.get("paragraph_style")).get("alignment")),
            style_ref=_style_ref_from_data(data),
        ),
        list_info=_list_info_from_data(data.get("list_info")),
        is_empty=not any(run.text for run in text_runs),
        paragraph_type=_optional_str(data.get("paragraph_type")) or "unknown_paragraph",
        source_path=source_path,
        source_index=_optional_int(data.get("index")),
    )


def _table_from_block_data(data: Mapping[str, Any], source_path: str | None) -> Table:
    rows: list[TableRow] = []
    for row_data in data.get("rows", []):
        cells = [
            TableCell(
                text=_optional_str(cell_data.get("text")) or "",
                row_index=_optional_int(cell_data.get("row_index")) or 0,
                column_index=_optional_int(cell_data.get("column_index")) or 0,
                colspan=_optional_int(cell_data.get("colspan")) or 1,
                rowspan=_optional_int(cell_data.get("rowspan")) or 1,
                source_record_index=_optional_int(cell_data.get("source_record_index")),
                raw=dict(_mapping(cell_data.get("raw"))),
            )
            for cell_data in _iter_list_of_mappings(row_data.get("cells"))
        ]
        rows.append(
            TableRow(
                cells=cells,
                source_index=_optional_int(row_data.get("index")),
            )
        )

    return Table(
        rows=rows,
        row_count=_optional_int(data.get("row_count")) or len(rows),
        column_count=_optional_int(data.get("column_count")) or max((len(row.cells) for row in rows), default=0),
        source_path=source_path,
        source_index=_optional_int(data.get("index")),
    )


def _image_from_block_data(data: Mapping[str, Any], source_path: str | None) -> ImageBlock:
    return ImageBlock(
        source_path=source_path,
        source_index=_optional_int(data.get("index")),
        source_ref=_optional_str(data.get("source_ref")),
        source_record_index=_optional_int(data.get("source_record_index")),
        binary_stream_ref=_optional_str(data.get("binary_stream_ref")),
        width=_optional_int(data.get("width")),
        height=_optional_int(data.get("height")),
        placement=_optional_str(data.get("placement")),
        alt_text=_optional_str(data.get("alt_text")),
        original_filename=_optional_str(data.get("original_filename")),
        original_size_text=_optional_str(data.get("original_size_text")),
        raw=dict(_mapping(data.get("raw"))),
    )


def _section_from_data(data: Any, source_path: str | None) -> DocumentSection | None:
    mapping = _mapping(data)
    section_blocks = []
    for block_data in _iter_list_of_mappings(mapping.get("blocks")):
        block_type = _optional_str(block_data.get("block_type"))
        if block_type == "paragraph":
            section_blocks.append(_paragraph_from_block_data(block_data, source_path))
        elif block_type == "table":
            section_blocks.append(_table_from_block_data(block_data, source_path))
        elif block_type == "image":
            section_blocks.append(_image_from_block_data(block_data, source_path))
    if not section_blocks:
        return None
    return DocumentSection(blocks=section_blocks)


def _text_run_from_data(data: Mapping[str, Any]) -> TextRun:
    char_style = _mapping(data.get("char_style")) or _mapping(data.get("character_style"))
    return TextRun(
        text=_optional_str(data.get("text")) or "",
        kind=_optional_str(data.get("kind")) or "text",
        character_style=CharacterStyle(
            bold=_optional_bool(char_style.get("bold")),
            font_size_pt=_optional_float(char_style.get("font_size_pt")),
            style_ref=_char_style_ref_from_data(data, char_style),
        ),
        field_type=_optional_str(data.get("field_type")),
        resolved_text=_optional_str(data.get("resolved_text")),
        raw=dict(_mapping(data.get("raw"))),
    )


def _list_info_from_data(data: Any) -> ListInfo | None:
    mapping = _mapping(data)
    if not mapping:
        return None
    return ListInfo(
        kind=_optional_str(mapping.get("kind")),
        level=_optional_int(mapping.get("level")),
        numbering_ref=_optional_int(mapping.get("numbering_ref")),
        marker_text=_optional_str(mapping.get("marker_text")),
        raw=dict(_mapping(mapping.get("raw"))),
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _iter_list_of_mappings(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _style_ref_from_data(data: Mapping[str, Any]) -> int | None:
    direct = _optional_int(data.get("paragraph_style_ref"))
    if direct is not None:
        return direct
    nested = _mapping(data.get("paragraph_style"))
    return _optional_int(nested.get("style_ref"))


def _char_style_ref_from_data(data: Mapping[str, Any], char_style: Mapping[str, Any]) -> int | None:
    direct = _optional_int(data.get("char_style_ref"))
    if direct is not None:
        return direct
    return _optional_int(char_style.get("style_ref"))


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _optional_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None
