from __future__ import annotations

import json
import struct
from dataclasses import dataclass
import re

from .bodytext import ParagraphExtractor, ParagraphGrouper, ParsedBodyTextRecord, TextPayloadDecoder, strip_control_codes
from .style_analysis import ParagraphStyleAnalyzer


@dataclass(frozen=True)
class TableCellSummary:
    index: int
    row_index: int
    column_index: int
    colspan: int
    rowspan: int
    record_indices: list[int]
    text: str
    source_record_index: int
    raw: dict[str, object]


@dataclass(frozen=True)
class TableRowSummary:
    index: int
    cells: list[TableCellSummary]


@dataclass(frozen=True)
class ParagraphBlockSummary:
    index: int
    block_type: str
    paragraph_type: str
    text_decoded: str
    record_indices: list[int]
    paragraph_style_ref: int | None
    char_style_ref: int | None
    list_info: dict[str, object] | None
    paragraph_style: dict[str, object]
    text_runs: list[dict[str, object]]
    text_origin: str | None
    raw: dict[str, object]


@dataclass(frozen=True)
class TableBlockSummary:
    index: int
    block_type: str
    row_count: int
    column_count: int
    record_indices: list[int]
    rows: list[TableRowSummary]


@dataclass(frozen=True)
class ImageBlockSummary:
    index: int
    block_type: str
    record_indices: list[int]
    source_record_index: int
    source_ref: str
    binary_stream_ref: str | None
    width: int | None
    height: int | None
    placement: str | None
    alt_text: str | None
    original_filename: str | None
    original_size_text: str | None
    raw: dict[str, object]


@dataclass(frozen=True)
class BodyTextBlockDocument:
    source_path: str
    blocks: list[object]
    header_blocks: list[object]
    footer_blocks: list[object]


