from __future__ import annotations

import json
from pathlib import Path

from hwp_parser.container import HwpContainerDumper
from hwp_parser.ir.convert import document_from_debug_dir
from hwp_parser.ir.serialize import document_to_dict, document_to_json


def _build_document(sample_name: str, tmp_path: Path):
    sample = Path("hwp_samples") / sample_name
    summary = HwpContainerDumper(sample).dump(tmp_path / "debug")
    document = document_from_debug_dir(Path(summary.debug_dir))
    return summary, document


def test_ir_preserves_paragraph_count_for_text_only_sample(tmp_path: Path) -> None:
    _, document = _build_document("001_text_only.hwp", tmp_path)

    assert document.paragraph_count == 5


def test_ir_preserves_visible_text_for_text_only_sample(tmp_path: Path) -> None:
    _, document = _build_document("001_text_only.hwp", tmp_path)

    visible_texts = [paragraph.text for paragraph in document.blocks if paragraph.text]
    assert visible_texts == ["제목입니다", "첫 번째 문단입니다", "두 번째 문단입니다"]


def test_ir_preserves_title_paragraph_text_for_text_only_sample(tmp_path: Path) -> None:
    _, document = _build_document("001_text_only.hwp", tmp_path)

    assert document.blocks[0].text == "제목입니다"


def test_ir_preserves_alignment_for_paragraph_style_sample(tmp_path: Path) -> None:
    _, document = _build_document("002_paragraph_style.hwp", tmp_path)

    alignments = [paragraph.paragraph_style.alignment for paragraph in document.blocks]
    assert alignments == ["center", "left", "right"]


def test_ir_preserves_character_style_fields_for_paragraph_style_sample(tmp_path: Path) -> None:
    _, document = _build_document("002_paragraph_style.hwp", tmp_path)

    title_run = document.blocks[0].text_runs[0]
    left_run = document.blocks[1].text_runs[0]

    assert title_run.character_style.bold is True
    assert title_run.character_style.font_size_pt is not None
    assert title_run.character_style.style_ref is not None
    assert left_run.character_style.bold is False
    assert left_run.character_style.style_ref is not None


def test_ir_json_export_is_clean_and_diffable(tmp_path: Path) -> None:
    _, document = _build_document("002_paragraph_style.hwp", tmp_path)

    payload = json.loads(document_to_json(document))
    as_dict = document_to_dict(document)

    assert payload["block_count"] == as_dict["block_count"]
    assert payload["blocks"][0]["text"] == "제목입니다"
    assert payload["visible_text_blocks"][1]["paragraph_style"]["alignment"] == "left"


def test_ir_preserves_numbering_metadata_for_numbering_sample(tmp_path: Path) -> None:
    _, document = _build_document("005_numbering.hwp", tmp_path)

    assert [block.text for block in document.blocks] == ["첫 번째 항목", "두 번째 항목", "세 번째 항목"]
    assert all(block.list_info is not None for block in document.blocks)
    assert [block.list_info.kind for block in document.blocks] == ["numbered", "numbered", "numbered"]
    assert [block.list_info.level for block in document.blocks] == [0, 0, 0]
    assert [block.list_info.numbering_ref for block in document.blocks] == [2, 2, 2]
    assert [block.list_info.marker_text for block in document.blocks] == ["1.", "2.", "3."]
