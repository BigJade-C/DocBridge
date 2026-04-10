from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from hwp_parser.ir.models import (
    Block,
    CharacterStyle,
    Document,
    ImageBlock,
    Paragraph,
    ParagraphStyle,
    Table,
    TableCell,
    TextRun,
)


def ir_to_editor_model(document: Document) -> dict[str, object]:
    id_gen = _IdGenerator()
    return {
        "type": "doc",
        "id": id_gen.next("doc"),
        "children": [_block_to_node(block, id_gen) for block in document.blocks],
    }


def editor_model_to_ir(
    editor_model: Mapping[str, Any],
    original_ir: Document | None = None,
) -> Document:
    paragraph_templates = (
        [block for block in original_ir.blocks if isinstance(block, Paragraph)]
        if original_ir is not None
        else []
    )
    passthrough_tables = (
        [block for block in original_ir.blocks if isinstance(block, Table)]
        if original_ir is not None
        else []
    )
    passthrough_images = (
        [block for block in original_ir.blocks if isinstance(block, ImageBlock)]
        if original_ir is not None
        else []
    )

    paragraph_index = 0
    table_index = 0
    image_index = 0
    blocks: list[Block] = []

    for child in _list_of_mappings(editor_model.get("children")):
        node_type = _optional_str(child.get("type"))
        if node_type == "paragraph":
            template = paragraph_templates[paragraph_index] if paragraph_index < len(paragraph_templates) else None
            blocks.append(_paragraph_node_to_ir(child, template))
            paragraph_index += 1
            continue
        if node_type == "table":
            template = passthrough_tables[table_index] if table_index < len(passthrough_tables) else None
            blocks.append(_table_node_to_ir(child, template=template))
            table_index += 1
            continue
        if node_type == "image":
            if image_index < len(passthrough_images):
                blocks.append(passthrough_images[image_index])
            else:
                blocks.append(_image_node_to_ir(child))
            image_index += 1

    return Document(
        source_path=original_ir.source_path if original_ir is not None else None,
        blocks=blocks,
        header=original_ir.header if original_ir is not None else None,
        footer=original_ir.footer if original_ir is not None else None,
    )


def _block_to_node(block: object, id_gen: "_IdGenerator") -> dict[str, object]:
    if isinstance(block, Paragraph):
        return _paragraph_to_node(block, id_gen)
    if isinstance(block, Table):
        return _table_to_node(block, id_gen)
    if isinstance(block, ImageBlock):
        return _image_to_node(block, id_gen)
    raise TypeError(f"Unsupported IR block for Editor Model v0: {type(block)!r}")


def _paragraph_to_node(paragraph: Paragraph, id_gen: "_IdGenerator") -> dict[str, object]:
    children = [_text_run_to_node(text_run, id_gen) for text_run in paragraph.text_runs if text_run.display_text]
    return {
        "type": "paragraph",
        "id": id_gen.next("p"),
        "attrs": {
            "alignment": paragraph.paragraph_style.alignment or "left",
        },
        "children": children,
    }


def _text_run_to_node(text_run: TextRun, id_gen: "_IdGenerator") -> dict[str, object]:
    return {
        "type": "text",
        "id": id_gen.next("text"),
        "text": text_run.display_text,
        "marks": _marks_for_text_run(text_run),
    }


def _marks_for_text_run(text_run: TextRun) -> list[dict[str, object]]:
    marks: list[dict[str, object]] = []
    style = text_run.character_style
    if style.bold:
        marks.append({"type": "bold"})
    if style.font_size_pt is not None:
        marks.append({"type": "fontSize", "value": style.font_size_pt})
    return marks


def _table_to_node(table: Table, id_gen: "_IdGenerator") -> dict[str, object]:
    return {
        "type": "table",
        "id": id_gen.next("t"),
        "rows": [
            {
                "type": "tableRow",
                "id": id_gen.next("tr"),
                "cells": [_table_cell_to_node(cell, id_gen) for cell in row.cells],
            }
            for row in table.rows
        ],
    }


def _table_cell_to_node(cell: TableCell, id_gen: "_IdGenerator") -> dict[str, object]:
    paragraph = {
        "type": "paragraph",
        "id": id_gen.next("p"),
        "attrs": {
            "alignment": "left",
        },
        "children": (
            [
                {
                    "type": "text",
                    "id": id_gen.next("text"),
                    "text": cell.text,
                    "marks": [],
                }
            ]
            if cell.text
            else []
        ),
    }
    return {
        "type": "tableCell",
        "id": id_gen.next("tc"),
        "colspan": cell.colspan,
        "rowspan": cell.rowspan,
        "children": [paragraph],
    }


