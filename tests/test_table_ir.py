from __future__ import annotations

from pathlib import Path

from hwp_parser.container import HwpContainerDumper
from hwp_parser.ir.convert import document_from_debug_dir
from hwp_parser.ir.models import Paragraph, Table


def test_table_sample_block_order_is_paragraph_table_paragraph(tmp_path: Path) -> None:
    summary = HwpContainerDumper(Path("hwp_samples/003_table_basic.hwp")).dump(tmp_path / "debug")
    document = document_from_debug_dir(Path(summary.debug_dir))

    assert [type(block) for block in document.blocks] == [Paragraph, Table, Paragraph]


def test_table_dimensions_are_correct(tmp_path: Path) -> None:
    summary = HwpContainerDumper(Path("hwp_samples/003_table_basic.hwp")).dump(tmp_path / "debug")
    document = document_from_debug_dir(Path(summary.debug_dir))

    table = document.blocks[1]
    assert isinstance(table, Table)
    assert table.row_count == 2
    assert table.column_count == 3


def test_table_cell_texts_are_preserved(tmp_path: Path) -> None:
    summary = HwpContainerDumper(Path("hwp_samples/003_table_basic.hwp")).dump(tmp_path / "debug")
    document = document_from_debug_dir(Path(summary.debug_dir))

    table = document.blocks[1]
    assert isinstance(table, Table)
    texts = [cell.text for row in table.rows for cell in row.cells]
    assert texts == ["A", "B", "C", "D", "E", "F"]
