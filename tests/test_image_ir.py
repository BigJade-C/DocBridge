from __future__ import annotations

import json
from pathlib import Path

from hwp_parser.container import HwpContainerDumper
from hwp_parser.ir.convert import document_from_debug_dir
from hwp_parser.ir.models import ImageBlock, Paragraph
from hwp_parser.ir.serialize import document_to_dict


def _build_image_document(tmp_path: Path):
    summary = HwpContainerDumper(Path("hwp_samples/004_image_basic.hwp")).dump(tmp_path / "debug")
    document = document_from_debug_dir(Path(summary.debug_dir))
    return summary, document


def test_image_sample_detects_exactly_one_image_block(tmp_path: Path) -> None:
    _, document = _build_image_document(tmp_path)

    images = [block for block in document.blocks if isinstance(block, ImageBlock)]
    assert len(images) == 1


def test_image_sample_attaches_metadata_to_image_block(tmp_path: Path) -> None:
    _, document = _build_image_document(tmp_path)

    image = next(block for block in document.blocks if isinstance(block, ImageBlock))
    assert image.binary_stream_ref == "BinData/BIN0001.png"
    assert image.width == 444
    assert image.height == 517
    assert image.alt_text == "그림입니다."
    assert image.original_filename is not None
    assert image.original_filename.endswith(".png")
    assert image.original_size_text == "원본 그림의 크기: 가로 444pixel, 세로 517pixel"
    assert image.raw["metadata_lines"]


def test_image_metadata_lines_do_not_leak_into_paragraph_blocks(tmp_path: Path) -> None:
    _, document = _build_image_document(tmp_path)

    paragraph_texts = [
        block.text
        for block in document.blocks
        if isinstance(block, Paragraph) and block.text
    ]
    joined = "\n".join(paragraph_texts)

    assert "원본 그림의 이름:" not in joined
    assert "원본 그림의 크기:" not in joined
    assert "그림입니다." in paragraph_texts


def test_visible_paragraph_survives_when_image_has_human_readable_text(tmp_path: Path) -> None:
    _, document = _build_image_document(tmp_path)

    paragraphs = [block for block in document.blocks if isinstance(block, Paragraph) and block.text]
    assert len(paragraphs) >= 1
    assert paragraphs[0].text == "그림입니다."


def test_image_block_is_present_in_ir_json_export(tmp_path: Path) -> None:
    summary, document = _build_image_document(tmp_path)

    payload = document_to_dict(document)
    image_blocks = [block for block in payload["blocks"] if block["block_type"] == "image"]

    assert len(image_blocks) == 1
    assert image_blocks[0]["binary_stream_ref"] == "BinData/BIN0001.png"
    assert image_blocks[0]["original_size_text"] == "원본 그림의 크기: 가로 444pixel, 세로 517pixel"
    assert image_blocks[0]["raw"]["binary_output_path"].endswith("BinData/BIN0001.png")

    ir_json_path = Path(summary.debug_dir) / "ir.json"
    assert ir_json_path.exists()

    blocks_json_path = Path(summary.debug_dir) / "BodyText" / "Section0.blocks.json"
    blocks_payload = json.loads(blocks_json_path.read_text(encoding="utf-8"))
    assert [block["block_type"] for block in blocks_payload["blocks"]] == ["paragraph", "image"]
    assert blocks_payload["blocks"][0]["text_origin"] == "image_control_visible_text"


def test_regenerated_fixture_ir_contains_binary_output_path() -> None:
    fixture_path = Path("viewer/public/fixtures/008_mixed.ir.json")
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    image = next(block for block in payload["blocks"] if block["block_type"] == "image")

    assert image["raw"]["binary_output_path"].endswith("BinData/BIN0001.png")
