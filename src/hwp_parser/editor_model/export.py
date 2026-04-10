from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Mapping

from hwp_parser.docx_writer.write import write_docx
from hwp_parser.ir.convert import document_from_ir_dict, document_from_ir_json_file
from hwp_parser.ir.models import Document, ImageBlock

from .convert import editor_model_to_ir

LOGGER = logging.getLogger(__name__)


def write_docx_from_editor_model(
    editor_model: Mapping[str, Any],
    output_path: Path,
    *,
    original_ir: Document | None = None,
) -> Path:
    document = editor_model_to_ir(editor_model, original_ir=original_ir)
    _validate_export_images(document)
    return write_docx(document, output_path)


def write_docx_from_editor_model_json_files(
    editor_model_path: Path,
    output_path: Path,
    *,
    original_ir_path: Path | None = None,
) -> Path:
    editor_model_payload = json.loads(editor_model_path.read_text(encoding="utf-8"))
    original_ir = document_from_ir_json_file(original_ir_path) if original_ir_path is not None else None
    return write_docx_from_editor_model(
        editor_model_payload,
        output_path,
        original_ir=original_ir,
    )


def document_from_ir_dict_payload(payload: Mapping[str, Any]) -> Document:
    return document_from_ir_dict(payload)


def _validate_export_images(original_ir: Document | None) -> None:
    if original_ir is None:
        return

    for block in original_ir.blocks:
        if not isinstance(block, ImageBlock):
            continue
        replacement_data_url = block.raw.get("replacement_data_url")
        if isinstance(replacement_data_url, str) and replacement_data_url.startswith("data:"):
            continue
        binary_output_path = block.raw.get("binary_output_path")
        if not isinstance(binary_output_path, str) or not binary_output_path:
            LOGGER.warning(
                "Image export may be skipped because image.raw.binary_output_path is missing: "
                "binary_stream_ref=%s",
                block.binary_stream_ref,
            )