def _image_to_node(image: ImageBlock, id_gen: "_IdGenerator") -> dict[str, object]:
    return {
        "type": "image",
        "id": id_gen.next("img"),
        "attrs": {
            "src": image.binary_stream_ref,
            "width": image.width,
            "height": image.height,
            "alt": image.alt_text,
        },
    }


def _paragraph_node_to_ir(data: Mapping[str, Any], template: Paragraph | None) -> Paragraph:
    text_runs = [_text_node_to_ir(child, template) for child in _list_of_mappings(data.get("children"))]
    return Paragraph(
        text_runs=text_runs,
        paragraph_style=ParagraphStyle(
            alignment=_optional_str(_mapping(data.get("attrs")).get("alignment")) or "left",
            style_ref=template.paragraph_style.style_ref if template is not None else None,
        ),
        list_info=template.list_info if template is not None else None,
        is_empty=not any(run.text for run in text_runs),
        paragraph_type=template.paragraph_type if template is not None else "text_paragraph",
        source_path=template.source_path if template is not None else None,
        source_index=template.source_index if template is not None else None,
    )


def _text_node_to_ir(data: Mapping[str, Any], template: Paragraph | None) -> TextRun:
    marks = _list_of_mappings(data.get("marks"))
    style_ref = template.text_runs[0].character_style.style_ref if template and template.text_runs else None
    return TextRun(
        text=_optional_str(data.get("text")) or "",
        kind="text",
        character_style=CharacterStyle(
            bold=_has_mark(marks, "bold"),
            font_size_pt=_font_size_from_marks(marks),
            style_ref=style_ref,
        ),
    )


def _table_node_to_ir(data: Mapping[str, Any], template: Table | None = None) -> Table:
    rows = []
    column_count = 0
    for row_index, row_data in enumerate(_list_of_mappings(data.get("rows"))):
        cells = []
        template_row = template.rows[row_index] if template is not None and row_index < len(template.rows) else None
        for column_index, cell_data in enumerate(_list_of_mappings(row_data.get("cells"))):
            template_cell = (
                template_row.cells[column_index]
                if template_row is not None and column_index < len(template_row.cells)
                else None
            )
            cells.append(
                TableCell(
                    text=_cell_text_from_node(cell_data),
                    row_index=row_index,
                    column_index=column_index,
                    colspan=_optional_int(cell_data.get("colspan")) or (template_cell.colspan if template_cell is not None else 1),
                    rowspan=_optional_int(cell_data.get("rowspan")) or (template_cell.rowspan if template_cell is not None else 1),
                    source_record_index=template_cell.source_record_index if template_cell is not None else None,
                    raw=dict(template_cell.raw) if template_cell is not None else {},
                )
            )
        column_count = max(
            column_count,
            sum(cell.colspan for cell in cells) if cells else 0,
        )
        from hwp_parser.ir.models import TableRow

        rows.append(
            TableRow(
                cells=cells,
                source_index=template_row.source_index if template_row is not None else None,
            )
        )

    return Table(
        rows=rows,
        row_count=template.row_count if template is not None else len(rows),
        column_count=template.column_count if template is not None else column_count,
        source_path=template.source_path if template is not None else None,
        source_index=template.source_index if template is not None else None,
    )


def _image_node_to_ir(data: Mapping[str, Any]) -> ImageBlock:
    attrs = _mapping(data.get("attrs"))
    return ImageBlock(
        binary_stream_ref=_optional_str(attrs.get("src")),
        width=_optional_int(attrs.get("width")),
        height=_optional_int(attrs.get("height")),
        alt_text=_optional_str(attrs.get("alt")),
    )


def _cell_text_from_node(data: Mapping[str, Any]) -> str:
    paragraphs = _list_of_mappings(data.get("children"))
    parts: list[str] = []
    for paragraph in paragraphs:
        for text_node in _list_of_mappings(paragraph.get("children")):
            parts.append(_optional_str(text_node.get("text")) or "")
    return "".join(parts)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list_of_mappings(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _has_mark(marks: list[Mapping[str, Any]], mark_type: str) -> bool:
    return any(_optional_str(mark.get("type")) == mark_type for mark in marks)


def _font_size_from_marks(marks: list[Mapping[str, Any]]) -> float | None:
    for mark in marks:
        if _optional_str(mark.get("type")) != "fontSize":
            continue
        value = mark.get("value")
        if isinstance(value, (int, float)):
            return float(value)
    return None


@dataclass
class _IdGenerator:
    counters: dict[str, int] = field(default_factory=dict)

    def next(self, prefix: str) -> str:
        next_value = self.counters.get(prefix, 0) + 1
        self.counters[prefix] = next_value
        return f"{prefix}{next_value}"
