"""Utilities for preparing local Emby metadata HTML fixtures."""

from __future__ import annotations
import json
import re
import shutil
import tomllib
from pathlib import Path

_SOURCE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_HTML_SUFFIXES = {".htm", ".html"}
_CATEGORY_NAMES = {"日韩", "国产", "欧美"}


def split_source_spec(source: str) -> tuple[str | None, str]:
    """Split ``category/source`` input into category and source name."""
    normalized = source.replace("\\", "/").strip("/")
    parts = normalized.split("/")
    if len(parts) == 1:
        source_name = parts[0]
        category = None
    elif len(parts) == 2:
        category, source_name = parts
        if category not in _CATEGORY_NAMES:
            raise ValueError(f"unsupported category: {category}")
    else:
        raise ValueError("source must be SOURCE or CATEGORY/SOURCE")

    if not _SOURCE_NAME_PATTERN.fullmatch(source_name):
        raise ValueError(
            "source name must contain only letters, numbers, underscores, and hyphens"
        )
    return category, source_name


def create_cookie_file(config_root: Path, source: str) -> Path:
    """Create a disabled per-source Cookie file without overwriting it."""
    _, source_name = split_source_spec(source)
    cookie_dir = config_root / "cookies"
    cookie_dir.mkdir(parents=True, exist_ok=True)
    destination = cookie_dir / f"{source_name}.toml"
    default_content = "enabled = false\ncookie = \"\"\n"
    if destination.exists() and destination.read_text(encoding="utf-8") != default_content:
        return destination

    content = default_content
    legacy_file = config_root / "cookies.toml"
    if legacy_file.is_file():
        with legacy_file.open("rb") as file:
            legacy_config = tomllib.load(file)
        legacy_data = legacy_config.get(source_name)
        if isinstance(legacy_data, dict):
            enabled = bool(legacy_data.get("enabled", False))
            cookie = legacy_data.get("cookie", "")
            if not isinstance(cookie, str):
                cookie = ""
            content = (
                f"enabled = {'true' if enabled else 'false'}\n"
                f"cookie = {json.dumps(cookie, ensure_ascii=False)}\n"
            )
    destination.write_text(content, encoding="utf-8")
    return destination


def prepare_fixture_directories(fixtures_root: Path, source: str) -> Path:
    """Create and return the standard directory tree for one metadata source."""
    category, source_name = split_source_spec(source)
    source_root = fixtures_root / category / source_name if category else fixtures_root / source_name
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
