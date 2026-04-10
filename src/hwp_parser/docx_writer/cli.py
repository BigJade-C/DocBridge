from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Sequence

from .write import write_docx_from_ir_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ir-to-docx",
        description="Write a Phase 1 DOCX file from IR JSON.",
    )
    parser.add_argument("input_ir_json", type=Path, help="Path to an ir.json file")
    parser.add_argument("output_docx", type=Path, help="Path to the output .docx file")
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

    write_docx_from_ir_json(args.input_ir_json, args.output_docx)
    print(f"Wrote DOCX: {args.output_docx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
