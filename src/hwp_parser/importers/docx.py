from __future__ import annotations

import logging
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from docx import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.table import Table as DocxTable
from docx.table import _Cell as DocxCell
from docx.text.paragraph import Paragraph as DocxParagraph

from hwp_parser.ir.models import (
    CharacterStyle,
    Document,
    DocumentSection,
    ImageBlock,
    ListInfo,
    Paragraph,
    ParagraphStyle,
    Table,
    TableCell,
    TableRow,
    TextRun,
)
from hwp_parser.ir.serialize import document_to_dict, document_to_json

LOGGER = logging.getLogger(__name__)

EMU_PER_PIXEL = 9525
WORDPROCESSING_NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
}
NUMBERED_FORMATS = {
    "aiueo",
    "arabicAbjad",
    "arabicAlpha",
    "cardinalText",
    "chicago",
    "decimal",
    "decimalEnclosedCircle",
    "decimalEnclosedFullstop",
    "decimalEnclosedParen",
    "decimalFullWidth",
    "decimalFullWidth2",
    "decimalHalfWidth",
    "decimalZero",
    "ganada",
    "hebrew1",
    "hebrew2",
    "hindiConsonants",
    "hindiNumbers",
    "hindiVowels",
    "ideographDigital",
    "ideographEnclosedCircle",
    "ideographLegalTraditional",
    "ideographTraditional",
    "iroha",
    "irohaFullWidth",
    "japaneseCounting",
    "japaneseDigitalTenThousand",
    "japaneseLegal",
    "koreanCounting",
    "koreanDigital",
    "koreanDigital2",
    "koreanLegal",
    "lowerLetter",
    "lowerRoman",
    "ordinal",
    "ordinalText",
    "russianLower",
    "russianUpper",
    "taiwaneseCounting",
    "taiwaneseCountingThousand",
    "taiwaneseDigital",
    "thaiCounting",
    "thaiLetters",
    "thaiNumbers",
    "upperLetter",
    "upperRoman",
    "vietnameseCounting",
}
BULLETED_FORMATS = {"bullet", "picture"}


class NumberingContext:
    def __init__(
        self,
        *,
        style_num_ids: dict[str, int],
        num_abstract_ids: dict[int, int],
        abstract_level_formats: dict[int, dict[int, str]],
        abstract_level_texts: dict[int, dict[int, str]],
    ) -> None:
        self.style_num_ids = style_num_ids
        self.num_abstract_ids = num_abstract_ids
        self.abstract_level_formats = abstract_level_formats
        self.abstract_level_texts = abstract_level_texts

    def build_list_info(self, paragraph: DocxParagraph) -> ListInfo | None:
        num_id, level, source = _extract_paragraph_num_pr(paragraph)
        style_name = paragraph.style.name if paragraph.style is not None else None
        style_id = paragraph.style.style_id if paragraph.style is not None else None

        if num_id is None and style_id and style_id in self.style_num_ids:
            num_id = self.style_num_ids[style_id]
            source = "style"

        num_format = None
        lvl_text = None
        kind = None
        if num_id is not None:
            abstract_num_id = self.num_abstract_ids.get(num_id)
            resolved_level = level if level is not None else 0
            if abstract_num_id is not None:
                num_format = self.abstract_level_formats.get(abstract_num_id, {}).get(resolved_level)
                lvl_text = self.abstract_level_texts.get(abstract_num_id, {}).get(resolved_level)
                kind = _numbering_kind_from_format(num_format)
        else:
            abstract_num_id = None
            resolved_level = None

        if kind is None and style_name:
            lowered = style_name.lower()
            if lowered.startswith("list number"):
                kind = "numbered"
            elif lowered.startswith("list bullet"):
                kind = "bulleted"

        if kind is None and num_id is None:
            return None

        return ListInfo(
            kind=kind,
            level=resolved_level,
            numbering_ref=num_id,
            marker_text=lvl_text if lvl_text and "%" not in lvl_text else None,
            raw={
                "source": source,
                "style_id": style_id,
                "style_name": style_name,
                "num_id": num_id,
                "abstract_num_id": abstract_num_id,
                "num_format": num_format,
                "lvl_text": lvl_text,
            },
        )


def import_docx_to_ir_dict(
    input_path: Path,
    *,
    artifact_root: Path = Path("artifacts/imports"),
) -> dict[str, object]:
    document = import_docx_to_ir_document(input_path, artifact_root=artifact_root)
    return document_to_dict(document)


