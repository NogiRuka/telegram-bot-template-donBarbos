"""Create Cookie configuration files for existing fixture sources."""

from __future__ import annotations

import argparse
from pathlib import Path

from bot.services.emby_metadata.fixture_tools import create_cookie_file


def build_parser() -> argparse.ArgumentParser:
    """Build the batch Cookie setup command-line parser."""
    parser = argparse.ArgumentParser(
        description="Create disabled per-source Cookie files for fixture sources."
    )
    parser.add_argument(
        "--fixtures-root",
        type=Path,
        default=Path(__file__).parents[1]
        / "bot"
        / "services"
        / "emby_metadata"
        / "fixtures",
    )
    parser.add_argument(
        "--config-root",
        type=Path,
        default=Path(__file__).parents[1] / "bot" / "config",
    )
    return parser


def main() -> int:
    """Create one Cookie file for every categorized fixture source."""
    parser = build_parser()
    args = parser.parse_args()
    categories = {"日韩", "国产", "欧美"}
    sources = [
        f"{category}/{source_dir.name}"
        for category in sorted(categories)
        for source_dir in sorted((args.fixtures_root / category).iterdir())
        if source_dir.is_dir()
    ]
    for source in sources:
        print(create_cookie_file(args.config_root, source))  # noqa: T201
    print(f"Prepared {len(sources)} Cookie config files")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