class BodyTextBlockAnalyzer:
    def __init__(self) -> None:
        self._paragraph_extractor = ParagraphExtractor()
        self._paragraph_grouper = ParagraphGrouper()
        self._paragraph_style_analyzer = ParagraphStyleAnalyzer()
        self._text_decoder = TextPayloadDecoder()

    def analyze(
        self,
        *,
        source_path: str,
        bodytext_records: list[ParsedBodyTextRecord],
        docinfo_records: list[ParsedBodyTextRecord],
        bin_data_refs: list[str] | None = None,
        bin_data_output_paths: dict[str, str] | None = None,
    ) -> BodyTextBlockDocument:
        header_footer = self._extract_header_footer_sections(
            source_path=source_path,
            bodytext_records=bodytext_records,
            docinfo_records=docinfo_records,
        )
        body_records = [
            record for record in bodytext_records
            if record.index not in header_footer.consumed_record_indices
        ]

        blocks: list[object] = []
        cursor = 0
        block_index = 0
        bin_data_refs = bin_data_refs or []
        bin_data_output_paths = bin_data_output_paths or {}

        while cursor < len(body_records):
            image_start = self._find_next_image_start(body_records, cursor)
            table_start = self._find_next_table_start(body_records, cursor)

            next_special = _pick_next_index(image_start, table_start)
            if next_special is None:
                paragraph_blocks = self._build_paragraph_blocks(
                    block_index=block_index,
                    source_path=source_path,
                    bodytext_records=body_records[cursor:],
                    docinfo_records=docinfo_records,
                )
                blocks.extend(paragraph_blocks)
                break

            if next_special > cursor:
                paragraph_blocks = self._build_paragraph_blocks(
                    block_index=block_index,
                    source_path=source_path,
                    bodytext_records=body_records[cursor:next_special],
                    docinfo_records=docinfo_records,
                )
                if image_start is not None and next_special == image_start:
                    paragraph_blocks = self._filter_noise_paragraphs_before_image(
                        paragraph_blocks=paragraph_blocks,
                        bodytext_records=body_records,
                    )
                if table_start is not None and next_special == table_start:
                    paragraph_blocks = self._filter_empty_paragraphs_before_table(paragraph_blocks)
                blocks.extend(paragraph_blocks)
                block_index += len(paragraph_blocks)

            if image_start is not None and image_start == next_special:
                image_related = self._build_image_blocks(
                    block_index=block_index,
                    source_path=source_path,
                    bodytext_records=body_records,
                    image_start=image_start,
                    bin_data_refs=bin_data_refs,
                    bin_data_output_paths=bin_data_output_paths,
                )
                blocks.extend(image_related.blocks)
                block_index += len(image_related.blocks)
                cursor = image_related.next_cursor
            else:
                table_block, next_cursor = self._build_table_block(
                    block_index=block_index,
                    bodytext_records=body_records,
                    table_start=table_start,
                )
                blocks.append(table_block)
                block_index += 1
                cursor = next_cursor

        blocks = self._cleanup_blocks(blocks)

        return BodyTextBlockDocument(
            source_path=source_path,
            blocks=blocks,
            header_blocks=header_footer.header_blocks,
            footer_blocks=header_footer.footer_blocks,
        )

    @staticmethod
    def _cleanup_blocks(blocks: list[object]) -> list[object]:
        has_special_blocks = any(isinstance(block, (TableBlockSummary, ImageBlockSummary)) for block in blocks)
        cleaned = list(blocks)

        if has_special_blocks:
            cleaned = [
                block
                for block in cleaned
                if not (
                    isinstance(block, ParagraphBlockSummary)
                    and not block.text_decoded.strip()
                )
            ]

        non_image_control_paragraphs = [
            block
            for block in cleaned
            if isinstance(block, ParagraphBlockSummary)
            and block.text_decoded.strip()
            and block.text_origin != "image_control_visible_text"
        ]
        if non_image_control_paragraphs:
            filtered: list[object] = []
            for index, block in enumerate(cleaned):
                if not (
                    isinstance(block, ParagraphBlockSummary)
                    and block.text_origin == "image_control_visible_text"
                    and index + 1 < len(cleaned)
                    and isinstance(cleaned[index + 1], ImageBlockSummary)
                ):
                    filtered.append(block)
            cleaned = filtered

        for index, block in enumerate(cleaned):
            if isinstance(block, (ParagraphBlockSummary, TableBlockSummary, ImageBlockSummary)):
                object.__setattr__(block, "index", index)
        return cleaned

    def _extract_header_footer_sections(
        self,
        *,
        source_path: str,
        bodytext_records: list[ParsedBodyTextRecord],
        docinfo_records: list[ParsedBodyTextRecord],
    ):
        header_blocks: list[object] = []
        footer_blocks: list[object] = []
        consumed: set[int] = set()
        record_count = len(bodytext_records)

        for index, record in enumerate(bodytext_records):
            if record.index in consumed or record.tag_id != 71 or record.level != 1:
                continue

            control_kind = _extract_header_footer_control_kind(record.payload)
            if control_kind is None:
                continue

            cursor = index + 1
            region_records: list[ParsedBodyTextRecord] = []
            consumed.add(record.index)

            if cursor < record_count and bodytext_records[cursor].tag_id == 72 and bodytext_records[cursor].level == 2:
                consumed.add(bodytext_records[cursor].index)
                cursor += 1

            while cursor < record_count and bodytext_records[cursor].level >= 2:
                region_records.append(bodytext_records[cursor])
                consumed.add(bodytext_records[cursor].index)
                cursor += 1

            if not region_records:
                continue

            section_source_path = f"{source_path}/{control_kind.capitalize()}"
            section_blocks = self._build_section_paragraph_blocks(
                block_index=0,
                source_path=section_source_path,
                paragraph_records=region_records,
                docinfo_records=docinfo_records,
            )
            if control_kind == "header":
                header_blocks = section_blocks
            else:
                footer_blocks = section_blocks

        return _HeaderFooterExtractionResult(
            header_blocks=header_blocks,
            footer_blocks=footer_blocks,
            consumed_record_indices=consumed,
        )

    def _build_section_paragraph_blocks(
        self,
        *,
        block_index: int,
        source_path: str,
        paragraph_records: list[ParsedBodyTextRecord],
        docinfo_records: list[ParsedBodyTextRecord],
    ) -> list[ParagraphBlockSummary]:
        grouped_records = self._paragraph_grouper.group(paragraph_records)
        paragraph_summary = self._paragraph_extractor.extract(
            source_path=source_path,
            records=paragraph_records,
        )
        style_summary = self._paragraph_style_analyzer.analyze(
            paragraph_summary=paragraph_summary,
            bodytext_records=paragraph_records,
            docinfo_records=docinfo_records,
        )

        blocks: list[ParagraphBlockSummary] = []
        for offset, (styled_paragraph, group_records) in enumerate(zip(style_summary.paragraphs, grouped_records)):
            text_runs = self._build_runs_from_records(
                group_records,
                default_char_style_ref=styled_paragraph.char_style_ref,
                default_char_style_raw=styled_paragraph.text_runs[0].char_style.raw if styled_paragraph.text_runs else {},
                default_char_style_bold=styled_paragraph.text_runs[0].char_style.bold if styled_paragraph.text_runs else None,
                default_char_style_font_size_pt=styled_paragraph.text_runs[0].char_style.font_size_pt if styled_paragraph.text_runs else None,
            )
            visible_text = "".join(
                (run.get("resolved_text") if run.get("kind") == "field" else run.get("text", "")) or ""
                for run in text_runs
            )
            blocks.append(
                ParagraphBlockSummary(
                    index=block_index + offset,
                    block_type="paragraph",
                    paragraph_type=styled_paragraph.paragraph_type,
                    text_decoded=visible_text or styled_paragraph.text_decoded,
                    record_indices=styled_paragraph.record_indices,
                    paragraph_style_ref=styled_paragraph.paragraph_style_ref,
                    char_style_ref=styled_paragraph.char_style_ref,
                    list_info=None,
                    paragraph_style={
                        "alignment": styled_paragraph.paragraph_style.alignment,
                        "style_ref": styled_paragraph.paragraph_style.style_ref,
                        "raw": styled_paragraph.paragraph_style.raw,
                    },
                    text_runs=text_runs,
                    text_origin="bodytext_paragraph_records",
                    raw={
                        "source_record_tags": [record.tag_id for record in group_records],
                    },
                )
            )
        return blocks

    def _build_runs_from_records(
        self,
        records: list[ParsedBodyTextRecord],
        *,
        default_char_style_ref: int | None,
        default_char_style_raw: dict[str, object],
        default_char_style_bold: bool | None,
        default_char_style_font_size_pt: float | None,
    ) -> list[dict[str, object]]:
        runs: list[dict[str, object]] = []
        has_field_run = any(record.tag_id == 71 and record.level >= 3 for record in records)
        for record in records:
            if record.tag_id == 67:
                text = self._extract_record_text(record)
                if not text:
                    continue
                if has_field_run and b"\x20\x00" in record.payload and not text.endswith(" "):
                    text = f"{text} "
                runs.append(
                    {
                        "kind": "text",
                        "text": text,
                        "char_style_ref": default_char_style_ref,
                        "char_style": {
                            "bold": default_char_style_bold,
                            "font_size_pt": default_char_style_font_size_pt,
                            "style_ref": default_char_style_ref,
                            "raw": default_char_style_raw,
                        },
                        "raw": {
                            "record_index": record.index,
                            "tag_id": record.tag_id,
                            "payload_hex": record.payload.hex(),
                        },
                    }
                )
            elif record.tag_id == 71 and record.level >= 3:
                field_run = _parse_control_field_run(record)
                if field_run is not None:
                    runs.append(field_run)
        return runs

    def _extract_record_text(self, record: ParsedBodyTextRecord) -> str:
        direct_text = strip_control_codes(record.payload.decode("utf-16le", errors="ignore"))
        candidates = self._text_decoder.find_candidates(record.payload)
        if candidates:
            candidate_text = candidates[0].text
            if _has_suspicious_text_artifacts(direct_text) or len(candidate_text) >= len(direct_text.strip()):
                return candidate_text
        return direct_text

    def _build_paragraph_blocks(
        self,
        *,
        block_index: int,
        source_path: str,
        bodytext_records: list[ParsedBodyTextRecord],
        docinfo_records: list[ParsedBodyTextRecord],
    ) -> list[ParagraphBlockSummary]:
        if not bodytext_records:
            return []

        paragraph_summary = self._paragraph_extractor.extract(
            source_path=source_path,
            records=bodytext_records,
        )
        style_summary = self._paragraph_style_analyzer.analyze(
            paragraph_summary=paragraph_summary,
            bodytext_records=bodytext_records,
            docinfo_records=docinfo_records,
        )

        blocks: list[ParagraphBlockSummary] = []
        for offset, paragraph in enumerate(style_summary.paragraphs):
            source_tags = [
                record.tag_id
                for record in bodytext_records
                if record.index in paragraph.record_indices
            ]
            list_info = _infer_list_info(paragraph.paragraph_style_ref, paragraph.paragraph_style.raw)
            blocks.append(
                ParagraphBlockSummary(
                    index=block_index + offset,
                    block_type="paragraph",
                    paragraph_type=paragraph.paragraph_type,
                    text_decoded=paragraph.text_decoded,
                    record_indices=paragraph.record_indices,
                    paragraph_style_ref=paragraph.paragraph_style_ref,
                    char_style_ref=paragraph.char_style_ref,
                    list_info=list_info,
                    paragraph_style={
                        "alignment": paragraph.paragraph_style.alignment,
                        "style_ref": paragraph.paragraph_style.style_ref,
                        "raw": paragraph.paragraph_style.raw,
                    },
                    text_runs=[
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
                    text_origin="bodytext_paragraph_records",
                    raw={
                        "source_record_tags": source_tags,
                    },
                )
            )
        return _populate_list_markers(blocks)

    def _filter_noise_paragraphs_before_image(
        self,
        *,
        paragraph_blocks: list[ParagraphBlockSummary],
        bodytext_records: list[ParsedBodyTextRecord],
    ) -> list[ParagraphBlockSummary]:
        record_map = {record.index: record for record in bodytext_records}
        filtered: list[ParagraphBlockSummary] = []
        control_like_tags = {71, 73, 74, 75, 76, 85}

        for block in paragraph_blocks:
            has_hangul = any("\uac00" <= char <= "\ud7a3" for char in block.text_decoded)
            tags = {
                record_map[record_index].tag_id
                for record_index in block.record_indices
                if record_index in record_map
            }
            if not has_hangul and tags & control_like_tags:
                continue
            if (
                not has_hangul
                and len(block.text_decoded.strip()) <= 32
                and not any(char.isdigit() for char in block.text_decoded)
            ):
                continue
            filtered.append(block)

        return filtered

    @staticmethod
    def _filter_empty_paragraphs_before_table(
        paragraph_blocks: list[ParagraphBlockSummary],
    ) -> list[ParagraphBlockSummary]:
        filtered = list(paragraph_blocks)
        while filtered and not filtered[-1].text_decoded.strip():
            filtered.pop()
        return filtered

    def _build_table_block(
        self,
        *,
        block_index: int,
        bodytext_records: list[ParsedBodyTextRecord],
        table_start: int,
    ) -> tuple[TableBlockSummary, int]:
        table_header = bodytext_records[table_start + 1]
        header_u16 = _u16_list(table_header.payload)
        cell_count = header_u16[0] if len(header_u16) > 0 else 0
        row_count = header_u16[2] if len(header_u16) > 2 else 0
        column_count = header_u16[3] if len(header_u16) > 3 else 0

        cells: list[TableCellSummary] = []
        cursor = table_start + 2
        last_consumed = table_start + 1
        cell_index = 0

        while cursor < len(bodytext_records) and len(cells) < cell_count:
            record = bodytext_records[cursor]
            if record.tag_id != 72 or record.level != 2:
                cursor += 1
                continue

            cell_records = [record]
            cursor += 1
            while cursor < len(bodytext_records):
                next_record = bodytext_records[cursor]
                if next_record.level < 2:
                    break
                if next_record.tag_id == 72 and next_record.level == 2:
                    break
                cell_records.append(next_record)
                cursor += 1

            cell_u16 = _u16_list(record.payload)
            row_index = cell_u16[5] if len(cell_u16) > 5 else 0
            column_index = cell_u16[4] if len(cell_u16) > 4 else cell_index
            colspan = cell_u16[6] if len(cell_u16) > 6 and cell_u16[6] > 0 else 1
            rowspan = cell_u16[7] if len(cell_u16) > 7 and cell_u16[7] > 0 else 1

            text = self._extract_cell_text(cell_records)
            cells.append(
                TableCellSummary(
                    index=cell_index,
                    row_index=row_index,
                    column_index=column_index,
                    colspan=colspan,
                    rowspan=rowspan,
                    record_indices=[item.index for item in cell_records],
                    text=text,
                    source_record_index=record.index,
                    raw={
                        "payload_hex": record.payload.hex(),
                        "u16": cell_u16[:24],
                    },
                )
            )
            last_consumed = cell_records[-1].index
            cell_index += 1

        next_cursor = last_consumed + 1
        next_cursor = self._consume_trailing_empty_paragraph(bodytext_records, next_cursor)

        cells.sort(key=lambda item: (item.row_index, item.column_index, item.index))
        rows: list[TableRowSummary] = []
        for row_index in range(row_count):
            row_cells = [cell for cell in cells if cell.row_index == row_index]
            rows.append(TableRowSummary(index=row_index, cells=row_cells))

        return (
            TableBlockSummary(
                index=block_index,
                block_type="table",
                row_count=row_count,
                column_count=column_count,
                record_indices=list(range(bodytext_records[table_start].index, next_cursor)),
                rows=rows,
            ),
            next_cursor,
        )

    def _build_image_blocks(
        self,
        *,
        block_index: int,
        source_path: str,
        bodytext_records: list[ParsedBodyTextRecord],
        image_start: int,
        bin_data_refs: list[str],
        bin_data_output_paths: dict[str, str],
    ):
        image_records = [bodytext_records[image_start]]
        cursor = image_start + 1
        while cursor < len(bodytext_records):
            record = bodytext_records[cursor]
            if record.level < 1:
                break
            image_records.append(record)
            cursor += 1

        metadata_record = _pick_image_metadata_record(image_records)
        decoded_metadata = strip_control_codes(metadata_record.payload.decode("utf-16le", errors="ignore"))
        metadata_lines = _extract_image_metadata_lines(decoded_metadata)
        visible_text_lines = _extract_image_visible_text_lines(metadata_lines)
        alt_text = _extract_image_alt_text(metadata_lines)
        original_filename = _extract_original_filename(metadata_lines)
        original_size_text = _extract_original_size_text(metadata_lines)

        width, height = _extract_image_dimensions(image_records, metadata_lines)

        blocks: list[object] = []
        next_index = block_index
        if visible_text_lines:
            visible_text = "\n".join(visible_text_lines).strip()
            blocks.append(
                ParagraphBlockSummary(
                    index=next_index,
                    block_type="paragraph",
                    paragraph_type="text_paragraph",
                    text_decoded=visible_text,
                    record_indices=[metadata_record.index],
                    paragraph_style_ref=0,
                    char_style_ref=0,
                    list_info=None,
                    paragraph_style={"alignment": None, "style_ref": 0, "raw": {}},
                    text_runs=[
                        {
                            "text": visible_text,
                            "char_style_ref": 0,
                            "char_style": {
                                "bold": None,
                                "font_size_pt": None,
                                "style_ref": 0,
                                "raw": {},
                            },
                        }
                    ],
                    text_origin="image_control_visible_text",
                    raw={
                        "source_record_tags": [metadata_record.tag_id],
                        "metadata_lines": metadata_lines,
                    },
                )
            )
            next_index += 1

        binary_stream_ref = bin_data_refs[0] if bin_data_refs else None
        image_block = ImageBlockSummary(
            index=next_index,
            block_type="image",
            record_indices=[record.index for record in image_records],
            source_record_index=metadata_record.index,
            source_ref=f"{source_path}:{metadata_record.index}",
            binary_stream_ref=binary_stream_ref,
            width=width,
            height=height,
            placement=None,
            alt_text=alt_text,
            original_filename=original_filename,
            original_size_text=original_size_text,
            raw={
                "payload_hex": metadata_record.payload.hex(),
                "metadata_lines": metadata_lines,
                "visible_text_lines": visible_text_lines,
                "binary_output_path": (
                    bin_data_output_paths.get(binary_stream_ref)
                    if binary_stream_ref is not None
                    else None
                ),
            },
        )
        blocks.append(image_block)

        return _ImageBuildResult(blocks=blocks, next_cursor=cursor)

    def _extract_cell_text(self, cell_records: list[ParsedBodyTextRecord]) -> str:
        chunks: list[str] = []
        for record in cell_records:
            if record.tag_id != 67:
                continue
            direct_text = strip_control_codes(record.payload.decode("utf-16le", errors="ignore"))
            if direct_text:
                chunks.append(direct_text)
                continue
            candidates = self._text_decoder.find_candidates(record.payload)
            if not candidates:
                continue
            chunks.append(candidates[0].text)
        return "\n".join(chunk for chunk in chunks if chunk).strip()

    @staticmethod
    def _find_next_table_start(records: list[ParsedBodyTextRecord], start: int) -> int | None:
        for index in range(start, len(records) - 1):
            record = records[index]
            next_record = records[index + 1]
            if record.tag_id == 71 and next_record.tag_id == 77 and next_record.level == 2:
                return index
        return None

    @staticmethod
    def _find_next_image_start(records: list[ParsedBodyTextRecord], start: int) -> int | None:
        for index in range(start, len(records) - 2):
            record = records[index]
            if record.tag_id != 71 or record.level != 1:
                continue
            if index + 1 < len(records):
                next_record = records[index + 1]
                if next_record.tag_id == 77 and next_record.level == 2:
                    continue

            window = records[index:min(len(records), index + 12)]
            has_image_payload = any(
                candidate.tag_id == 76 and candidate.level == 2
                for candidate in window
            )
            has_shape_component = any(
                candidate.tag_id == 85 and candidate.level >= 3
                for candidate in window
            )
            if has_image_payload and has_shape_component:
                return index
        return None

    def _consume_trailing_empty_paragraph(
        self,
        records: list[ParsedBodyTextRecord],
        cursor: int,
    ) -> int:
        if cursor >= len(records):
            return cursor
        region: list[ParsedBodyTextRecord] = []
        probe = cursor
        while probe < len(records):
            record = records[probe]
            if record.level == 0 and region:
                break
            region.append(record)
            probe += 1

        if not region:
            return cursor

        paragraph_summary = self._paragraph_extractor.extract(
            source_path="BodyText/Section0",
            records=region,
        )
        if (
            len(paragraph_summary.paragraphs) == 1
            and paragraph_summary.paragraphs[0].paragraph_type == "empty_paragraph"
        ):
            return probe
        return cursor


def block_document_to_json(document: BodyTextBlockDocument) -> str:
    return json.dumps(
        {
            "source_path": document.source_path,
            "header": {
                "blocks": [
                    _block_to_dict(block)
                    for block in document.header_blocks
                ]
            } if document.header_blocks else None,
            "footer": {
                "blocks": [
                    _block_to_dict(block)
                    for block in document.footer_blocks
                ]
            } if document.footer_blocks else None,
            "blocks": [
                _block_to_dict(block)
                for block in document.blocks
            ],
        },
        indent=2,
        ensure_ascii=False,
    )


def _block_to_dict(block: object) -> dict[str, object]:
    if isinstance(block, ParagraphBlockSummary):
        return {
            "index": block.index,
            "block_type": block.block_type,
            "paragraph_type": block.paragraph_type,
            "text_decoded": block.text_decoded,
            "record_indices": block.record_indices,
            "paragraph_style_ref": block.paragraph_style_ref,
            "char_style_ref": block.char_style_ref,
            "list_info": block.list_info,
            "paragraph_style": block.paragraph_style,
            "text_runs": block.text_runs,
            "text_origin": block.text_origin,
            "raw": block.raw,
        }
    if isinstance(block, TableBlockSummary):
        return {
            "index": block.index,
            "block_type": block.block_type,
            "row_count": block.row_count,
            "column_count": block.column_count,
            "record_indices": block.record_indices,
            "rows": [
                {
                    "index": row.index,
                    "cells": [
                        {
                            "index": cell.index,
                            "row_index": cell.row_index,
                            "column_index": cell.column_index,
                            "colspan": cell.colspan,
                            "rowspan": cell.rowspan,
                            "record_indices": cell.record_indices,
                            "source_record_index": cell.source_record_index,
                            "text": cell.text,
                            "raw": cell.raw,
                        }
                        for cell in row.cells
                    ],
                }
                for row in block.rows
            ],
        }
    if isinstance(block, ImageBlockSummary):
        return {
            "index": block.index,
            "block_type": block.block_type,
            "record_indices": block.record_indices,
            "source_record_index": block.source_record_index,
            "source_ref": block.source_ref,
            "binary_stream_ref": block.binary_stream_ref,
            "width": block.width,
            "height": block.height,
            "placement": block.placement,
            "alt_text": block.alt_text,
            "original_filename": block.original_filename,
            "original_size_text": block.original_size_text,
            "raw": block.raw,
        }
    raise TypeError(f"Unsupported block type: {type(block)!r}")


def _u16_list(payload: bytes) -> list[int]:
    usable = len(payload) // 2 * 2
    return [struct.unpack_from("<H", payload, offset)[0] for offset in range(0, usable, 2)]


@dataclass(frozen=True)
class _ImageBuildResult:
    blocks: list[object]
    next_cursor: int


@dataclass(frozen=True)
class _HeaderFooterExtractionResult:
    header_blocks: list[object]
    footer_blocks: list[object]
    consumed_record_indices: set[int]


def _pick_next_index(*values: int | None) -> int | None:
    non_null = [value for value in values if value is not None]
    return min(non_null) if non_null else None


def _extract_header_footer_control_kind(payload: bytes) -> str | None:
    prefix = payload[:4]
    if prefix == b"daeh":
        return "header"
    if prefix == b"toof":
        return "footer"
    return None


def _parse_control_field_run(record: ParsedBodyTextRecord) -> dict[str, object] | None:
    prefix = record.payload[:4]
    if prefix != b"onta":
        return None

    resolved_number = None
    if len(record.payload) >= 12:
        candidate = int.from_bytes(record.payload[8:12], "little")
        if candidate > 0:
            resolved_number = str(candidate)

    return {
        "kind": "field",
        "text": "",
        "field_type": "page_number",
        "resolved_text": resolved_number,
        "char_style_ref": None,
        "char_style": {
            "bold": None,
            "font_size_pt": None,
            "style_ref": None,
            "raw": {},
        },
        "raw": {
            "record_index": record.index,
            "tag_id": record.tag_id,
            "payload_hex": record.payload.hex(),
            "control_prefix": prefix.decode("ascii", errors="ignore"),
        },
    }


def _has_suspicious_text_artifacts(text: str) -> bool:
    for char in text:
        if char in {" ", "\n", "\r", "\t"}:
            continue
        if "\uac00" <= char <= "\ud7a3":
            continue
        if char.isascii() and (char.isalnum() or char in ".,:;!?-_()/[]{}'\""):
            continue
        return True
    return False


def _extract_image_metadata_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.split("\n"):
        line = raw_line.strip().lstrip("_")
        line = re.sub(r"^[^A-Za-z0-9가-힣]+", "", line)
        if not line:
            continue
        if any(ch.isalnum() or ("\uac00" <= ch <= "\ud7a3") for ch in line):
            lines.append(line)
    return lines


def _extract_image_dimensions(
    records: list[ParsedBodyTextRecord],
    metadata_lines: list[str],
) -> tuple[int | None, int | None]:
    for line in metadata_lines:
        match = re.search(r"가로\s+(\d+)pixel,\s*세로\s+(\d+)pixel", line)
        if match:
            return int(match.group(1)), int(match.group(2))

    for record in records:
        if record.tag_id not in {71, 76, 85}:
            continue
        values = _u16_list(record.payload)
        for index in range(len(values) - 1):
            width = values[index]
            height = values[index + 1]
            if width > 1000 and height > 1000:
                return width, height
    return None, None


def _infer_list_info(
    paragraph_style_ref: int | None,
    paragraph_style_raw: dict[str, object],
) -> dict[str, object] | None:
    u32_values = paragraph_style_raw.get("u32")
    if not isinstance(u32_values, list) or len(u32_values) <= 7:
        return None

    list_flags = u32_values[7]
    if not isinstance(list_flags, int) or list_flags <= 0:
        return None

    numbering_ref = (list_flags >> 16) & 0xFFFF
    level = list_flags & 0xFFFF
    if numbering_ref <= 0:
        return None

    return {
        "kind": "numbered",
        "level": level,
        "numbering_ref": numbering_ref,
        "marker_text": None,
        "raw": {
            "paragraph_style_ref": paragraph_style_ref,
            "list_flags": list_flags,
            "u32": u32_values[:12],
        },
    }


def _populate_list_markers(paragraph_blocks: list[ParagraphBlockSummary]) -> list[ParagraphBlockSummary]:
    counters: dict[tuple[int, int], int] = {}
    updated: list[ParagraphBlockSummary] = []

    for block in paragraph_blocks:
        if not block.list_info or block.list_info.get("kind") != "numbered":
            updated.append(block)
            continue

        numbering_ref = block.list_info.get("numbering_ref")
        level = block.list_info.get("level")
        if not isinstance(numbering_ref, int) or not isinstance(level, int):
            updated.append(block)
            continue

        key = (numbering_ref, level)
        counters[key] = counters.get(key, 0) + 1
        marker_text = f"{counters[key]}."
        updated.append(
            ParagraphBlockSummary(
                index=block.index,
                block_type=block.block_type,
                paragraph_type=block.paragraph_type,
                text_decoded=block.text_decoded,
                record_indices=block.record_indices,
                paragraph_style_ref=block.paragraph_style_ref,
                char_style_ref=block.char_style_ref,
                list_info={
                    **block.list_info,
                    "marker_text": marker_text,
                },
                paragraph_style=block.paragraph_style,
                text_runs=block.text_runs,
                text_origin=block.text_origin,
                raw=block.raw,
            )
        )

    return updated


def _extract_image_alt_text(metadata_lines: list[str]) -> str | None:
    for line in metadata_lines:
        if line.startswith("원본 그림의 이름:") or line.startswith("원본 그림의 크기:"):
            continue
        return line
    return None


def _extract_image_visible_text_lines(metadata_lines: list[str]) -> list[str]:
    return [
        line
        for line in metadata_lines
        if not line.startswith("원본 그림의 이름:")
        and not line.startswith("원본 그림의 크기:")
    ]


def _extract_original_filename(metadata_lines: list[str]) -> str | None:
    prefix = "원본 그림의 이름:"
    for line in metadata_lines:
        if line.startswith(prefix):
            value = line[len(prefix):].strip()
            return value or None
    return None


def _extract_original_size_text(metadata_lines: list[str]) -> str | None:
    prefix = "원본 그림의 크기:"
    for line in metadata_lines:
        if line.startswith(prefix):
            return line
    return None


def _pick_image_metadata_record(records: list[ParsedBodyTextRecord]) -> ParsedBodyTextRecord:
    def score(record: ParsedBodyTextRecord) -> tuple[int, int, int]:
        decoded = strip_control_codes(record.payload.decode("utf-16le", errors="ignore"))
        metadata_lines = _extract_image_metadata_lines(decoded)
        hangul_chars = sum(1 for char in decoded if "\uac00" <= char <= "\ud7a3")
        return (len(metadata_lines), hangul_chars, len(record.payload))

    return max(records, key=score)
