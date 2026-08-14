from __future__ import annotations

import hashlib
import importlib.util
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / ".github" / "build_zaparoo_db.py"
SPEC = importlib.util.spec_from_file_location("build_zaparoo_db", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
build_zaparoo_db = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = build_zaparoo_db
SPEC.loader.exec_module(build_zaparoo_db)


class BuildDatabaseTests(unittest.TestCase):
    def test_main_binary_is_independent_from_frontend_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            core_zip = tmp_path / "core.zip"
            frontend_zip = tmp_path / "frontend.zip"
            main_binary = tmp_path / "MiSTer_Zaparoo"

            self.write_zip(core_zip, {"zaparoo.sh": b"core"})
            self.write_zip(
                frontend_zip,
                {
                    "zaparoo/frontend": b"frontend",
                    "zaparoo/menu_zaparoo.rbf": b"menu",
                    "zaparoo/MiSTer_Zaparoo": b"stale-main",
                },
            )
            main_binary.write_bytes(b"current-main")

            core_asset = build_zaparoo_db.ReleaseAsset(
                "v2.0.0", core_zip.name, "https://example/core.zip"
            )
            frontend_asset = build_zaparoo_db.ReleaseAsset(
                "v1.0.0", frontend_zip.name, "https://example/frontend.zip"
            )
            main_asset = build_zaparoo_db.ReleaseAsset(
                "MiSTer_Zaparoo_20260707",
                main_binary.name,
                "https://example/MiSTer_Zaparoo",
            )

            database = build_zaparoo_db.build_db(
                core_asset,
                core_zip,
                frontend_asset,
                frontend_zip,
                main_asset,
                main_binary,
            )

        main_file = database["files"][build_zaparoo_db.MAIN_INSTALL_PATH]
        self.assertEqual(main_file["hash"], hashlib.md5(b"current-main").hexdigest())
        self.assertEqual(main_file["size"], len(b"current-main"))
        self.assertEqual(main_file["url"], main_asset.url)
        self.assertTrue(main_file["reboot"])
        self.assertEqual(main_file["backup"], "zaparoo/MiSTer_Zaparoo.bak")
        self.assertEqual(main_file["tmp"], "zaparoo/MiSTer_Zaparoo.tmp")

        frontend_files = database["archives"]["zaparoo_frontend"]["summary_inline"][
            "files"
        ]
        self.assertEqual(
            set(frontend_files),
            {"zaparoo/frontend", "zaparoo/menu_zaparoo.rbf"},
        )
        self.assertNotIn(build_zaparoo_db.MAIN_INSTALL_PATH, frontend_files)

    def test_main_asset_pattern_excludes_debug_binary(self) -> None:
        self.assertIsNotNone(build_zaparoo_db.MAIN_ASSET_RE.fullmatch("MiSTer_Zaparoo"))
        self.assertIsNone(
            build_zaparoo_db.MAIN_ASSET_RE.fullmatch("MiSTer_Zaparoo.elf")
        )

    @staticmethod
    def write_zip(path: Path, files: dict[str, bytes]) -> None:
        with zipfile.ZipFile(path, "w") as archive:
            for name, contents in files.items():
                archive.writestr(name, contents)


if __name__ == "__main__":
    unittest.main()
