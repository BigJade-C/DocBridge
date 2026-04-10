from __future__ import annotations

import json
import logging
import struct
from dataclasses import dataclass

from .bodytext import ParagraphSummary, ParagraphSummaryDocument, ParsedBodyTextRecord

LOGGER = logging.getLogger(__name__)

DOCINFO_TAG_CHAR_SHAPE = 21
DOCINFO_TAG_PARA_SHAPE = 25
BODYTEXT_TAG_PARA_HEADER = 66
BODYTEXT_TAG_PARA_TEXT = 67
BODYTEXT_TAG_CHAR_SHAPE = 68


@dataclass(frozen=True)
class ParagraphStyleAnalysis:
    alignment: str | None
    style_ref: int | None
    raw: dict[str, object]


@dataclass(frozen=True)
class CharacterStyleAnalysis:
    bold: bool | None
    font_size_pt: float | None
    style_ref: int | None
    raw: dict[str, object]


@dataclass(frozen=True)
class TextRunAnalysis:
    text: str
    char_style_ref: int | None
    char_style: CharacterStyleAnalysis


@dataclass(frozen=True)
class StyledParagraphAnalysis:
    index: int
    paragraph_type: str
    text_decoded: str
    record_indices: list[int]
    paragraph_style_ref: int | None
    char_style_ref: int | None
    paragraph_style: ParagraphStyleAnalysis
    text_runs: list[TextRunAnalysis]


@dataclass(frozen=True)
class StyleAnalysisDocument:
    source_path: str
    paragraph_count_all: int
    paragraph_count_text_only: int
    paragraphs: list[StyledParagraphAnalysis]


@dataclass(frozen=True)
class DocInfoStyleTables:
    paragraph_shapes: dict[int, ParagraphStyleAnalysis]
    character_shapes: dict[int, CharacterStyleAnalysis]


class DocInfoStyleResolver:
    def build_tables(self, records: list[ParsedBodyTextRecord]) -> DocInfoStyleTables:
        paragraph_shapes: dict[int, ParagraphStyleAnalysis] = {}
        character_shapes: dict[int, CharacterStyleAnalysis] = {}

        para_shape_index = 0
        char_shape_index = 0
        for record in records:
            if record.tag_id == DOCINFO_TAG_PARA_SHAPE:
                paragraph_shapes[para_shape_index] = self._parse_paragraph_shape(record.payload)
                para_shape_index += 1
            elif record.tag_id == DOCINFO_TAG_CHAR_SHAPE:
                character_shapes[char_shape_index] = self._parse_character_shape(record.payload)
                char_shape_index += 1

        return DocInfoStyleTables(
            paragraph_shapes=paragraph_shapes,
            character_shapes=character_shapes,
        )

    def _parse_paragraph_shape(self, payload: bytes) -> ParagraphStyleAnalysis:
        values = _u32_list(payload)
        style_ref = None
        alignment = None
        if values:
            raw_flags = values[0]
            style_ref = None
            alignment_code = raw_flags & 0x0C
            alignment = {
                0x04: "left",
                0x08: "right",
                0x0C: "center",
            }.get(alignment_code)

        return ParagraphStyleAnalysis(
            alignment=alignment,
            style_ref=style_ref,
            raw={
                "payload_hex": payload.hex(),
                "u32": values[:12],
            },
        )

    def _parse_character_shape(self, payload: bytes) -> CharacterStyleAnalysis:
        values = _u32_list(payload)
        bold = None
        font_size_pt = None
        if len(values) > 10:
            # HWP char shape stores point size in 1/100 pt, packed into a fixed-point slot.
            font_size_hwp = values[10] // 65536
            font_size_pt = round(font_size_hwp / 100, 2)
        if len(values) > 11:
            bold = bool(values[11] & 0x00020000)

        return CharacterStyleAnalysis(
            bold=bold,
            font_size_pt=font_size_pt,
            style_ref=None,
            raw={
                "payload_hex": payload.hex(),
                "u32": values[:18],
            },
        )