def import_docx_to_ir_document(
    input_path: Path,
    *,
    artifact_root: Path = Path("artifacts/imports"),
) -> Document:
    docx_document = DocxDocument(input_path)
    import_dir = artifact_root / f"{input_path.stem}_docx"
    media_dir = import_dir / "word" / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    _extract_docx_media(input_path, media_dir)
    numbering_context = _load_numbering_context(input_path)

    blocks = _story_to_blocks(
        docx_document.element.body,
        docx_document,
        media_dir,
        source_path="word/document.xml",
        numbering_context=numbering_context,
    )

    header = None
    footer = None
    if docx_document.sections:
        header = _section_to_ir(
            docx_document.sections[0].header,
            media_dir,
            numbering_context=numbering_context,
        )
        footer = _section_to_ir(
            docx_document.sections[0].footer,
            media_dir,
            numbering_context=numbering_context,
        )

    document = Document(
        source_path=str(input_path),
        blocks=blocks,
        header=header,
        footer=footer,
    )

    import_dir.mkdir(parents=True, exist_ok=True)
    (import_dir / "ir.json").write_text(document_to_json(document), encoding="utf-8")
    return document


def _extract_docx_media(input_path: Path, media_dir: Path) -> None:
    with ZipFile(input_path) as archive:
        for name in archive.namelist():
            if not name.startswith("word/media/"):
                continue
            output_path = media_dir / Path(name).name
            output_path.write_bytes(archive.read(name))


def _story_to_blocks(
    story_element: object,
    parent: object,
    media_dir: Path,
    *,
    source_path: str,
    numbering_context: NumberingContext,
) -> list[object]:
    blocks: list[object] = []
    for child in story_element.iterchildren():
        if child.tag.endswith("}p"):
            paragraph = DocxParagraph(child, parent)
            blocks.extend(
                _paragraph_to_blocks(
                    paragraph,
                    media_dir,
                    source_path=source_path,
                    numbering_context=numbering_context,
                )
            )
        elif child.tag.endswith("}tbl"):
            table = DocxTable(child, parent)
            blocks.append(_table_to_ir(table, source_path=source_path))
    return blocks


def _section_to_ir(section: object, media_dir: Path, *, numbering_context: NumberingContext) -> DocumentSection | None:
    source_path = str(section.part.partname).lstrip("/")
    blocks = _story_to_blocks(
        section._element,
        section,
        media_dir,
        source_path=source_path,
        numbering_context=numbering_context,
    )
    meaningful_blocks = [
        block
        for block in blocks
        if not (isinstance(block, Paragraph) and block.is_empty and not block.text_runs)
    ]
    if not meaningful_blocks:
        return None
    return DocumentSection(blocks=meaningful_blocks)


def _paragraph_to_blocks(
    paragraph: DocxParagraph,
    media_dir: Path,
    *,
    source_path: str,
    numbering_context: NumberingContext,
) -> list[object]:
    text_runs = _paragraph_runs_to_ir(paragraph)
    has_visible_text = any(run.display_text for run in text_runs)
    image_blocks = _extract_image_blocks_from_paragraph(paragraph, media_dir, source_path=source_path)
    list_info = numbering_context.build_list_info(paragraph)

    blocks: list[object] = []
    if has_visible_text or list_info is not None or (not image_blocks and paragraph.text == ""):
        blocks.append(
            Paragraph(
                text_runs=text_runs,
                paragraph_style=ParagraphStyle(alignment=_alignment_to_str(paragraph.alignment)),
                list_info=list_info,
                is_empty=not has_visible_text,
                paragraph_type="text_paragraph" if has_visible_text else "empty_paragraph",
                source_path=source_path,
            )
        )
    blocks.extend(image_blocks)
    return blocks


def _paragraph_runs_to_ir(paragraph: DocxParagraph) -> list[TextRun]:
    runs: list[TextRun] = []
    for run in paragraph.runs:
        if not run.text:
            continue
        font_size = run.font.size.pt if run.font.size is not None else None
        runs.append(
            TextRun(
                text=run.text,
                kind="text",
                character_style=CharacterStyle(
                    bold=bool(run.bold) if run.bold is not None else None,
                    font_size_pt=float(font_size) if font_size is not None else None,
                ),
            )
        )
    return runs


