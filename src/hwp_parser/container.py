from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from zipfile import ZipFile

import olefile

from .block_analysis import BodyTextBlockAnalyzer, block_document_to_json
from .bodytext import (
    BodyTextDecoder,
    BodyTextRecordParser,
    ParagraphExtractor,
    record_summary_to_json,
    write_bodytext_debug_outputs,
)
from .file_header import parse_file_header
from .models import DumpSummary, ExtractedStream, StreamInfo
from .bodytext import ParsedBodyTextRecord
from .style_analysis import (
    DocInfoStyleResolver,
    ParagraphStyleAnalyzer,
    style_analysis_to_json,
    style_tables_to_json,
)
from .ir.convert import document_from_blocks
from .ir.serialize import document_to_json

LOGGER = logging.getLogger(__name__)

OLE_TARGET_STREAMS = {
    "FileHeader",
    "DocInfo",
    "BodyText/Section0",
}
OLE_TARGET_PREFIXES = ("BinData/",)

HWPX_TARGET_STREAMS = {
    "Contents/header.xml",
    "Contents/section0.xml",
}
HWPX_TARGET_PREFIXES = ("BinData/",)
HWPX_LOGICAL_PATHS = {
    "Contents/header.xml": "FileHeader",
    "Contents/section0.xml": "BodyText/Section0",
}


