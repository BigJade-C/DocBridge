from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Sequence

from .export import write_docx_from_editor_model_json_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="editor-model-to-docx",
        description="Write a DOCX file from Editor Model JSON.",
    )
    parser.add_argument("input_editor_model_json", type=Path, help="Path to Editor Model JSON")
    parser.add_argument("output_docx", type=Path, help="Path to the output .docx file")
    parser.add_argument(
        "--original-ir-json",
        type=Path,
        default=None,
        help="Optional IR JSON used to preserve unchanged non-paragraph blocks",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s %(name)s: %(message)s",
    )

    write_docx_from_editor_model_json_files(
        args.input_editor_model_json,
        args.output_docx,
        original_ir_path=args.original_ir_json,
    )
    print(f"Wrote DOCX: {args.output_docx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