class ParagraphStyleAnalyzer:
    def analyze(
        self,
        *,
        paragraph_summary: ParagraphSummaryDocument,
        bodytext_records: list[ParsedBodyTextRecord],
        docinfo_records: list[ParsedBodyTextRecord],
    ) -> StyleAnalysisDocument:
        tables = DocInfoStyleResolver().build_tables(docinfo_records)
        body_records_by_index = {record.index: record for record in bodytext_records}

        paragraphs: list[StyledParagraphAnalysis] = []
        for paragraph in paragraph_summary.paragraphs:
            paragraph_style_ref = _extract_paragraph_style_ref(paragraph, body_records_by_index)
            char_style_ref = _extract_char_style_ref(paragraph, body_records_by_index)

            paragraph_style = self._resolve_paragraph_style(
                paragraph_style_ref,
                tables.paragraph_shapes,
            )
            char_style = self._resolve_character_style(
                char_style_ref,
                tables.character_shapes,
            )

            text_runs: list[TextRunAnalysis] = []
            if paragraph.text_decoded:
                text_runs.append(
                    TextRunAnalysis(
                        text=paragraph.text_decoded,
                        char_style_ref=char_style_ref,
                        char_style=char_style,
                    )
                )

            paragraphs.append(
                StyledParagraphAnalysis(
                    index=paragraph.index,
                    paragraph_type=paragraph.paragraph_type,
                    text_decoded=paragraph.text_decoded,
                    record_indices=paragraph.record_indices,
                    paragraph_style_ref=paragraph_style_ref,
                    char_style_ref=char_style_ref,
                    paragraph_style=paragraph_style,
                    text_runs=text_runs,
                )
            )

        return StyleAnalysisDocument(
            source_path=paragraph_summary.source_path,
            paragraph_count_all=paragraph_summary.paragraph_count_all,
            paragraph_count_text_only=paragraph_summary.paragraph_count_text_only,
            paragraphs=paragraphs,
        )

    def _resolve_paragraph_style(
        self,
        style_ref: int | None,
        paragraph_shapes: dict[int, ParagraphStyleAnalysis],
    ) -> ParagraphStyleAnalysis:
        if style_ref is None:
            return ParagraphStyleAnalysis(alignment=None, style_ref=None, raw={})

        resolved = paragraph_shapes.get(style_ref)
        if resolved is None:
            return ParagraphStyleAnalysis(
                alignment=None,
                style_ref=style_ref,
                raw={},
            )

        return ParagraphStyleAnalysis(
            alignment=resolved.alignment,
            style_ref=style_ref,
            raw=resolved.raw,
        )

    def _resolve_character_style(
        self,
        style_ref: int | None,
        character_shapes: dict[int, CharacterStyleAnalysis],
    ) -> CharacterStyleAnalysis:
        if style_ref is None:
            return CharacterStyleAnalysis(
                bold=None,
                font_size_pt=None,
                style_ref=None,
                raw={},
            )

        resolved = character_shapes.get(style_ref)
        if resolved is None:
            return CharacterStyleAnalysis(
                bold=None,
                font_size_pt=None,
                style_ref=style_ref,
                raw={},
            )

        return CharacterStyleAnalysis(
            bold=resolved.bold,
            font_size_pt=resolved.font_size_pt,
            style_ref=style_ref,
            raw=resolved.raw,
        )


def style_analysis_to_json(document: StyleAnalysisDocument) -> str:
    return json.dumps(
        {
            "source_path": document.source_path,
            "paragraph_count_all": document.paragraph_count_all,
            "paragraph_count_text_only": document.paragraph_count_text_only,
            "paragraphs": [
                {
                    "index": paragraph.index,
                    "paragraph_type": paragraph.paragraph_type,
                    "text_decoded": paragraph.text_decoded,
                    "record_indices": paragraph.record_indices,
                    "paragraph_style_ref": paragraph.paragraph_style_ref,
                    "char_style_ref": paragraph.char_style_ref,
                    "paragraph_style": {
                        "alignment": paragraph.paragraph_style.alignment,
                        "style_ref": paragraph.paragraph_style.style_ref,
                        "raw": paragraph.paragraph_style.raw,
                    },
                    "text_runs": [
                        {
                            "text": run.text,
                            "char_style_ref": run.char_style_ref,
                            "char_style": {
                                "bold": run.char_style.bold,
                                "font_size_pt": run.char_style.font_size_pt,
                                "style_ref": run.char_style.style_ref,
                                "raw": run.char_style.raw,
                            },
                        }
                        for run in paragraph.text_runs
                    ],
                }
                for paragraph in document.paragraphs
            ],
        },
        indent=2,
        ensure_ascii=False,
    )


def style_tables_to_json(tables: DocInfoStyleTables) -> str:
    return json.dumps(
        {
            "paragraph_shapes": {
                str(style_ref): {
                    "alignment": style.alignment,
                    "style_ref": style_ref,
                    "raw": style.raw,
                }
                for style_ref, style in tables.paragraph_shapes.items()
            },
            "character_shapes": {
                str(style_ref): {
                    "bold": style.bold,
                    "font_size_pt": style.font_size_pt,
                    "style_ref": style_ref,
                    "raw": style.raw,
                }
                for style_ref, style in tables.character_shapes.items()
            },
        },
        indent=2,
        ensure_ascii=False,
    )


def _u32_list(payload: bytes) -> list[int]:
    usable = len(payload) // 4 * 4
    return [struct.unpack_from("<I", payload, offset)[0] for offset in range(0, usable, 4)]


def _extract_paragraph_style_ref(
    paragraph: ParagraphSummary,
    body_records_by_index: dict[int, ParsedBodyTextRecord],
) -> int | None:
    for record_index in paragraph.record_indices:
        record = body_records_by_index[record_index]
        if record.tag_id != BODYTEXT_TAG_PARA_HEADER or len(record.payload) < 12:
            continue
        raw_ref = struct.unpack_from("<I", record.payload, 8)[0]
        return raw_ref & 0xFFFF
    return None


def _extract_char_style_ref(
    paragraph: ParagraphSummary,
    body_records_by_index: dict[int, ParsedBodyTextRecord],
) -> int | None:
    for record_index in paragraph.record_indices:
        record = body_records_by_index[record_index]
        if record.tag_id != BODYTEXT_TAG_CHAR_SHAPE or len(record.payload) < 8:
            continue
        return struct.unpack_from("<I", record.payload, 4)[0]
    return None
