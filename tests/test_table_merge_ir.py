from __future__ import annotations

from pathlib import Path

from hwp_parser.container import HwpContainerDumper
from hwp_parser.ir.convert import document_from_debug_dir
from hwp_parser.ir.models import Paragraph, Table


def _build_table_merge_document(tmp_path: Path):
    summary = HwpContainerDumper(Path("hwp_samples/007_table_merge.hwp")).dump(tmp_path / "debug")
    document = document_from_debug_dir(Path(summary.debug_dir))
    return summary, document


def test_table_merge_block_order_is_paragraph_table_paragraph(tmp_path: Path) -> None:
    _, document = _build_table_merge_document(tmp_path)

    assert [type(block) for block in document.blocks] == [Paragraph, Table, Paragraph]
    assert [block.text for block in document.blocks if isinstance(block, Paragraph)] == ["표 병합 테스트", "표 아래 설명"]


def test_merged_top_row_cell_is_represented_once_with_colspan(tmp_path: Path) -> None:
    _, document = _build_table_merge_document(tmp_path)

    table = document.blocks[1]
    assert isinstance(table, Table)
    top_row = table.rows[0]

    assert len(top_row.cells) == 2
    assert [cell.text for cell in top_row.cells] == ["A", "B+C"]
    assert top_row.cells[0].colspan == 1
    assert top_row.cells[1].colspan == 2
    assert top_row.cells[1].rowspan == 1


def test_second_row_still_contains_normal_cells(tmp_path: Path) -> None:
    _, document = _build_table_merge_document(tmp_path)

    table = document.blocks[1]
    assert isinstance(table, Table)
    second_row = table.rows[1]

    assert len(second_row.cells) == 3
    assert [cell.text for cell in second_row.cells] == ["D", "E", "F"]
    assert all(cell.colspan == 1 for cell in second_row.cells)
    assert all(cell.rowspan == 1 for cell in second_row.cells)


def test_merged_table_visible_texts_are_preserved(tmp_path: Path) -> None:
    _, document = _build_table_merge_document(tmp_path)

    table = document.blocks[1]
    assert isinstance(table, Table)
    texts = [cell.text for row in table.rows for cell in row.cells]
    assert texts == ["A", "B+C", "D", "E", "F"]
