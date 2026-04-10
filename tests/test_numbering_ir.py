from __future__ import annotations

import json
from pathlib import Path

from hwp_parser.container import HwpContainerDumper
from hwp_parser.ir.convert import document_from_debug_dir
from hwp_parser.ir.models import Paragraph


def _build_numbering_document(tmp_path: Path):
    summary = HwpContainerDumper(Path("hwp_samples/005_numbering.hwp")).dump(tmp_path / "debug")
    document = document_from_debug_dir(Path(summary.debug_dir))
    return summary, document


def test_numbering_item_count_and_order_are_preserved(tmp_path: Path) -> None:
    _, document = _build_numbering_document(tmp_path)

    assert [type(block) for block in document.blocks] == [Paragraph, Paragraph, Paragraph]
    assert [block.text for block in document.blocks] == ["첫 번째 항목", "두 번째 항목", "세 번째 항목"]


def test_numbering_metadata_is_present_on_list_paragraphs(tmp_path: Path) -> None:
    _, document = _build_numbering_document(tmp_path)

    for block in document.blocks:
        assert block.list_info is not None
        assert block.list_info.kind == "numbered"
        assert block.list_info.level == 0
        assert block.list_info.numbering_ref == 2
        assert block.list_info.raw["paragraph_style_ref"] == 20


def test_numbering_marker_texts_are_exported_in_order(tmp_path: Path) -> None:
    summary, _ = _build_numbering_document(tmp_path)

    blocks_payload = json.loads(
        (Path(summary.debug_dir) / "BodyText" / "Section0.blocks.json").read_text(encoding="utf-8")
    )
    assert [block["list_info"]["marker_text"] for block in blocks_payload["blocks"]] == ["1.", "2.", "3."]
