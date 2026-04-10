from __future__ import annotations

import json
import logging
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from string import punctuation

LOGGER = logging.getLogger(__name__)

RECORD_HEADER_SIZE = 4
EXTENDED_SIZE_SENTINEL = 0xFFF
PAYLOAD_PREVIEW_BYTES = 32


@dataclass(frozen=True)
class BodyTextRecord:
    index: int
    offset: int
    tag_id: int
    level: int
    size: int
    header_size: int
    payload_preview_hex: str


@dataclass(frozen=True)
class ParsedBodyTextRecord:
    index: int
    offset: int
    tag_id: int
    level: int
    size: int
    header_size: int
    payload: bytes


@dataclass(frozen=True)
class BodyTextRecordSummary:
    source_path: str
    decoded_size: int
    record_count: int
    records: list[BodyTextRecord]


@dataclass(frozen=True)
class TextDecodingCandidate:
    encoding: str
    offset: int
    text: str
    score: float
    raw_hex: str


@dataclass(frozen=True)
class ParagraphSummary:
    index: int
    paragraph_type: str
    record_indices: list[int]
    text_record_indices: list[int]
    text_raw_hex: str
    text_decoded: str
    candidate_decodings: list[TextDecodingCandidate]


@dataclass(frozen=True)
class ParagraphSummaryDocument:
    source_path: str
    paragraph_count_all: int
    paragraph_count_text_only: int
    paragraphs: list[ParagraphSummary]

    @property
    def visible_text_paragraphs(self) -> list[ParagraphSummary]:
        return [paragraph for paragraph in self.paragraphs if paragraph.paragraph_type == "text_paragraph"]


class BodyTextDecoder:
    def decode(self, payload: bytes, *, compressed: bool) -> bytes:
        if not compressed:
            return payload

        try:
            return zlib.decompress(payload, -15)
        except zlib.error as exc:
            LOGGER.warning("Failed to decompress BodyText stream: %s", exc)
            raise


class BodyTextRecordParser:
    def split_records(self, payload: bytes) -> list[ParsedBodyTextRecord]:
        records: list[ParsedBodyTextRecord] = []
        cursor = 0
        index = 0
        payload_size = len(payload)

        while cursor < payload_size:
            if payload_size - cursor < RECORD_HEADER_SIZE:
                LOGGER.warning(
                    "Truncated record header at offset %d: remaining=%d",
                    cursor,
                    payload_size - cursor,
                )
                break

            header = struct.unpack_from("<I", payload, cursor)[0]
            tag_id = header & 0x3FF
            level = (header >> 10) & 0x3FF
            record_size = (header >> 20) & 0xFFF
            header_size = RECORD_HEADER_SIZE

            if record_size == EXTENDED_SIZE_SENTINEL:
                if payload_size - cursor < RECORD_HEADER_SIZE + 4:
                    LOGGER.warning(
                        "Truncated extended record size at offset %d: remaining=%d",
                        cursor,
                        payload_size - cursor,
                    )
                    break
                record_size = struct.unpack_from("<I", payload, cursor + RECORD_HEADER_SIZE)[0]
                header_size += 4

            payload_offset = cursor + header_size
            record_end = payload_offset + record_size
            if record_end > payload_size:
                LOGGER.warning(
                    "Record overflow at offset %d: end=%d decoded_size=%d",
                    cursor,
                    record_end,
                    payload_size,
                )
                break

            record_payload = payload[payload_offset:record_end]
            records.append(
                ParsedBodyTextRecord(
                    index=index,
                    offset=cursor,
                    tag_id=tag_id,
                    level=level,
                    size=record_size,
                    header_size=header_size,
                    payload=record_payload,
                )
            )
            cursor = record_end
            index += 1

        return records

    def parse(self, payload: bytes, *, source_path: str) -> BodyTextRecordSummary:
        split_records = self.split_records(payload)
        payload_size = len(payload)

        return BodyTextRecordSummary(
            source_path=source_path,
            decoded_size=payload_size,
            record_count=len(split_records),
            records=[
                BodyTextRecord(
                    index=record.index,
                    offset=record.offset,
                    tag_id=record.tag_id,
                    level=record.level,
                    size=record.size,
                    header_size=record.header_size,
                    payload_preview_hex=record.payload[:PAYLOAD_PREVIEW_BYTES].hex(),
                )
                for record in split_records
            ],
        )


