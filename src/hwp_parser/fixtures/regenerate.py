from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from hwp_parser.container import HwpContainerDumper
from hwp_parser.ir.convert import document_from_debug_dir
from hwp_parser.ir.serialize import document_to_json

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class IrFixtureSpec:
    sample_path: Path
    output_paths: tuple[Path, ...]


DEFAULT_IR_FIXTURE_SPECS: tuple[IrFixtureSpec, ...] = (
    IrFixtureSpec(
        sample_path=Path("hwp_samples/008_mixed.hwp"),
        output_paths=(
            Path("viewer/public/fixtures/008_mixed.ir.json"),
            Path("viewer/src/test/fixtures/008_mixed.ir.json"),
        ),
    ),
)


def regenerate_ir_fixtures(
    fixture_specs: Sequence[IrFixtureSpec] = DEFAULT_IR_FIXTURE_SPECS,
    *,
    debug_root: Path = Path("artifacts/editor_model_fixtures/debug"),
) -> list[Path]:
    written_paths: list[Path] = []
    for spec in fixture_specs:
        if not spec.sample_path.exists():
            raise FileNotFoundError(f"Fixture source sample not found: {spec.sample_path}")

        LOGGER.info("Regenerating IR fixture from %s", spec.sample_path)
        summary = HwpContainerDumper(spec.sample_path).dump(debug_root)
        debug_dir = Path(summary.debug_dir)
        canonical_ir_path = debug_dir / "ir.json"

        if canonical_ir_path.exists():
            payload = canonical_ir_path.read_text(encoding="utf-8")
        else:
            document = document_from_debug_dir(debug_dir)
            payload = document_to_json(document)
            canonical_ir_path.write_text(payload, encoding="utf-8")

        for output_path in spec.output_paths:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(payload, encoding="utf-8")
            written_paths.append(output_path)
            LOGGER.info("Wrote IR fixture %s", output_path)

    return written_paths


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Regenerate stable IR fixtures from the latest parser output.",
    )
    parser.add_argument(
        "--debug-root",
        type=Path,
        default=Path("artifacts/editor_model_fixtures/debug"),
        help="Directory where canonical debug/ir.json artifacts are generated.",
    )
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_argument_parser().parse_args()
    written_paths = regenerate_ir_fixtures(debug_root=args.debug_root)
    print(f"Regenerated {len(written_paths)} IR fixture files.")
    for path in written_paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
