"""Create empty Emby metadata fixture files."""

from __future__ import annotations
import argparse
from pathlib import Path

from bot.services.emby_metadata.fixture_tools import (
    create_empty_fixture_files,
    prepare_fixture_directories,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Create fixtures and a per-source Cookie config scaffold."
    )
    parser.add_argument("source", help="source name or CATEGORY/SOURCE, e.g. 日韩/temp")
    parser.add_argument(
        "detail_name",
        nargs="?",
        default="detail",
        help="detail fixture name, with or without .html (default: detail.html)",
    )
    parser.add_argument(
        "search_name",
        nargs="?",
        default="search",
        help="search fixture name, with or without .html (default: search.html)",
    )
    parser.add_argument(
        "--fixtures-root",
        type=Path,
        default=Path(__file__).parents[1]
        / "bot"
        / "services"
        / "emby_metadata"
        / "fixtures",
        help="fixture root (defaults to the project's fixture directory)",
    )
    parser.add_argument("--overwrite", action="store_true", help="empty existing files")
    return parser


def main() -> int:
    """Create the source directories and two empty HTML files."""
    parser = build_parser()
    args = parser.parse_args()
    try:
        source_root = prepare_fixture_directories(args.fixtures_root, args.source)
        destinations = create_empty_fixture_files(
            source_root,
            args.detail_name,
            args.search_name,
            overwrite=args.overwrite,
        )
    except (FileExistsError, ValueError) as error:
        parser.error(str(error))

    print(f"Created {destinations['detail']}")  # noqa: T201
    print(f"Created {destinations['search']}")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
