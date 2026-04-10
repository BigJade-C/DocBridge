from __future__ import annotations

from pathlib import Path

from hwp_parser.bodytext import BodyTextDecoder, BodyTextRecordParser
from hwp_parser.file_header import parse_file_header


def find_sample_hwp() -> Path:
    for root_name in ("samples", "hwp_samples"):
        root = Path(root_name)
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.hwp")):
            return path
    raise AssertionError("Expected at least one .hwp sample")


def test_bodytext_can_be_decoded(tmp_path: Path) -> None:
    from hwp_parser.container import HwpContainerDumper

    sample = find_sample_hwp()
    summary = HwpContainerDumper(sample).dump(tmp_path / "debug")
    extracted = {item.logical_path: item for item in summary.extracted}

    file_header = parse_file_header(extracted["FileHeader"].output_path.read_bytes())
    decoded = BodyTextDecoder().decode(
        extracted["BodyText/Section0"].output_path.read_bytes(),
        compressed=file_header.is_compressed,
    )

    assert len(decoded) > 0


def test_bodytext_has_at_least_one_record(tmp_path: Path) -> None:
    from hwp_parser.container import HwpContainerDumper

    sample = find_sample_hwp()
    summary = HwpContainerDumper(sample).dump(tmp_path / "debug")
    extracted = {item.logical_path: item for item in summary.extracted}

    file_header = parse_file_header(extracted["FileHeader"].output_path.read_bytes())
    decoded = BodyTextDecoder().decode(
        extracted["BodyText/Section0"].output_path.read_bytes(),
        compressed=file_header.is_compressed,
    )
    record_summary = BodyTextRecordParser().parse(
        decoded,
        source_path="BodyText/Section0",
    )

    assert record_summary.record_count > 0


def test_record_boundaries_do_not_overflow_decoded_stream(tmp_path: Path) -> None:
    from hwp_parser.container import HwpContainerDumper

    sample = find_sample_hwp()
    summary = HwpContainerDumper(sample).dump(tmp_path / "debug")
    extracted = {item.logical_path: item for item in summary.extracted}

    file_header = parse_file_header(extracted["FileHeader"].output_path.read_bytes())
    decoded = BodyTextDecoder().decode(
        extracted["BodyText/Section0"].output_path.read_bytes(),
        compressed=file_header.is_compressed,
    )
    record_summary = BodyTextRecordParser().parse(
        decoded,
        source_path="BodyText/Section0",
    )

    for index, record in enumerate(record_summary.records):
        payload_start = record.offset + record.header_size
        payload_end = payload_start + record.size
        assert payload_end <= len(decoded), f"record {index} overflowed decoded stream"
