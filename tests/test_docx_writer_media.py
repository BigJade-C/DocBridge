from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from hwp_parser.container import HwpContainerDumper
from hwp_parser.ir.convert import document_from_debug_dir
from hwp_parser.docx_writer.write import write_docx


def _build_ir_document(sample_name: str, tmp_path: Path):
    summary = HwpContainerDumper(Path("hwp_samples") / sample_name).dump(tmp_path / "debug")
    return document_from_debug_dir(Path(summary.debug_dir))


def test_docx_image_export_creates_word_media_files(tmp_path: Path) -> None:
    document = _build_ir_document("004_image_basic.hwp", tmp_path)
    output_path = tmp_path / "004_image_basic.docx"

    write_docx(document, output_path)

    with ZipFile(output_path) as archive:
        media_files = [
            name
            for name in archive.namelist()
            if name.startswith("word/media/")
        ]

    assert media_files


def test_docx_image_export_creates_word_media_files_via_binary_stream_ref_fallback(tmp_path: Path) -> None:
    document = _build_ir_document("004_image_basic.hwp", tmp_path)
    image = next(block for block in document.blocks if block.block_type == "image")
    image.raw.pop("binary_output_path", None)
    output_path = tmp_path / "004_image_basic_fallback.docx"

    from hwp_parser.docx_writer import ImageResolutionContext

    write_docx(
        document,
        output_path,
        image_resolution_context=ImageResolutionContext(search_roots=(tmp_path / "debug",)),
    )

    with ZipFile(output_path) as archive:
        media_files = [
            name
            for name in archive.namelist()
            if name.startswith("word/media/")
        ]

    assert media_files
