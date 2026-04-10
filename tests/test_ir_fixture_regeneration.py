from __future__ import annotations

import json
from pathlib import Path

from hwp_parser.fixtures import IrFixtureSpec, regenerate_ir_fixtures


def test_regenerated_fixture_contains_binary_output_path(tmp_path: Path) -> None:
    public_output = tmp_path / "viewer" / "public" / "fixtures" / "008_mixed.ir.json"
    test_output = tmp_path / "viewer" / "src" / "test" / "fixtures" / "008_mixed.ir.json"

    regenerate_ir_fixtures(
        fixture_specs=(
            IrFixtureSpec(
                sample_path=Path("hwp_samples/008_mixed.hwp"),
                output_paths=(public_output, test_output),
            ),
        ),
        debug_root=tmp_path / "debug",
    )

    payload = json.loads(public_output.read_text(encoding="utf-8"))
    image = next(block for block in payload["blocks"] if block["block_type"] == "image")

    assert image["raw"]["binary_output_path"].endswith("BinData/BIN0001.png")


def test_regenerated_fixtures_are_synchronized_between_public_and_test(tmp_path: Path) -> None:
    public_output = tmp_path / "viewer" / "public" / "fixtures" / "008_mixed.ir.json"
    test_output = tmp_path / "viewer" / "src" / "test" / "fixtures" / "008_mixed.ir.json"

    regenerate_ir_fixtures(
        fixture_specs=(
            IrFixtureSpec(
                sample_path=Path("hwp_samples/008_mixed.hwp"),
                output_paths=(public_output, test_output),
            ),
        ),
        debug_root=tmp_path / "debug",
    )

    assert public_output.read_text(encoding="utf-8") == test_output.read_text(encoding="utf-8")


def test_ir_fixture_regeneration_is_deterministic_for_identical_inputs(tmp_path: Path) -> None:
    public_output = tmp_path / "viewer" / "public" / "fixtures" / "008_mixed.ir.json"
    test_output = tmp_path / "viewer" / "src" / "test" / "fixtures" / "008_mixed.ir.json"
    fixture_spec = IrFixtureSpec(
        sample_path=Path("hwp_samples/008_mixed.hwp"),
        output_paths=(public_output, test_output),
    )

    regenerate_ir_fixtures(
        fixture_specs=(fixture_spec,),
        debug_root=tmp_path / "debug",
    )
    first_payload = public_output.read_text(encoding="utf-8")

    regenerate_ir_fixtures(
        fixture_specs=(fixture_spec,),
        debug_root=tmp_path / "debug",
    )
    second_payload = public_output.read_text(encoding="utf-8")

    assert first_payload == second_payload
