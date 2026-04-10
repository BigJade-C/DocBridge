from __future__ import annotations

from pathlib import Path

from hwp_parser.container import HwpContainerDumper
from hwp_parser.ir.convert import document_from_debug_dir
from hwp_parser.ir.serialize import document_to_dict

from .docx import import_docx_to_ir_dict


def import_document_to_ir_dict(
    input_path: Path,
    *,
    artifact_root: Path = Path("artifacts/imports"),
) -> dict[str, object]:
    suffix = input_path.suffix.lower()
    if suffix in {".hwp", ".hwpx"}:
        summary = HwpContainerDumper(input_path).dump(artifact_root / "debug")
        return document_to_dict(document_from_debug_dir(Path(summary.debug_dir)))
    if suffix == ".docx":
        return import_docx_to_ir_dict(input_path, artifact_root=artifact_root)
    raise ValueError(f"Unsupported import format: {input_path.suffix}")
