from __future__ import annotations

import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from hwp_parser.container import HwpContainerDumper
from hwp_parser.docx_writer import ImageResolutionContext, resolve_image_path
from hwp_parser.ir.convert import document_from_debug_dir
from hwp_parser.ir.models import ImageBlock


def _build_image_document(sample_name: str, tmp_path: Path):
    summary = HwpContainerDumper(Path("hwp_samples") / sample_name).dump(tmp_path / "debug")
    document = document_from_debug_dir(Path(summary.debug_dir))
    return document


def _get_image_block(document) -> ImageBlock:
    return next(block for block in document.blocks if isinstance(block, ImageBlock))


def test_resolve_image_path_prefers_binary_output_path(tmp_path: Path) -> None:
    document = _build_image_document("004_image_basic.hwp", tmp_path)
    image = _get_image_block(document)

    resolved = resolve_image_path(image)

    assert resolved is not None
    assert resolved == Path(image.raw["binary_output_path"]).resolve()


def test_resolve_image_path_falls_back_to_binary_stream_ref_search(tmp_path: Path) -> None:
    document = _build_image_document("004_image_basic.hwp", tmp_path)
    image = _get_image_block(document)
    image.raw.pop("binary_output_path", None)

    resolved = resolve_image_path(
        image,
        context=ImageResolutionContext(search_roots=(tmp_path / "debug",)),
    )

    assert resolved is not None
    assert resolved.name == "BIN0001.png"


def test_resolve_image_path_logs_when_ambiguous(tmp_path: Path, caplog) -> None:
    document = _build_image_document("004_image_basic.hwp", tmp_path)
    image = _get_image_block(document)
    image.raw.pop("binary_output_path", None)

    root_a = tmp_path / "search-a" / "BinData"
    root_b = tmp_path / "search-b" / "nested" / "BinData"
    root_a.mkdir(parents=True, exist_ok=True)
    root_b.mkdir(parents=True, exist_ok=True)
    source = Path(next(iter((tmp_path / "debug").rglob("BIN0001.png"))))
    (root_a / "BIN0001.png").write_bytes(source.read_bytes())
    (root_b / "BIN0001.png").write_bytes(source.read_bytes())

    with caplog.at_level(logging.WARNING):
        resolved = resolve_image_path(
            image,
            context=ImageResolutionContext(search_roots=(tmp_path / "search-a", tmp_path / "search-b")),
        )

    assert resolved is None
    assert "ambiguous" in caplog.text


def test_resolve_image_path_logs_when_missing(caplog) -> None:
    image = ImageBlock(
        binary_stream_ref="BinData/BIN9999.png",
        raw={},
    )

    with caplog.at_level(logging.WARNING):
        resolved = resolve_image_path(
            image,
            context=ImageResolutionContext(search_roots=(Path("/definitely/missing/path"),)),
        )

    assert resolved is None
    assert "fallback failed" in caplog.text