class ParagraphGrouper:
    def group(self, records: list[ParsedBodyTextRecord]) -> list[list[ParsedBodyTextRecord]]:
        paragraphs: list[list[ParsedBodyTextRecord]] = []
        current: list[ParsedBodyTextRecord] = []

        for record in records:
            if record.level == 0 and current:
                paragraphs.append(current)
                current = []
            current.append(record)

        if current:
            paragraphs.append(current)
        return paragraphs


class TextPayloadDecoder:
    _encodings = ("utf-16le", "utf-8", "cp949")

    def find_candidates(self, payload: bytes) -> list[TextDecodingCandidate]:
        candidates: list[TextDecodingCandidate] = []
        max_offset = min(len(payload), 32)
        for encoding in self._encodings:
            offsets = range(0, max_offset, 2) if encoding == "utf-16le" else range(0, max_offset)
            for offset in offsets:
                chunk = payload[offset:]
                if len(chunk) < 2:
                    continue
                decoded = chunk.decode(encoding, errors="ignore")
                cleaned = extract_meaningful_text(decoded)
                score = _score_text(cleaned)
                if score <= 0:
                    continue
                raw_hex = _candidate_raw_hex(payload, offset, encoding, cleaned)
                candidates.append(
                    TextDecodingCandidate(
                        encoding=encoding,
                        offset=offset,
                        text=cleaned,
                        score=score,
                        raw_hex=raw_hex,
                    )
                )

        unique: dict[tuple[str, int, str], TextDecodingCandidate] = {}
        for candidate in sorted(candidates, key=_candidate_sort_key):
            key = (candidate.encoding, candidate.offset, candidate.text)
            unique.setdefault(key, candidate)

        ordered = sorted(unique.values(), key=_candidate_sort_key)
        return ordered[:5]


class ParagraphExtractor:
    def __init__(self) -> None:
        self._grouper = ParagraphGrouper()
        self._text_decoder = TextPayloadDecoder()

    def extract(
        self,
        *,
        source_path: str,
        records: list[ParsedBodyTextRecord],
    ) -> ParagraphSummaryDocument:
        grouped = self._grouper.group(records)
        paragraphs: list[ParagraphSummary] = []

        for paragraph_index, paragraph_records in enumerate(grouped):
            paragraph_candidates: list[TextDecodingCandidate] = []
            text_record_indices: list[int] = []
            selected_candidates: list[TextDecodingCandidate] = []

            for record in paragraph_records:
                candidates = self._text_decoder.find_candidates(record.payload)
                if not candidates:
                    continue
                best = candidates[0]
                if best.score < 6:
                    continue
                if (
                    selected_candidates
                    and _hangul_count(selected_candidates[0].text) >= 2
                    and _hangul_count(best.text) == 0
                ):
                    continue
                paragraph_candidates.extend(candidates[:3])
                selected_candidates.append(best)
                text_record_indices.append(record.index)

            paragraph_candidates.sort(key=_candidate_sort_key)
            chosen_texts: list[str] = []
            chosen_hex_parts: list[str] = []
            seen_texts: set[str] = set()
            for candidate in selected_candidates:
                normalized = candidate.text.strip()
                if not normalized or normalized in seen_texts:
                    continue
                seen_texts.add(normalized)
                chosen_texts.append(normalized)
                chosen_hex_parts.append(candidate.raw_hex)

            paragraphs.append(
                ParagraphSummary(
                    index=paragraph_index,
                    paragraph_type=self._classify_paragraph(
                        paragraph_records=paragraph_records,
                        text_record_indices=text_record_indices,
                        text_decoded="\n".join(chosen_texts),
                    ),
                    record_indices=[record.index for record in paragraph_records],
                    text_record_indices=text_record_indices,
                    text_raw_hex="".join(chosen_hex_parts),
                    text_decoded="\n".join(chosen_texts),
                    candidate_decodings=paragraph_candidates[:5],
                )
            )

        return ParagraphSummaryDocument(
            source_path=source_path,
            paragraph_count_all=len(paragraphs),
            paragraph_count_text_only=sum(
                1 for paragraph in paragraphs if paragraph.paragraph_type == "text_paragraph"
            ),
            paragraphs=paragraphs,
        )

    def _classify_paragraph(
        self,
        *,
        paragraph_records: list[ParsedBodyTextRecord],
        text_record_indices: list[int],
        text_decoded: str,
    ) -> str:
        if text_decoded.strip():
            return "text_paragraph"

        tag_ids = {record.tag_id for record in paragraph_records}
        max_level = max((record.level for record in paragraph_records), default=0)
        control_like_tags = {71, 73, 74, 75, 76, 85}

        if tag_ids.issubset({66, 68, 69}) and max_level <= 1:
            return "empty_paragraph"
        if text_record_indices:
            return "unknown_paragraph"
        if tag_ids & control_like_tags or max_level >= 2:
            return "control_paragraph"
        return "unknown_paragraph"


