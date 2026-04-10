from __future__ import annotations

import argparse
import json
from pathlib import Path

from .dispatch import import_document_to_ir_dict


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import an HWP or DOCX file into IR JSON.")
    parser.add_argument("input_path", type=Path, help="Source .hwp or .docx file")
    parser.add_argument("output_ir_json", type=Path, help="Output IR JSON path")
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=Path("artifacts/imports"),
        help="Directory for import-time extracted artifacts",
    )
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    payload = import_document_to_ir_dict(args.input_path, artifact_root=args.artifact_root)
    args.output_ir_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_ir_json.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
