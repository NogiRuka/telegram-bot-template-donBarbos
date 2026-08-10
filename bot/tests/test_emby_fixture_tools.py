# ruff: noqa: PT009, PT027

import tempfile
import unittest
from pathlib import Path

from bot.services.emby_metadata.fixture_tools import (
    add_fixture_files,
    create_empty_fixture_files,
    prepare_fixture_directories,
)


class FixtureToolsTests(unittest.TestCase):
    def test_create_empty_fixture_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_root = prepare_fixture_directories(Path(temporary_directory), "source")

            destinations = create_empty_fixture_files(source_root, "detail-name", "search-name")

            self.assertEqual(destinations["detail"].name, "detail-name.html")
            self.assertEqual(destinations["search"].name, "search-name.html")
            self.assertEqual(destinations["detail"].read_text(encoding="utf-8"), "")
            self.assertEqual(destinations["search"].read_text(encoding="utf-8"), "")

    def test_default_fixture_names(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_root = prepare_fixture_directories(Path(temporary_directory), "source")

            destinations = create_empty_fixture_files(source_root, "detail", "search")

            self.assertEqual(destinations["detail"].name, "detail.html")
            self.assertEqual(destinations["search"].name, "search.html")

    def test_prepare_directories_and_copy_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            html_file = root / "search.html"
            html_file.write_text("<html></html>", encoding="utf-8")

            source_root = prepare_fixture_directories(root / "fixtures", "new_source")
            destination = add_fixture_files(source_root, "search", [html_file])[0]

            self.assertEqual(destination, source_root / "search" / "search.html")
            self.assertEqual(destination.read_text(encoding="utf-8"), "<html></html>")
            self.assertTrue((source_root / "detail").is_dir())

    def test_existing_file_is_not_overwritten_without_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            html_file = root / "detail.html"
            html_file.write_text("new", encoding="utf-8")
            source_root = prepare_fixture_directories(root / "fixtures", "source")
            destination = source_root / "detail" / "detail.html"
            destination.write_text("old", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                add_fixture_files(source_root, "detail", [html_file])

            self.assertEqual(destination.read_text(encoding="utf-8"), "old")


if __name__ == "__main__":
    unittest.main()