def _extract_image_blocks_from_paragraph(
    paragraph: DocxParagraph,
    media_dir: Path,
    *,
    source_path: str,
) -> list[ImageBlock]:
    image_blocks: list[ImageBlock] = []
    for run in paragraph.runs:
        drawing_elements = run._element.xpath(".//w:drawing")
        if not drawing_elements:
            continue
        for drawing in drawing_elements:
            relationship_ids = drawing.xpath(".//a:blip/@r:embed")
            if not relationship_ids:
                continue
            relationship_id = relationship_ids[0]
            image_part = paragraph.part.related_parts.get(relationship_id)
            if image_part is None:
                LOGGER.warning("DOCX import could not resolve related image part: %s", relationship_id)
                continue
            filename = Path(str(image_part.partname)).name
            binary_output_path = media_dir / filename
            if not binary_output_path.exists():
                binary_output_path.write_bytes(image_part.blob)

            extent = drawing.xpath(".//wp:extent")
            width = None
            height = None
            if extent:
                width = _emu_to_pixels(int(extent[0].get("cx", "0")))
                height = _emu_to_pixels(int(extent[0].get("cy", "0")))

            doc_pr = drawing.xpath(".//wp:docPr")
            alt_text = None
            if doc_pr:
                alt_text = (
                    doc_pr[0].get("descr")
                    or doc_pr[0].get("title")
                    or doc_pr[0].get("name")
                )

            image_blocks.append(
                ImageBlock(
                    source_path=source_path,
                    source_ref=f"rId:{relationship_id}",
                    binary_stream_ref=f"word/media/{filename}",
                    width=width,
                    height=height,
                    alt_text=alt_text,
                    raw={"binary_output_path": str(binary_output_path)},
                )
            )
    return image_blocks


def _table_to_ir(table: DocxTable, *, source_path: str) -> Table:
    row_entries: list[list[dict[str, object]]] = []
    column_count = 0

    for row_index, tr in enumerate(table._tbl.tr_lst):
        entries: list[dict[str, object]] = []
        column_index = 0
        for tc in tr.tc_lst:
            colspan = _grid_span_from_tc(tc)
            v_merge = _v_merge_state_from_tc(tc)
            cell = DocxCell(tc, table)
            entries.append(
                {
                    "row_index": row_index,
                    "column_index": column_index,
                    "colspan": colspan,
                    "v_merge": v_merge,
                    "text": cell.text,
                    "raw": {
                        "grid_span": colspan,
                        "v_merge": v_merge,
                    },
                }
            )
            column_index += colspan
        column_count = max(column_count, column_index)
        row_entries.append(entries)

    rows: list[TableRow] = []
    for row_index, entries in enumerate(row_entries):
        cells: list[TableCell] = []
        for entry in entries:
            if entry["v_merge"] == "continue":
                continue
            cells.append(
                TableCell(
                    text=str(entry["text"]),
                    row_index=row_index,
                    column_index=int(entry["column_index"]),
                    colspan=int(entry["colspan"]),
                    rowspan=_calculate_rowspan(row_entries, row_index, entry),
                    raw=dict(entry["raw"]),
                )
            )
        rows.append(TableRow(cells=cells))

    return Table(
        rows=rows,
        row_count=len(rows),
        column_count=column_count,
        source_path=source_path,
    )


def _calculate_rowspan(
    row_entries: list[list[dict[str, object]]],
    row_index: int,
    entry: dict[str, object],
) -> int:
    if entry["v_merge"] != "restart":
        return 1

    rowspan = 1
    next_row = row_index + 1
    while next_row < len(row_entries):
        continuation = _find_entry(
            row_entries[next_row],
            column_index=int(entry["column_index"]),
            colspan=int(entry["colspan"]),
        )
        if continuation is None or continuation["v_merge"] != "continue":
            break
        rowspan += 1
        next_row += 1
    return rowspan


def _find_entry(
    entries: list[dict[str, object]],
    *,
    column_index: int,
    colspan: int,
) -> dict[str, object] | None:
    for entry in entries:
        if int(entry["column_index"]) == column_index and int(entry["colspan"]) == colspan:
            return entry
    return None


def _grid_span_from_tc(tc: object) -> int:
    grid_span = getattr(getattr(tc, "tcPr", None), "gridSpan", None)
    if grid_span is not None and getattr(grid_span, "val", None):
        return int(grid_span.val)
    return 1


def _v_merge_state_from_tc(tc: object) -> str | None:
    v_merge = getattr(getattr(tc, "tcPr", None), "vMerge", None)
    if v_merge is None:
        return None
    value = getattr(v_merge, "val", None)
    if value in {None, "continue"}:
        return "continue"
    if value == "restart":
        return "restart"
    return str(value)


