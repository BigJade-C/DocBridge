from __future__ import annotations

from pathlib import Path

import pytest

from hwp_parser.container import HwpContainerDumper


def find_sample_document() -> Path:
    search_roots = [
        Path("samples"),
        Path("hwp_samples"),
    ]
    for root in search_roots:
        if not root.exists():
            continue
        candidates = list(sorted(root.rglob("*.hwp")))
        candidates.extend(sorted(root.rglob("*.hwpx")))
        for path in candidates:
            return path
    pytest.skip("No .hwp or .hwpx sample found under samples/ or hwp_samples/")


def test_document_opens_correctly(tmp_path: Path) -> None:
    sample = find_sample_document()

    summary = HwpContainerDumper(sample).dump(tmp_path / "debug")

    assert summary.container_type in {"ole", "hwpx"}
    assert summary.stream_count > 0


def test_bodytext_exists(tmp_path: Path) -> None:
    sample = find_sample_document()

    summary = HwpContainerDumper(sample).dump(tmp_path / "debug")
    stream_paths = {stream.path for stream in summary.streams}

    expected_path = (
        "BodyText/Section0"
        if summary.container_type == "ole"
        else "Contents/section0.xml"
    )
    assert expected_path in stream_paths


def test_extracted_outputs_use_common_logical_paths(tmp_path: Path) -> None:
    hwpx_sample = Path("hwp_samples/001_text_only.hwpx")
    if not hwpx_sample.exists():
        pytest.skip("No .hwpx sample found for logical path test")

    summary = HwpContainerDumper(hwpx_sample).dump(tmp_path / "debug")
    logical_paths = {item.logical_path for item in summary.extracted}

    assert "FileHeader" in logical_paths
    assert "BodyText/Section0" in logical_paths
