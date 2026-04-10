from __future__ import annotations

import json

from .models import Document, ImageBlock, Paragraph, Table


def document_to_dict(document: Document) -> dict[str, object]:
    visible_text_blocks = [
        _block_to_dict(block)
        for block in document.blocks
        if _is_visible_text_block(block)
    ]
    return {
        "source_path": document.source_path,
        "header": _section_to_dict(document.header),
        "footer": _section_to_dict(document.footer),
        "block_count": len(document.blocks),
        "blocks": [_block_to_dict(block) for block in document.blocks],
        "visible_text_blocks": visible_text_blocks,
    }


def document_to_json(document: Document) -> str:
    return json.dumps(
        document_to_dict(document),
        indent=2,
        ensure_ascii=False,
    )


def _paragraph_to_dict(paragraph: Paragraph) -> dict[str, object]:
    return {
        "block_type": paragraph.block_type,
        "source_path": paragraph.source_path,
        "source_index": paragraph.source_index,
        "paragraph_type": paragraph.paragraph_type,
        "is_empty": paragraph.is_empty,
        "text": paragraph.text,
        "paragraph_style": {
            "alignment": paragraph.paragraph_style.alignment,
            "style_ref": paragraph.paragraph_style.style_ref,
        },
        "list_info": (
            {
                "kind": paragraph.list_info.kind,
                "level": paragraph.list_info.level,
                "numbering_ref": paragraph.list_info.numbering_ref,
                "marker_text": paragraph.list_info.marker_text,
                "raw": paragraph.list_info.raw,
            }
            if paragraph.list_info is not None
            else None
        ),
        "text_runs": [
            {
                "kind": run.kind,
                "text": run.text,
                "field_type": run.field_type,
                "resolved_text": run.resolved_text,
                "raw": run.raw,
                "character_style": {
                    "bold": run.character_style.bold,
                    "font_size_pt": run.character_style.font_size_pt,
                    "style_ref": run.character_style.style_ref,
                },
            }
            for run in paragraph.text_runs
        ],
    }


def _table_to_dict(table: Table) -> dict[str, object]:
    return {
        "block_type": table.block_type,
        "source_path": table.source_path,
        "source_index": table.source_index,
        "row_count": table.row_count,
        "column_count": table.column_count,
        "rows": [
            {
                "source_index": row.source_index,
                "cells": [
                    {
                        "text": cell.text,
                        "row_index": cell.row_index,
                        "column_index": cell.column_index,
                        "colspan": cell.colspan,
                        "rowspan": cell.rowspan,
                        "source_record_index": cell.source_record_index,
                        "raw": cell.raw,
                    }
                    for cell in row.cells
                ],
            }
            for row in table.rows
        ],
    }


def _image_to_dict(image: ImageBlock) -> dict[str, object]:
    return {
        "block_type": image.block_type,
        "source_path": image.source_path,
        "source_index": image.source_index,
        "source_ref": image.source_ref,
        "source_record_index": image.source_record_index,
        "binary_stream_ref": image.binary_stream_ref,
        "width": image.width,
        "height": image.height,
        "placement": image.placement,
        "alt_text": image.alt_text,
        "original_filename": image.original_filename,
        "original_size_text": image.original_size_text,
        "raw": image.raw,
    }


def _section_to_dict(section: object) -> dict[str, object] | None:
    if section is None:
        return None
    blocks = getattr(section, "blocks", None)
    if not isinstance(blocks, list):
        return None
    return {
        "blocks": [_block_to_dict(block) for block in blocks],
    }


def _block_to_dict(block: object) -> dict[str, object]:
    if isinstance(block, Paragraph):
        return _paragraph_to_dict(block)
    if isinstance(block, Table):
        return _table_to_dict(block)
    if isinstance(block, ImageBlock):
        return _image_to_dict(block)
    raise TypeError(f"Unsupported block type: {type(block)!r}")


def _is_visible_text_block(block: object) -> bool:
    if isinstance(block, Paragraph):
        return bool(block.text) and not block.is_empty
    if isinstance(block, Table):
        return any(cell.text for row in block.rows for cell in row.cells)
    if isinstance(block, ImageBlock):
        return True
    return False
