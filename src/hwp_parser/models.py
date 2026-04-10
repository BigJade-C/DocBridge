from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StreamInfo:
    path: str
    size: int


@dataclass(frozen=True)
class ExtractedStream:
    source_path: str
    logical_path: str
    output_path: Path
    size: int


@dataclass(frozen=True)
class DumpSummary:
    file: str
    container_type: str
    stream_count: int
    extracted_count: int
    debug_dir: str
    streams: list[StreamInfo]
    extracted: list[ExtractedStream]
