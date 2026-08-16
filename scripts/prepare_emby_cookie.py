"""Create a per-source Emby metadata Cookie configuration file."""

from __future__ import annotations

import argparse
from pathlib import Path

from bot.services.emby_metadata.fixture_tools import create_cookie_file


def build_parser() -> argparse.ArgumentParser:
    """Build the Cookie setup command-line parser."""
    parser = argparse.ArgumentParser(
        description="Create a disabled per-source Emby Cookie configuration."
    )
    parser.add_argument("source", help="source name or CATEGORY/SOURCE")
    parser.add_argument(
        "--config-root",
        type=Path,
        default=Path(__file__).parents[1] / "bot" / "config",
    )
    return parser


def main() -> int:
    """Create one per-source Cookie configuration file."""
    parser = build_parser()
    args = parser.parse_args()
    try:
        destination = create_cookie_file(args.config_root, args.source)
    except ValueError as error:
        parser.error(str(error))
    print(f"Cookie config ready: {destination}")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
