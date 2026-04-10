from __future__ import annotations

import json
from pathlib import Path

from hwp_parser.container import HwpContainerDumper
from hwp_parser.ir.convert import document_from_debug_dir


def _build_header_footer_document(tmp_path: Path):
    summary = HwpContainerDumper(Path("hwp_samples/006_header_footer.hwp")).dump(tmp_path / "debug")
    document = document_from_debug_dir(Path(summary.debug_dir))
    return summary, document


def test_header_text_is_correctly_extracted(tmp_path: Path) -> None:
    _, document = _build_header_footer_document(tmp_path)

    assert document.header is not None
    assert [block.text for block in document.header.blocks] == ["문서 헤더"]


def test_footer_text_is_correctly_extracted(tmp_path: Path) -> None:
    _, document = _build_header_footer_document(tmp_path)

    assert document.footer is not None
    assert [block.text for block in document.footer.blocks] == ["페이지 1"]
    footer_runs = document.footer.blocks[0].text_runs
    assert footer_runs[0].kind == "text"
    assert footer_runs[0].text == "페이지 "
    assert footer_runs[1].kind == "field"
    assert footer_runs[1].field_type == "page_number"
    assert footer_runs[1].resolved_text == "1"


def test_main_document_blocks_remain_separate_from_header_footer(tmp_path: Path) -> None:
    _, document = _build_header_footer_document(tmp_path)

    assert [block.text for block in document.blocks] == ["본문 내용입니다"]


def test_header_footer_are_present_in_ir_json(tmp_path: Path) -> None:
    summary, _ = _build_header_footer_document(tmp_path)

    payload = json.loads((Path(summary.debug_dir) / "ir.json").read_text(encoding="utf-8"))
    assert payload["header"]["blocks"][0]["text"] == "문서 헤더"
    assert payload["footer"]["blocks"][0]["text"] == "페이지 1"
    assert payload["footer"]["blocks"][0]["text_runs"][1]["field_type"] == "page_number"
    assert payload["blocks"][0]["text"] == "본문 내용입니다"
