from __future__ import annotations

from pathlib import Path

from hwp_parser.bodytext import BodyTextDecoder, BodyTextRecordParser, ParagraphExtractor
from hwp_parser.file_header import parse_file_header


def find_sample_hwp(name_hint: str | None = None) -> Path:
    candidates = sorted(Path("hwp_samples").glob("*.hwp"))
    if name_hint is not None:
        for candidate in candidates:
            if name_hint in candidate.name:
                return candidate
    if candidates:
        return candidates[0]
    raise AssertionError("Expected at least one .hwp sample")


def _extract_paragraphs(sample: Path, tmp_path: Path):
    from hwp_parser.container import HwpContainerDumper

    summary = HwpContainerDumper(sample).dump(tmp_path / "debug")
    extracted = {item.logical_path: item for item in summary.extracted}
    file_header = parse_file_header(extracted["FileHeader"].output_path.read_bytes())
    decoded = BodyTextDecoder().decode(
        extracted["BodyText/Section0"].output_path.read_bytes(),
        compressed=file_header.is_compressed,
    )
    records = BodyTextRecordParser().split_records(decoded)
    return ParagraphExtractor().extract(
        source_path="BodyText/Section0",
        records=records,
    )


def test_at_least_one_paragraph_is_found(tmp_path: Path) -> None:
    paragraphs = _extract_paragraphs(find_sample_hwp(), tmp_path)
    assert paragraphs.paragraph_count_all > 0


def test_decoded_text_is_non_empty_for_text_only_sample(tmp_path: Path) -> None:
    paragraphs = _extract_paragraphs(find_sample_hwp("text_only"), tmp_path)
    text_values = [paragraph.text_decoded.strip() for paragraph in paragraphs.paragraphs]
    assert any(text_values)


def test_paragraph_record_ranges_are_valid_and_ordered(tmp_path: Path) -> None:
    paragraphs = _extract_paragraphs(find_sample_hwp(), tmp_path)

    last_index = -1
    for paragraph in paragraphs.paragraphs:
        assert paragraph.record_indices == sorted(paragraph.record_indices)
        assert paragraph.record_indices
        assert paragraph.record_indices[0] > last_index
        last_index = paragraph.record_indices[-1]
        for text_record_index in paragraph.text_record_indices:
            assert text_record_index in paragraph.record_indices


def test_all_paragraph_count_is_not_smaller_than_visible_count(tmp_path: Path) -> None:
    paragraphs = _extract_paragraphs(find_sample_hwp("text_only"), tmp_path)

    assert paragraphs.paragraph_count_all >= paragraphs.paragraph_count_text_only


def test_visible_text_paragraph_count_matches_text_only_sample(tmp_path: Path) -> None:
    paragraphs = _extract_paragraphs(find_sample_hwp("text_only"), tmp_path)

    assert paragraphs.paragraph_count_text_only == 3
