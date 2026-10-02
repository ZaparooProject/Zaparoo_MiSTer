from __future__ import annotations

import hashlib
import importlib.util
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


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
        self.assertEqual(set(main_file), {"hash", "size", "url", "reboot"})

        frontend_files = database["archives"]["zaparoo_frontend"]["summary_inline"][
            "files"
        ]
        self.assertEqual(
            set(frontend_files),
            {"zaparoo/frontend", "zaparoo/menu_zaparoo.rbf"},
        )
        self.assertNotIn(build_zaparoo_db.MAIN_INSTALL_PATH, frontend_files)

    def test_scanout_modules_are_installed_from_frontend_archive(self) -> None:
        profile = "zaparoo/modules/6.18.38-MiSTer/ff9b30a1/"
        with tempfile.TemporaryDirectory() as tmp:
            frontend_zip = Path(tmp) / "frontend.zip"
            self.write_zip(
                frontend_zip,
                {
                    "zaparoo/frontend": b"frontend",
                    "zaparoo/menu_zaparoo.rbf": b"menu",
                    profile + "profile": b"profile",
                    profile + "zaparoo_scanout.ko": b"module",
                    profile + "source/README.md": b"readme",
                    "LICENSES/COPYING": b"license",
                },
            )
            summary = build_zaparoo_db.build_frontend_summary(frontend_zip)

        self.assertEqual(
            set(summary["files"]),
            {
                "zaparoo/frontend",
                "zaparoo/menu_zaparoo.rbf",
                profile + "profile",
                profile + "zaparoo_scanout.ko",
                profile + "source/README.md",
            },
        )
        module = summary["files"][profile + "zaparoo_scanout.ko"]
        self.assertEqual(module["hash"], hashlib.md5(b"module").hexdigest())
        self.assertEqual(module["arc_at"], profile + "zaparoo_scanout.ko")
        self.assertEqual(module["arc_id"], "zaparoo_frontend")
        self.assertEqual(
            set(summary["folders"]),
            {
                "zaparoo/",
                "zaparoo/modules/",
                "zaparoo/modules/6.18.38-MiSTer/",
                profile,
                profile + "source/",
            },
        )

    def test_frontend_without_modules_installs_only_base_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            frontend_zip = Path(tmp) / "frontend.zip"
            self.write_zip(
                frontend_zip,
                {"zaparoo/frontend": b"frontend", "zaparoo/menu_zaparoo.rbf": b"menu"},
            )
            summary = build_zaparoo_db.build_frontend_summary(frontend_zip)

        self.assertEqual(
            set(summary["files"]), {"zaparoo/frontend", "zaparoo/menu_zaparoo.rbf"}
        )
        self.assertEqual(set(summary["folders"]), {"zaparoo/"})

    def test_stable_main_selector_uses_latest_stable_release(self) -> None:
        expected = build_zaparoo_db.ReleaseAsset(
            "MiSTer_Zaparoo_20260707",
            "MiSTer_Zaparoo",
            "https://example/MiSTer_Zaparoo",
        )
        with mock.patch.object(
            build_zaparoo_db,
            "find_release_asset",
            return_value=expected,
        ) as find_release_asset:
            actual = build_zaparoo_db.find_main_release_asset("stable")

        self.assertEqual(actual, expected)
        find_release_asset.assert_called_once_with(
            build_zaparoo_db.MAIN_REPO,
            "latest",
            build_zaparoo_db.MAIN_ASSET_RE,
        )

    def test_explicit_main_selector_forwards_release_tag(self) -> None:
        tag = "MiSTer_Zaparoo_20260707"
        expected = build_zaparoo_db.ReleaseAsset(
            tag,
            "MiSTer_Zaparoo",
            "https://example/MiSTer_Zaparoo",
        )
        with mock.patch.object(
            build_zaparoo_db,
            "find_release_asset",
            return_value=expected,
        ) as find_release_asset:
            actual = build_zaparoo_db.find_main_release_asset(tag)

        self.assertEqual(actual, expected)
        find_release_asset.assert_called_once_with(
            build_zaparoo_db.MAIN_REPO,
            tag,
            build_zaparoo_db.MAIN_ASSET_RE,
        )

    def test_main_asset_selector_excludes_debug_binary(self) -> None:
        tag = "MiSTer_Zaparoo_20260707"
        release_url = f"https://api.github.com/repos/{build_zaparoo_db.MAIN_REPO}/releases/tags/{tag}"
        with mock.patch.object(
            build_zaparoo_db,
            "read_json_url",
            return_value={
                "tag_name": tag,
                "assets": [
                    {
                        "name": "MiSTer_Zaparoo.elf",
                        "browser_download_url": "https://example/MiSTer_Zaparoo.elf",
                    },
                    {
                        "name": "MiSTer_Zaparoo",
                        "browser_download_url": "https://example/MiSTer_Zaparoo",
                    },
                ],
            },
        ) as read_json_url:
            asset = build_zaparoo_db.find_release_asset(
                build_zaparoo_db.MAIN_REPO,
                tag,
                build_zaparoo_db.MAIN_ASSET_RE,
            )

        self.assertEqual(
            asset,
            build_zaparoo_db.ReleaseAsset(
                tag,
                "MiSTer_Zaparoo",
                "https://example/MiSTer_Zaparoo",
            ),
        )
        read_json_url.assert_called_once_with(release_url)

    @staticmethod
    def write_zip(path: Path, files: dict[str, bytes]) -> None:
        with zipfile.ZipFile(path, "w") as archive:
            for name, contents in files.items():
                archive.writestr(name, contents)


if __name__ == "__main__":
    unittest.main()
