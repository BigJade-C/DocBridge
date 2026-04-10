from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class ParagraphStyle:
    alignment: str | None = None
    style_ref: int | None = None


@dataclass(frozen=True)
class ListInfo:
    kind: str | None = None
    level: int | None = None
    numbering_ref: int | None = None
    marker_text: str | None = None
    raw: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class CharacterStyle:
    bold: bool | None = None
    font_size_pt: float | None = None
    style_ref: int | None = None


@dataclass(frozen=True)
class TextRun:
    text: str = ""
    kind: str = "text"
    character_style: CharacterStyle = field(default_factory=CharacterStyle)
    field_type: str | None = None
    resolved_text: str | None = None
    raw: dict[str, object] = field(default_factory=dict)

    @property
    def display_text(self) -> str:
        if self.kind == "field":
            return self.resolved_text or ""
        return self.text


@dataclass(frozen=True)
class Block:
    block_type: str


@dataclass(frozen=True)
class TableCell:
    text: str = ""
    row_index: int = 0
    column_index: int = 0
    colspan: int = 1
    rowspan: int = 1
    source_record_index: int | None = None
    raw: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class TableRow:
    cells: list[TableCell] = field(default_factory=list)
    source_index: int | None = None


@dataclass(frozen=True)
class Table(Block):
    block_type: Literal["table"] = "table"
    rows: list[TableRow] = field(default_factory=list)
    row_count: int = 0
    column_count: int = 0
    source_path: str | None = None
    source_index: int | None = None


@dataclass(frozen=True)
class ImageBlock(Block):
    block_type: Literal["image"] = "image"
    source_path: str | None = None
    source_index: int | None = None
    source_ref: str | None = None
    source_record_index: int | None = None
    binary_stream_ref: str | None = None
    width: int | None = None
    height: int | None = None
    placement: str | None = None
    alt_text: str | None = None
    original_filename: str | None = None
    original_size_text: str | None = None
    raw: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Paragraph(Block):
    block_type: Literal["paragraph"] = "paragraph"
    text_runs: list[TextRun] = field(default_factory=list)
    paragraph_style: ParagraphStyle = field(default_factory=ParagraphStyle)
    list_info: ListInfo | None = None
    is_empty: bool = False
    paragraph_type: str = "unknown_paragraph"
    source_path: str | None = None
    source_index: int | None = None

    @property
    def text(self) -> str:
        return "".join(run.display_text for run in self.text_runs)


@dataclass(frozen=True)
class Document:
    source_path: str | None = None
    blocks: list[Block] = field(default_factory=list)
    header: "DocumentSection | None" = None
    footer: "DocumentSection | None" = None

    @property
    def paragraph_count(self) -> int:
        return sum(1 for block in self.blocks if isinstance(block, Paragraph))


@dataclass(frozen=True)
class DocumentSection:
    blocks: list[Block] = field(default_factory=list)