def record_summary_to_json(summary: BodyTextRecordSummary) -> str:
    return json.dumps(
        {
            "source_path": summary.source_path,
            "decoded_size": summary.decoded_size,
            "record_count": summary.record_count,
            "records": [
                {
                    "index": record.index,
                    "offset": record.offset,
                    "tag_id": record.tag_id,
                    "level": record.level,
                    "size": record.size,
                    "header_size": record.header_size,
                    "payload_preview_hex": record.payload_preview_hex,
                }
                for record in summary.records
            ],
        },
        indent=2,
    )


def paragraph_summary_to_json(summary: ParagraphSummaryDocument) -> str:
    return json.dumps(
        {
            "source_path": summary.source_path,
            "paragraph_count_all": summary.paragraph_count_all,
            "paragraph_count_text_only": summary.paragraph_count_text_only,
            "paragraphs": [
                {
                    "index": paragraph.index,
                    "paragraph_type": paragraph.paragraph_type,
                    "record_indices": paragraph.record_indices,
                    "text_record_indices": paragraph.text_record_indices,
                    "text_raw_hex": paragraph.text_raw_hex,
                    "text_decoded": paragraph.text_decoded,
                    "candidate_decodings": [
                        {
                            "encoding": candidate.encoding,
                            "offset": candidate.offset,
                            "text": candidate.text,
                            "score": candidate.score,
                            "raw_hex": candidate.raw_hex,
                        }
                        for candidate in paragraph.candidate_decodings
                    ],
                }
                for paragraph in summary.paragraphs
            ],
            "visible_text_paragraphs": [
                {
                    "index": paragraph.index,
                    "paragraph_type": paragraph.paragraph_type,
                    "text_decoded": paragraph.text_decoded,
                }
                for paragraph in summary.visible_text_paragraphs
            ],
        },
        indent=2,
        ensure_ascii=False,
    )


def write_bodytext_debug_outputs(
    *,
    decoded_payload: bytes,
    record_summary: BodyTextRecordSummary,
    paragraph_summary: ParagraphSummaryDocument,
    decoded_output_path: Path,
    summary_output_path: Path,
    paragraph_output_path: Path,
) -> None:
    decoded_output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_output_path.parent.mkdir(parents=True, exist_ok=True)
    paragraph_output_path.parent.mkdir(parents=True, exist_ok=True)
    decoded_output_path.write_bytes(decoded_payload)
    summary_output_path.write_text(
        record_summary_to_json(record_summary),
        encoding="utf-8",
    )
    paragraph_output_path.write_text(
        paragraph_summary_to_json(paragraph_summary),
        encoding="utf-8",
    )


