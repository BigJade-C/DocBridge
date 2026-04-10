from __future__ import annotations

import json
from pathlib import Path


def find_paragraph_style_sample() -> Path:
    sample = Path("hwp_samples/002_paragraph_style.hwp")
    if not sample.exists():
        raise AssertionError("Expected paragraph-style sample file")
    return sample


def test_style_analysis_json_is_generated(tmp_path: Path) -> None:
    from hwp_parser.container import HwpContainerDumper

    summary = HwpContainerDumper(find_paragraph_style_sample()).dump(tmp_path / "debug")
    style_json = Path(summary.debug_dir) / "BodyText" / "Section0.styles.json"
    docinfo_records_json = Path(summary.debug_dir) / "DocInfo.records.json"
    docinfo_tables_json = Path(summary.debug_dir) / "DocInfo.style_tables.json"

    assert style_json.exists()
    assert docinfo_records_json.exists()
    assert docinfo_tables_json.exists()


def test_style_analysis_detects_left_and_right_alignment(tmp_path: Path) -> None:
    from hwp_parser.container import HwpContainerDumper

    summary = HwpContainerDumper(find_paragraph_style_sample()).dump(tmp_path / "debug")
    style_json = Path(summary.debug_dir) / "BodyText" / "Section0.styles.json"
    document = json.loads(style_json.read_text(encoding="utf-8"))

    alignments = {
        paragraph["paragraph_style"]["alignment"]
        for paragraph in document["paragraphs"]
        if paragraph["paragraph_style"]["alignment"] is not None
    }
    assert "left" in alignments
    assert "right" in alignments


def test_style_analysis_exposes_style_refs_and_font_size(tmp_path: Path) -> None:
    from hwp_parser.container import HwpContainerDumper

    summary = HwpContainerDumper(find_paragraph_style_sample()).dump(tmp_path / "debug")
    style_json = Path(summary.debug_dir) / "BodyText" / "Section0.styles.json"
    document = json.loads(style_json.read_text(encoding="utf-8"))

    paragraphs = document["paragraphs"]
    assert paragraphs[0]["paragraph_style_ref"] is not None
    assert paragraphs[0]["text_runs"][0]["char_style_ref"] is not None
    assert paragraphs[0]["text_runs"][0]["char_style"]["font_size_pt"] is not None


def test_three_style_sample_paragraphs_do_not_share_same_paragraph_style_ref(tmp_path: Path) -> None:
    from hwp_parser.container import HwpContainerDumper

    summary = HwpContainerDumper(find_paragraph_style_sample()).dump(tmp_path / "debug")
    style_json = Path(summary.debug_dir) / "BodyText" / "Section0.styles.json"
    document = json.loads(style_json.read_text(encoding="utf-8"))

    refs = [paragraph["paragraph_style_ref"] for paragraph in document["paragraphs"]]
    assert len(set(refs)) > 1


def test_title_paragraph_style_differs_from_other_two(tmp_path: Path) -> None:
    from hwp_parser.container import HwpContainerDumper

    summary = HwpContainerDumper(find_paragraph_style_sample()).dump(tmp_path / "debug")
    style_json = Path(summary.debug_dir) / "BodyText" / "Section0.styles.json"
    document = json.loads(style_json.read_text(encoding="utf-8"))

    paragraphs = document["paragraphs"]
    title_ref = paragraphs[0]["paragraph_style_ref"]
    other_refs = {paragraphs[1]["paragraph_style_ref"], paragraphs[2]["paragraph_style_ref"]}

    assert all(ref is not None for ref in [title_ref, *other_refs])
    assert title_ref not in other_refs
