from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .regenerate import DEFAULT_IR_FIXTURE_SPECS, IrFixtureSpec, regenerate_ir_fixtures


def __getattr__(name: str):
    if name in {"DEFAULT_IR_FIXTURE_SPECS", "IrFixtureSpec", "regenerate_ir_fixtures"}:
        from .regenerate import (
            DEFAULT_IR_FIXTURE_SPECS,
            IrFixtureSpec,
            regenerate_ir_fixtures,
        )

        namespace = {
            "DEFAULT_IR_FIXTURE_SPECS": DEFAULT_IR_FIXTURE_SPECS,
            "IrFixtureSpec": IrFixtureSpec,
            "regenerate_ir_fixtures": regenerate_ir_fixtures,
        }
        return namespace[name]
    raise AttributeError(name)

__all__ = [
    "DEFAULT_IR_FIXTURE_SPECS",
    "IrFixtureSpec",
    "regenerate_ir_fixtures",
]