def _extract_paragraph_num_pr(paragraph: DocxParagraph) -> tuple[int | None, int | None, str | None]:
    p_pr = paragraph._p.pPr
    if p_pr is None or p_pr.numPr is None:
        return None, None, None

    num_pr = p_pr.numPr
    num_id = int(num_pr.numId.val) if num_pr.numId is not None and num_pr.numId.val is not None else None
    level = int(num_pr.ilvl.val) if num_pr.ilvl is not None and num_pr.ilvl.val is not None else None
    return num_id, level, "numPr"


def _load_numbering_context(input_path: Path) -> NumberingContext:
    style_num_ids: dict[str, int] = {}
    num_abstract_ids: dict[int, int] = {}
    abstract_level_formats: dict[int, dict[int, str]] = {}
    abstract_level_texts: dict[int, dict[int, str]] = {}

    with ZipFile(input_path) as archive:
        if "word/styles.xml" in archive.namelist():
            styles_root = ET.fromstring(archive.read("word/styles.xml"))
            for style_element in styles_root.findall("w:style", WORDPROCESSING_NS):
                style_id = style_element.get(f"{{{WORDPROCESSING_NS['w']}}}styleId")
                if not style_id:
                    continue
                num_id_element = style_element.find("w:pPr/w:numPr/w:numId", WORDPROCESSING_NS)
                if num_id_element is None:
                    continue
                value = num_id_element.get(f"{{{WORDPROCESSING_NS['w']}}}val")
                if value is None:
                    continue
                style_num_ids[style_id] = int(value)

        if "word/numbering.xml" in archive.namelist():
            numbering_root = ET.fromstring(archive.read("word/numbering.xml"))
            for num_element in numbering_root.findall("w:num", WORDPROCESSING_NS):
                num_id = num_element.get(f"{{{WORDPROCESSING_NS['w']}}}numId")
                abstract_num_id_element = num_element.find("w:abstractNumId", WORDPROCESSING_NS)
                if num_id is None or abstract_num_id_element is None:
                    continue
                abstract_num_id = abstract_num_id_element.get(f"{{{WORDPROCESSING_NS['w']}}}val")
                if abstract_num_id is None:
                    continue
                num_abstract_ids[int(num_id)] = int(abstract_num_id)

            for abstract_num_element in numbering_root.findall("w:abstractNum", WORDPROCESSING_NS):
                abstract_num_id = abstract_num_element.get(f"{{{WORDPROCESSING_NS['w']}}}abstractNumId")
                if abstract_num_id is None:
                    continue
                abstract_id = int(abstract_num_id)
                formats: dict[int, str] = {}
                texts: dict[int, str] = {}
                for level_element in abstract_num_element.findall("w:lvl", WORDPROCESSING_NS):
                    level_value = level_element.get(f"{{{WORDPROCESSING_NS['w']}}}ilvl")
                    if level_value is None:
                        continue
                    ilvl = int(level_value)
                    format_element = level_element.find("w:numFmt", WORDPROCESSING_NS)
                    text_element = level_element.find("w:lvlText", WORDPROCESSING_NS)
                    format_value = (
                        format_element.get(f"{{{WORDPROCESSING_NS['w']}}}val")
                        if format_element is not None
                        else None
                    )
                    text_value = (
                        text_element.get(f"{{{WORDPROCESSING_NS['w']}}}val")
                        if text_element is not None
                        else None
                    )
                    if format_value is not None:
                        formats[ilvl] = format_value
                    if text_value is not None:
                        texts[ilvl] = text_value
                if formats:
                    abstract_level_formats[abstract_id] = formats
                if texts:
                    abstract_level_texts[abstract_id] = texts

    return NumberingContext(
        style_num_ids=style_num_ids,
        num_abstract_ids=num_abstract_ids,
        abstract_level_formats=abstract_level_formats,
        abstract_level_texts=abstract_level_texts,
    )


def _numbering_kind_from_format(num_format: str | None) -> str | None:
    if num_format in NUMBERED_FORMATS:
        return "numbered"
    if num_format in BULLETED_FORMATS:
        return "bulleted"
    return None


def _alignment_to_str(alignment: WD_ALIGN_PARAGRAPH | None) -> str | None:
    if alignment == WD_ALIGN_PARAGRAPH.CENTER:
        return "center"
    if alignment == WD_ALIGN_PARAGRAPH.RIGHT:
        return "right"
    if alignment == WD_ALIGN_PARAGRAPH.LEFT:
        return "left"
    return None


def _emu_to_pixels(value: int) -> int | None:
    if value <= 0:
        return None
    return round(value / EMU_PER_PIXEL)
