from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from hwp_parser.ir.models import ImageBlock

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImageResolutionContext:
    search_roots: tuple[Path, ...] = field(default_factory=tuple)


def resolve_image_path(
    image_block: ImageBlock,
    context: ImageResolutionContext | None = None,
) -> Path | None:
    raw_path = image_block.raw.get("binary_output_path")
    if isinstance(raw_path, str) and raw_path:
        candidate = Path(raw_path)
        if candidate.exists():
            return candidate
        LOGGER.warning(
            "Image binary_output_path does not exist: binary_stream_ref=%s path=%s",
            image_block.binary_stream_ref,
            candidate,
        )

    binary_stream_ref = image_block.binary_stream_ref
    if not binary_stream_ref:
        LOGGER.warning("Image export fallback skipped because binary_stream_ref is missing")
        return None

    suffix_parts = tuple(part for part in Path(binary_stream_ref).parts if part not in (".", ""))
    roots = _collect_search_roots(context)
    matches = _find_matches(roots, suffix_parts)

    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        LOGGER.warning(
            "Image export fallback ambiguous for %s: %s",
            binary_stream_ref,
            ", ".join(str(match) for match in matches),
        )
        return None

    LOGGER.warning("Image export fallback failed for %s", binary_stream_ref)
    return None


def _collect_search_roots(context: ImageResolutionContext | None) -> tuple[Path, ...]:
    explicit_roots = tuple(
        root.resolve()
        for root in (context.search_roots if context is not None else ())
    )
    if explicit_roots:
        return _dedupe_roots(explicit_roots)

    cwd = Path.cwd().resolve()
    default_roots = (
        cwd,
        cwd / "artifacts",
        cwd / "artifacts" / "editor_model_fixtures",
        cwd / "artifacts" / "editor_model_fixtures" / "debug",
        cwd / "artifacts" / "docx" / "phase2" / "debug",
        cwd / "artifacts" / "docx" / "phase1" / "phase1_docx_out" / "debug",
        cwd / "viewer" / "public" / "fixtures",
    )
    return _dedupe_roots(default_roots)


def _dedupe_roots(roots: Iterable[Path]) -> tuple[Path, ...]:
    ordered: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if root in seen:
            continue
        ordered.append(root)
        seen.add(root)
    return tuple(ordered)


def _find_matches(search_roots: Sequence[Path], suffix_parts: tuple[str, ...]) -> list[Path]:
    matches: list[Path] = []
    seen: set[Path] = set()
    leaf_name = suffix_parts[-1]

    for root in search_roots:
        if not root.exists():
            continue
        direct = root.joinpath(*suffix_parts)
        if direct.exists():
            resolved = direct.resolve()
            if resolved not in seen:
                matches.append(resolved)
                seen.add(resolved)
            continue

        for candidate in root.rglob(leaf_name):
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            if _path_has_suffix_parts(resolved, suffix_parts):
                matches.append(resolved)
                seen.add(resolved)

    return matches


def _path_has_suffix_parts(path: Path, suffix_parts: tuple[str, ...]) -> bool:
    path_parts = path.parts
    if len(path_parts) < len(suffix_parts):
        return False
    return tuple(path_parts[-len(suffix_parts) :]) == suffix_parts
