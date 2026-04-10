from __future__ import annotations

import json
from pathlib import Path

from hwp_parser.container import HwpContainerDumper
from hwp_parser.editor_model import ir_to_editor_model
from hwp_parser.ir.convert import document_from_debug_dir


def _build_ir_document(sample_name: str, tmp_path: Path):
    summary = HwpContainerDumper(Path("hwp_samples") / sample_name).dump(tmp_path / "debug")
    return document_from_debug_dir(Path(summary.debug_dir))


def test_editor_model_text_only_paragraph_structure_is_correct(tmp_path: Path) -> None:
    document = _build_ir_document("001_text_only.hwp", tmp_path)

    editor_model = ir_to_editor_model(document)

    assert editor_model["type"] == "doc"
    assert [child["type"] for child in editor_model["children"]] == [
        "paragraph",
        "paragraph",
        "paragraph",
        "paragraph",
        "paragraph",
    ]
    assert [child["children"][0]["text"] for child in editor_model["children"] if child["children"]] == [
        "제목입니다",
        "첫 번째 문단입니다",
        "두 번째 문단입니다",
    ]
    json.dumps(editor_model, ensure_ascii=False)


def test_editor_model_table_basic_structure_is_correct(tmp_path: Path) -> None:
    document = _build_ir_document("003_table_basic.hwp", tmp_path)

    editor_model = ir_to_editor_model(document)

    assert [child["type"] for child in editor_model["children"]] == ["paragraph", "table", "paragraph"]
    table_node = editor_model["children"][1]
    assert table_node["type"] == "table"
    assert len(table_node["rows"]) == 2
    assert [len(row["cells"]) for row in table_node["rows"]] == [3, 3]
    assert [
        cell["children"][0]["children"][0]["text"]
        for row in table_node["rows"]
        for cell in row["cells"]
    ] == ["A", "B", "C", "D", "E", "F"]


def test_editor_model_mixed_block_order_is_correct(tmp_path: Path) -> None:
    document = _build_ir_document("008_mixed.hwp", tmp_path)

    editor_model = ir_to_editor_model(document)

    assert [child["type"] for child in editor_model["children"]] == [
        "paragraph",
        "paragraph",
        "table",
        "paragraph",
        "image",
        "paragraph",
    ]
    image_node = editor_model["children"][4]
    assert image_node["attrs"]["src"] == "BinData/BIN0001.png"
    assert image_node["attrs"]["width"] == 444
    assert image_node["attrs"]["height"] == 517
    assert image_node["attrs"]["alt"] == "그림입니다."


def test_editor_model_paragraph_marks_are_preserved(tmp_path: Path) -> None:
    document = _build_ir_document("002_paragraph_style.hwp", tmp_path)

    editor_model = ir_to_editor_model(document)

    title_paragraph = editor_model["children"][0]
    title_text = title_paragraph["children"][0]

    assert title_paragraph["attrs"]["alignment"] == "center"
    assert {"type": "bold"} in title_text["marks"]
    assert {"type": "fontSize", "value": 13.0} in title_text["marks"]


def test_editor_model_node_ids_are_present_and_stable_per_conversion(tmp_path: Path) -> None:
    document = _build_ir_document("003_table_basic.hwp", tmp_path)

    first = ir_to_editor_model(document)
    second = ir_to_editor_model(document)

    assert first == second
    assert first["id"] == "doc1"
    assert all("id" in child for child in first["children"])
