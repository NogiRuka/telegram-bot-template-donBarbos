"""Utilities for preparing local Emby metadata HTML fixtures."""

from __future__ import annotations
import re
import shutil
from pathlib import Path

_SOURCE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_HTML_SUFFIXES = {".htm", ".html"}


def prepare_fixture_directories(fixtures_root: Path, source: str) -> Path:
    """Create and return the standard directory tree for one metadata source."""
    if not _SOURCE_NAME_PATTERN.fullmatch(source):
        msg = "source must contain only letters, numbers, underscores, and hyphens"
        raise ValueError(
            msg
        )

    source_root = fixtures_root / source
    (source_root / "search").mkdir(parents=True, exist_ok=True)
    (source_root / "detail").mkdir(parents=True, exist_ok=True)
    return source_root


def add_fixture_files(
    source_root: Path,
    fixture_type: str,
    files: list[Path],
    *,
    overwrite: bool = False,
) -> list[Path]:
    """Copy HTML files into a source's ``search`` or ``detail`` directory."""
    if fixture_type not in {"search", "detail"}:
        msg = "fixture_type must be 'search' or 'detail'"
        raise ValueError(msg)

    destination_root = source_root / fixture_type
    destination_root.mkdir(parents=True, exist_ok=True)
    destinations: list[Path] = []
    for source_file in files:
        if not source_file.is_file():
            raise FileNotFoundError(source_file)
        if source_file.suffix.lower() not in _HTML_SUFFIXES:
            msg = f"fixture must be an HTML file: {source_file}"
            raise ValueError(msg)

        destination = destination_root / source_file.name
        if destination.exists() and not overwrite:
            msg = f"fixture already exists: {destination}; use --overwrite to replace it"
            raise FileExistsError(
                msg
            )
        shutil.copy2(source_file, destination)
        destinations.append(destination)
    return destinations


def create_empty_fixture_files(
    source_root: Path,
    detail_name: str,
    search_name: str,
    *,
    overwrite: bool = False,
) -> dict[str, Path]:
    """Create empty detail and search HTML fixtures from short names.

    The ``.html`` suffix is added when omitted. Existing files are preserved
    unless ``overwrite`` is enabled.
    """
    destinations = {
        "detail": source_root / "detail" / _html_filename(detail_name),
        "search": source_root / "search" / _html_filename(search_name),
    }
    for destination in destinations.values():
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and not overwrite:
            msg = f"fixture already exists: {destination}; use --overwrite to replace it"
            raise FileExistsError(msg)
        destination.write_text("", encoding="utf-8")
    return destinations


def _html_filename(name: str) -> str:
    """Validate a fixture name and return it with an HTML suffix."""
    filename = f"{name}.html" if Path(name).suffix == "" else name
    if (
        Path(filename).name != filename
        or Path(filename).suffix.lower() not in _HTML_SUFFIXES
        or not Path(filename).stem
    ):
        msg = f"fixture name must be a simple .html filename: {name}"
        raise ValueError(msg)
    return filename
