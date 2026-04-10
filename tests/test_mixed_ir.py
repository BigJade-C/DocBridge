from __future__ import annotations

from pathlib import Path

from hwp_parser.container import HwpContainerDumper
from hwp_parser.ir.convert import document_from_debug_dir
from hwp_parser.ir.models import ImageBlock, Paragraph, Table
from hwp_parser.ir.serialize import document_to_dict


def _build_mixed_document(tmp_path: Path):
    summary = HwpContainerDumper(Path("hwp_samples/008_mixed.hwp")).dump(tmp_path / "debug")
    document = document_from_debug_dir(Path(summary.debug_dir))
    return summary, document


def test_mixed_block_order_and_count_are_correct(tmp_path: Path) -> None:
    _, document = _build_mixed_document(tmp_path)

    assert [type(block) for block in document.blocks] == [Paragraph, Paragraph, Table, Paragraph, ImageBlock, Paragraph]
    assert len(document.blocks) == 6


def test_mixed_contains_expected_block_types(tmp_path: Path) -> None:
    _, document = _build_mixed_document(tmp_path)

    assert sum(isinstance(block, Paragraph) for block in document.blocks) == 4
    assert sum(isinstance(block, Table) for block in document.blocks) == 1
    assert sum(isinstance(block, ImageBlock) for block in document.blocks) == 1


def test_mixed_text_content_integrity_is_preserved(tmp_path: Path) -> None:
    _, document = _build_mixed_document(tmp_path)

    paragraph_texts = [block.text for block in document.blocks if isinstance(block, Paragraph)]
    assert paragraph_texts == ["문서 제목", "첫 번째 문단입니다", "두 번째 문단입니다", "세 번째 문단입니다"]

    title_run = document.blocks[0].text_runs[0]
    assert title_run.character_style.bold is True
    assert title_run.character_style.font_size_pt == 15.0
    assert document.blocks[0].paragraph_style.alignment == "center"


def test_mixed_table_and_image_are_preserved(tmp_path: Path) -> None:
    _, document = _build_mixed_document(tmp_path)

    table = document.blocks[2]
    image = document.blocks[4]

    assert isinstance(table, Table)
    assert isinstance(image, ImageBlock)
    assert [cell.text for row in table.rows for cell in row.cells] == ["A", "B", "C", "D", "E", "F"]
    assert image.binary_stream_ref == "BinData/BIN0001.png"
    assert image.width == 444
    assert image.height == 517


def test_mixed_has_no_unexpected_extra_blocks(tmp_path: Path) -> None:
    _, document = _build_mixed_document(tmp_path)

    assert all(not (isinstance(block, Paragraph) and not block.text) for block in document.blocks)


def test_mixed_ir_json_preserves_image_block_and_order(tmp_path: Path) -> None:
    summary, document = _build_mixed_document(tmp_path)

    payload = document_to_dict(document)
    block_types = [block["block_type"] for block in payload["blocks"]]
    visible_block_types = [block["block_type"] for block in payload["visible_text_blocks"]]
    image_blocks = [block for block in payload["blocks"] if block["block_type"] == "image"]

    assert block_types == ["paragraph", "paragraph", "table", "paragraph", "image", "paragraph"]
    assert visible_block_types == ["paragraph", "paragraph", "table", "paragraph", "image", "paragraph"]
    assert len(image_blocks) == 1
    assert image_blocks[0]["binary_stream_ref"] == "BinData/BIN0001.png"
    assert image_blocks[0]["width"] == 444
    assert image_blocks[0]["height"] == 517
    assert image_blocks[0]["alt_text"] == "그림입니다."

    ir_json_path = Path(summary.debug_dir) / "ir.json"
    assert ir_json_path.exists()