def strip_control_codes(text: str) -> str:
    preserved = {"\n", "\r", "\t"}
    cleaned = "".join(ch for ch in text if ch in preserved or ch.isprintable())
    cleaned = cleaned.replace("\x00", "")
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in cleaned.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def extract_meaningful_text(text: str) -> str:
    cleaned = strip_control_codes(text)
    if not cleaned:
        return ""

    segments: list[str] = []
    current: list[str] = []
    for ch in cleaned:
        if _is_meaningful_char(ch):
            current.append(ch)
            continue
        if current:
            segments.append("".join(current).strip())
            current = []
    if current:
        segments.append("".join(current).strip())

    valid_segments = [segment for segment in segments if _score_text_segment(segment) > 0]
    if not valid_segments:
        return ""

    valid_segments.sort(key=lambda item: (-_score_text_segment(item), -len(item)))
    return valid_segments[0]


def _score_text(text: str) -> float:
    if not text:
        return 0.0

    hangul = sum(1 for ch in text if "\uac00" <= ch <= "\ud7a3")
    ascii_alnum = sum(1 for ch in text if ch.isascii() and ch.isalnum())
    spaces = text.count(" ")
    allowed_punct = sum(1 for ch in text if ch in punctuation or ch in "·…“”‘’")
    bad = sum(1 for ch in text if not _is_meaningful_char(ch))
    length_bonus = min(len(text), 80) * 0.05

    if hangul >= 2:
        return hangul * 3.0 + ascii_alnum * 0.5 + spaces * 0.2 + allowed_punct * 0.3 + length_bonus - bad * 3.0
    if ascii_alnum < 4:
        return 0.0

    return ascii_alnum * 1.2 + spaces * 0.2 + allowed_punct * 0.3 + length_bonus - bad * 3.0


def _score_text_segment(text: str) -> float:
    hangul = _hangul_count(text)
    ascii_alnum = sum(1 for ch in text if ch.isascii() and ch.isalnum())
    if hangul >= 2:
        return hangul * 3.0 + ascii_alnum * 0.5 + min(len(text), 80) * 0.05
    if ascii_alnum >= 4:
        return ascii_alnum * 1.2 + min(len(text), 80) * 0.05
    return 0.0


def _is_meaningful_char(ch: str) -> bool:
    if ch in "\n\t ":
        return True
    if "\uac00" <= ch <= "\ud7a3":
        return True
    if ch.isascii() and (ch.isalnum() or ch in punctuation):
        return True
    return False


def _hangul_count(text: str) -> int:
    return sum(1 for ch in text if "\uac00" <= ch <= "\ud7a3")


def _candidate_raw_hex(payload: bytes, offset: int, encoding: str, cleaned_text: str) -> str:
    if encoding == "utf-16le":
        encoded = cleaned_text.replace("\n", "\r\n").encode("utf-16le", errors="ignore")
    else:
        encoded = cleaned_text.encode(encoding, errors="ignore")

    if not encoded:
        return payload[offset: offset + min(32, len(payload) - offset)].hex()

    found_at = payload[offset:].find(encoded)
    if found_at >= 0:
        start = offset + found_at
        end = start + len(encoded)
        return payload[start:end].hex()

    end = offset + len(encoded)
    return payload[offset:end].hex()


def _candidate_sort_key(candidate: TextDecodingCandidate) -> tuple[float, float, int, int]:
    encoding_priority = 0 if candidate.encoding == "utf-16le" else 1
    return (encoding_priority, -candidate.score, candidate.offset, -len(candidate.text))
