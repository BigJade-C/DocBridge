from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Sequence

from .container import HwpContainerDumper, summary_to_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hwp-dump",
        description="Inspect and extract selected entries from HWP and HWPX containers.",
    )
    parser.add_argument("file", type=Path, help="Path to the .hwp or .hwpx file")
    parser.add_argument(
        "--debug-dir",
        type=Path,
        default=Path("debug"),
        help="Directory where extracted streams are stored",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity",
    )
    parser.add_argument(
        "--visible-text-only",
        action="store_true",
        help="Print only visible text paragraphs when paragraph debug output exists",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s %(name)s: %(message)s",
    )

    dumper = HwpContainerDumper(args.file)
    summary = dumper.dump(args.debug_dir)

    print(f"Container: {summary.container_type}")
    print("Streams:")
    for stream in summary.streams:
        print(f"- {stream.path} ({stream.size} bytes)")

    print("\nExtracted:")
    if summary.extracted:
        for item in summary.extracted:
            print(
                f"- {item.source_path} -> {item.logical_path} -> "
                f"{item.output_path} ({item.size} bytes)"
            )
    else:
        print("- No target streams found")

    print("\nJSON Summary:")
    print(summary_to_json(summary))

    if args.visible_text_only:
        paragraph_json_path = (
            Path(summary.debug_dir) / "BodyText" / "Section0.paragraphs.json"
        )
        if paragraph_json_path.exists():
            paragraph_summary = json.loads(paragraph_json_path.read_text(encoding="utf-8"))
            print("\nVisible Text Paragraphs:")
            visible_paragraphs = paragraph_summary.get("visible_text_paragraphs", [])
            if visible_paragraphs:
                for paragraph in visible_paragraphs:
                    print(f"- [{paragraph['index']}] {paragraph['text_decoded']}")
            else:
                print("- No visible text paragraphs found")
        else:
            print("\nVisible Text Paragraphs:")
            print("- Paragraph summary not available for this file")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
