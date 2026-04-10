from __future__ import annotations

from pathlib import Path

from hwp_parser.container import HwpContainerDumper
from hwp_parser.editor_model import editor_model_to_ir, ir_to_editor_model
from hwp_parser.ir.convert import document_from_debug_dir
from hwp_parser.ir.models import ImageBlock, Paragraph, Table


PNG_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a5u8AAAAASUVORK5CYII="
)


def _build_ir_document(sample_name: str, tmp_path: Path):
    summary = HwpContainerDumper(Path("hwp_samples") / sample_name).dump(tmp_path / "debug")
    return document_from_debug_dir(Path(summary.debug_dir))


def test_editor_model_text_edit_updates_ir_text(tmp_path: Path) -> None:
    original = _build_ir_document("001_text_only.hwp", tmp_path)
    editor_model = ir_to_editor_model(original)

    editor_model["children"][0]["children"][0]["text"] = "수정된 제목"

    updated = editor_model_to_ir(editor_model, original_ir=original)

    assert isinstance(updated.blocks[0], Paragraph)
    assert updated.blocks[0].text == "수정된 제목"


def test_editor_model_bold_updates_ir_character_style(tmp_path: Path) -> None:
    original = _build_ir_document("002_paragraph_style.hwp", tmp_path)
    editor_model = ir_to_editor_model(original)

    editor_model["children"][1]["children"][0]["marks"] = [{"type": "bold"}]

    updated = editor_model_to_ir(editor_model, original_ir=original)
    paragraph = updated.blocks[1]

    assert isinstance(paragraph, Paragraph)
    assert paragraph.text_runs[0].character_style.bold is True


def test_editor_model_font_size_updates_ir_character_style(tmp_path: Path) -> None:
    original = _build_ir_document("002_paragraph_style.hwp", tmp_path)
    editor_model = ir_to_editor_model(original)

    editor_model["children"][1]["children"][0]["marks"] = [{"type": "fontSize", "value": 18}]

    updated = editor_model_to_ir(editor_model, original_ir=original)
    paragraph = updated.blocks[1]

    assert isinstance(paragraph, Paragraph)
    assert paragraph.text_runs[0].character_style.font_size_pt == 18.0


def test_editor_model_alignment_updates_ir_paragraph_style(tmp_path: Path) -> None:
    original = _build_ir_document("002_paragraph_style.hwp", tmp_path)
    editor_model = ir_to_editor_model(original)

    editor_model["children"][1]["attrs"]["alignment"] = "center"

    updated = editor_model_to_ir(editor_model, original_ir=original)
    paragraph = updated.blocks[1]

    assert isinstance(paragraph, Paragraph)
    assert paragraph.paragraph_style.alignment == "center"


def test_inserted_paragraph_appears_in_ir(tmp_path: Path) -> None:
    original = _build_ir_document("001_text_only.hwp", tmp_path)
    editor_model = ir_to_editor_model(original)

    editor_model["children"].insert(
        1,
        {
            "type": "paragraph",
            "id": "p999",
            "attrs": {"alignment": "left"},
            "children": [{"type": "text", "id": "text999", "text": "새 문단", "marks": []}],
        },
    )

    updated = editor_model_to_ir(editor_model, original_ir=original)
    paragraph_texts = [block.text for block in updated.blocks if isinstance(block, Paragraph)]

    assert "새 문단" in paragraph_texts


def test_deleted_paragraph_is_removed_from_ir(tmp_path: Path) -> None:
    original = _build_ir_document("001_text_only.hwp", tmp_path)
    editor_model = ir_to_editor_model(original)

    editor_model["children"] = [child for child in editor_model["children"] if child.get("id") != "p3"]

    updated = editor_model_to_ir(editor_model, original_ir=original)
    paragraph_texts = [block.text for block in updated.blocks if isinstance(block, Paragraph)]

    assert "첫 번째 문단입니다" not in paragraph_texts


def test_unchanged_table_and_image_blocks_survive_round_trip(tmp_path: Path) -> None:
    original = _build_ir_document("008_mixed.hwp", tmp_path)
    editor_model = ir_to_editor_model(original)

    editor_model["children"][0]["children"][0]["text"] = "수정된 문서 제목"

    updated = editor_model_to_ir(editor_model, original_ir=original)

    assert [type(block) for block in updated.blocks] == [Paragraph, Paragraph, Table, Paragraph, ImageBlock, Paragraph]
    table = updated.blocks[2]
    image = updated.blocks[4]

    assert isinstance(table, Table)
    assert isinstance(image, ImageBlock)
    assert [cell.text for row in table.rows for cell in row.cells] == ["A", "B", "C", "D", "E", "F"]
    assert image.binary_stream_ref == "BinData/BIN0001.png"
    assert updated.blocks[0].text == "수정된 문서 제목"


def test_table_cell_text_edit_updates_ir_and_preserves_span_metadata(tmp_path: Path) -> None:
    original = _build_ir_document("007_table_merge.hwp", tmp_path)
    editor_model = ir_to_editor_model(original)

    table_node = next(child for child in editor_model["children"] if child["type"] == "table")
    table_node["rows"][0]["cells"][1]["children"][0]["children"][0]["text"] = "수정된 병합 셀"

    updated = editor_model_to_ir(editor_model, original_ir=original)
    table = next(block for block in updated.blocks if isinstance(block, Table))

    assert table.rows[0].cells[1].text == "수정된 병합 셀"
    assert table.rows[0].cells[1].colspan == 2
    assert table.rows[0].cells[1].rowspan == 1


def test_image_replacement_updates_ir_and_preserves_original_metadata(tmp_path: Path) -> None:
    original = _build_ir_document("004_image_basic.hwp", tmp_path)
    editor_model = ir_to_editor_model(original)

    image_node = next(child for child in editor_model["children"] if child["type"] == "image")
    image_node["attrs"]["src"] = PNG_DATA_URL
    image_node["attrs"]["alt"] = "교체된 이미지"

    updated = editor_model_to_ir(editor_model, original_ir=original)
    image = next(block for block in updated.blocks if isinstance(block, ImageBlock))

    assert image.binary_stream_ref == "BinData/BIN0001.png"
    assert image.alt_text == "교체된 이미지"
    assert image.raw["replacement_data_url"] == PNG_DATA_URL