class HwpContainerDumper:
    """Minimal dumper for HWP OLE files and HWPX ZIP containers."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self._bodytext_decoder = BodyTextDecoder()
        self._bodytext_record_parser = BodyTextRecordParser()
        self._paragraph_extractor = ParagraphExtractor()
        self._paragraph_style_analyzer = ParagraphStyleAnalyzer()
        self._docinfo_style_resolver = DocInfoStyleResolver()
        self._bodytext_block_analyzer = BodyTextBlockAnalyzer()

    def dump(self, debug_root: Path) -> DumpSummary:
        LOGGER.debug("Opening document container: %s", self.file_path)

        if olefile.isOleFile(str(self.file_path)):
            summary = self._dump_ole(debug_root)
            self._write_debug_reports(summary)
            return summary
        if self.file_path.suffix.lower() == ".hwpx":
            summary = self._dump_hwpx(debug_root)
            self._write_debug_reports(summary)
            return summary
        raise ValueError(f"Unsupported document container: {self.file_path}")

    def _dump_ole(self, debug_root: Path) -> DumpSummary:
        debug_dir = self._build_debug_dir(debug_root)
        debug_dir.mkdir(parents=True, exist_ok=True)
        LOGGER.debug("Detected OLE container, debug directory: %s", debug_dir)

        with olefile.OleFileIO(str(self.file_path)) as ole:
            streams = self._list_ole_streams(ole)
            extracted = self._extract_ole_streams(ole, streams, debug_dir)

        return DumpSummary(
            file=str(self.file_path),
            container_type="ole",
            stream_count=len(streams),
            extracted_count=len(extracted),
            debug_dir=str(debug_dir),
            streams=streams,
            extracted=extracted,
        )

    def _dump_hwpx(self, debug_root: Path) -> DumpSummary:
        debug_dir = self._build_debug_dir(debug_root)
        debug_dir.mkdir(parents=True, exist_ok=True)
        LOGGER.debug("Detected HWPX zip container, debug directory: %s", debug_dir)

        with ZipFile(self.file_path) as archive:
            streams = self._list_hwpx_entries(archive)
            extracted = self._extract_hwpx_entries(archive, streams, debug_dir)

        return DumpSummary(
            file=str(self.file_path),
            container_type="hwpx",
            stream_count=len(streams),
            extracted_count=len(extracted),
            debug_dir=str(debug_dir),
            streams=streams,
            extracted=extracted,
        )

    def _list_ole_streams(self, ole: olefile.OleFileIO) -> list[StreamInfo]:
        stream_infos: list[StreamInfo] = []
        for entry in ole.listdir(streams=True, storages=False):
            path = "/".join(entry)
            size = ole.get_size(entry)
            LOGGER.debug("Discovered OLE stream: %s (%d bytes)", path, size)
            stream_infos.append(StreamInfo(path=path, size=size))
        return sorted(stream_infos, key=lambda item: item.path.lower())

    def _extract_ole_streams(
        self,
        ole: olefile.OleFileIO,
        streams: list[StreamInfo],
        debug_dir: Path,
    ) -> list[ExtractedStream]:
        extracted: list[ExtractedStream] = []
        for stream in streams:
            if not self._should_extract_ole(stream.path):
                continue

            stream_parts = stream.path.split("/")
            output_path = debug_dir.joinpath(*stream_parts)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            LOGGER.debug("Extracting OLE stream %s to %s", stream.path, output_path)
            with ole.openstream(stream_parts) as handle:
                payload = handle.read()
            output_path.write_bytes(payload)

            extracted.append(
                ExtractedStream(
                    source_path=stream.path,
                    logical_path=stream.path,
                    output_path=output_path,
                    size=len(payload),
                )
            )

        return extracted

    def _list_hwpx_entries(self, archive: ZipFile) -> list[StreamInfo]:
        stream_infos: list[StreamInfo] = []
        for info in archive.infolist():
            if info.is_dir():
                continue
            LOGGER.debug("Discovered HWPX entry: %s (%d bytes)", info.filename, info.file_size)
            stream_infos.append(StreamInfo(path=info.filename, size=info.file_size))
        return sorted(stream_infos, key=lambda item: item.path.lower())

    def _extract_hwpx_entries(
        self,
        archive: ZipFile,
        streams: list[StreamInfo],
        debug_dir: Path,
    ) -> list[ExtractedStream]:
        extracted: list[ExtractedStream] = []
        for stream in streams:
            if not self._should_extract_hwpx(stream.path):
                continue

            logical_path = self._logical_hwpx_path(stream.path)
            output_path = debug_dir.joinpath(*logical_path.split("/"))
            output_path.parent.mkdir(parents=True, exist_ok=True)

            LOGGER.debug(
                "Extracting HWPX entry %s to %s using logical path %s",
                stream.path,
                output_path,
                logical_path,
            )
            payload = archive.read(stream.path)
            output_path.write_bytes(payload)

            extracted.append(
                ExtractedStream(
                    source_path=stream.path,
                    logical_path=logical_path,
                    output_path=output_path,
                    size=len(payload),
                )
            )

        return extracted

    @staticmethod
    def _should_extract_ole(stream_path: str) -> bool:
        if stream_path in OLE_TARGET_STREAMS:
            return True
        return any(stream_path.startswith(prefix) for prefix in OLE_TARGET_PREFIXES)

    @staticmethod
    def _should_extract_hwpx(stream_path: str) -> bool:
        if stream_path in HWPX_TARGET_STREAMS:
            return True
        return any(stream_path.startswith(prefix) for prefix in HWPX_TARGET_PREFIXES)

    @staticmethod
    def _logical_hwpx_path(stream_path: str) -> str:
        if stream_path in HWPX_LOGICAL_PATHS:
            return HWPX_LOGICAL_PATHS[stream_path]
        return stream_path

    def _build_debug_dir(self, debug_root: Path) -> Path:
        suffix = self.file_path.suffix.lower().lstrip(".")
        return debug_root / f"{self.file_path.stem}_{suffix}"

    def _write_debug_reports(self, summary: DumpSummary) -> None:
        debug_dir = Path(summary.debug_dir)
        summary_json_path = debug_dir / "summary.json"
        structure_xml_path = debug_dir / "structure.xml"

        summary_json_path.write_text(summary_to_json(summary), encoding="utf-8")
        structure_xml_path.write_text(summary_to_xml(summary), encoding="utf-8")

        for item in summary.extracted:
            self._write_extracted_metadata(item)

        self._write_bodytext_reports(summary)

    def _write_extracted_metadata(self, item: ExtractedStream) -> None:
        payload = item.output_path.read_bytes()
        metadata = {
            "source_path": item.source_path,
            "logical_path": item.logical_path,
            "output_path": str(item.output_path),
            "size": item.size,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "preview_hex": payload[:64].hex(),
        }
        metadata_path = item.output_path.with_name(f"{item.output_path.name}.json")
        metadata_path.write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )

    def _write_bodytext_reports(self, summary: DumpSummary) -> None:
        if summary.container_type != "ole":
            return

        extracted_by_logical_path = {
            item.logical_path: item for item in summary.extracted
        }
        file_header_item = extracted_by_logical_path.get("FileHeader")
        bodytext_item = extracted_by_logical_path.get("BodyText/Section0")
        if file_header_item is None or bodytext_item is None:
            return

        file_header_info = parse_file_header(file_header_item.output_path.read_bytes())
        decoded_payload = self._bodytext_decoder.decode(
            bodytext_item.output_path.read_bytes(),
            compressed=file_header_info.is_compressed,
        )
        split_records = self._bodytext_record_parser.split_records(decoded_payload)
        record_summary = self._bodytext_record_parser.parse(
            decoded_payload,
            source_path=bodytext_item.logical_path,
        )
        paragraph_summary = self._paragraph_extractor.extract(
            source_path=bodytext_item.logical_path,
            records=split_records,
        )

        write_bodytext_debug_outputs(
            decoded_payload=decoded_payload,
            record_summary=record_summary,
            paragraph_summary=paragraph_summary,
            decoded_output_path=bodytext_item.output_path.with_name("Section0.decoded.bin"),
            summary_output_path=bodytext_item.output_path.with_name("Section0.records.json"),
            paragraph_output_path=bodytext_item.output_path.with_name("Section0.paragraphs.json"),
        )

        docinfo_item = extracted_by_logical_path.get("DocInfo")
        docinfo_records: list[ParsedBodyTextRecord] = []
        if docinfo_item is not None:
            decoded_docinfo = self._bodytext_decoder.decode(
                docinfo_item.output_path.read_bytes(),
                compressed=file_header_info.is_compressed,
            )
            docinfo_records = self._bodytext_record_parser.split_records(decoded_docinfo)
            docinfo_record_summary = self._bodytext_record_parser.parse(
                decoded_docinfo,
                source_path=docinfo_item.logical_path,
            )
            docinfo_item.output_path.with_name("DocInfo.decoded.bin").write_bytes(decoded_docinfo)
            docinfo_item.output_path.with_name("DocInfo.records.json").write_text(
                record_summary_to_json(docinfo_record_summary),
                encoding="utf-8",
            )
            style_tables = self._docinfo_style_resolver.build_tables(docinfo_records)
            docinfo_item.output_path.with_name("DocInfo.style_tables.json").write_text(
                style_tables_to_json(style_tables),
                encoding="utf-8",
            )
            style_summary = self._paragraph_style_analyzer.analyze(
                paragraph_summary=paragraph_summary,
                bodytext_records=split_records,
                docinfo_records=docinfo_records,
            )
            bodytext_item.output_path.with_name("Section0.styles.json").write_text(
                style_analysis_to_json(style_summary),
                encoding="utf-8",
            )

        block_summary = self._bodytext_block_analyzer.analyze(
            source_path=bodytext_item.logical_path,
            bodytext_records=split_records,
            docinfo_records=docinfo_records,
            bin_data_refs=[
                item.logical_path
                for item in summary.extracted
                if item.logical_path.startswith("BinData/")
            ],
            bin_data_output_paths={
                item.logical_path: str(item.output_path)
                for item in summary.extracted
                if item.logical_path.startswith("BinData/")
            },
        )
        block_summary_json = block_document_to_json(block_summary)
        bodytext_item.output_path.with_name("Section0.blocks.json").write_text(
            block_summary_json,
            encoding="utf-8",
        )
        Path(summary.debug_dir, "ir.json").write_text(
            document_to_json(document_from_blocks(json.loads(block_summary_json))),
            encoding="utf-8",
        )


def summary_to_json(summary: DumpSummary) -> str:
    return json.dumps(
        {
            "file": summary.file,
            "container_type": summary.container_type,
            "stream_count": summary.stream_count,
            "extracted_count": summary.extracted_count,
            "debug_dir": summary.debug_dir,
            "streams": [
                {"path": stream.path, "size": stream.size}
                for stream in summary.streams
            ],
            "extracted": [
                {
                    "source_path": item.source_path,
                    "logical_path": item.logical_path,
                    "output_path": str(item.output_path),
                    "size": item.size,
                }
                for item in summary.extracted
            ],
        },
        indent=2,
    )


def summary_to_xml(summary: DumpSummary) -> str:
    root = Element("hwp_dump")
    root.set("file", summary.file)
    root.set("container_type", summary.container_type)
    root.set("stream_count", str(summary.stream_count))
    root.set("extracted_count", str(summary.extracted_count))
    root.set("debug_dir", summary.debug_dir)

    streams_el = SubElement(root, "streams")
    for stream in summary.streams:
        stream_el = SubElement(streams_el, "stream")
        stream_el.set("path", stream.path)
        stream_el.set("size", str(stream.size))

    extracted_el = SubElement(root, "extracted")
    for item in summary.extracted:
        item_el = SubElement(extracted_el, "item")
        item_el.set("source_path", item.source_path)
        item_el.set("logical_path", item.logical_path)
        item_el.set("output_path", str(item.output_path))
        item_el.set("size", str(item.size))

    return tostring(root, encoding="unicode")
