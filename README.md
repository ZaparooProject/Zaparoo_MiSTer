# Zaparoo MiSTer Database

MiSTer Downloader / Update All database for Zaparoo.

It installs:

- `Scripts/zaparoo.sh` — Zaparoo Core for MiSTer
- `zaparoo/frontend` — Zaparoo Frontend
- `zaparoo/MiSTer_Zaparoo` — frontend dependency
- `zaparoo/menu_zaparoo.rbf` — frontend dependency

## Manual install

Add this to `/media/fat/downloader.ini`:

```ini
[ZaparooProject/Zaparoo_MiSTer]
db_url = https://raw.githubusercontent.com/ZaparooProject/Zaparoo_MiSTer/db/db.json.zip
```

Then run `downloader` or `update_all`.

There is also a drop-in config ZIP:

```text
https://raw.githubusercontent.com/ZaparooProject/Zaparoo_MiSTer/db/downloader_ZaparooProject_Zaparoo_MiSTer.zip
```

## Binaries

This repo does not mirror Zaparoo binaries.

The workflow builds a Downloader database that points to official releases from:

- `ZaparooProject/zaparoo-core` — Core launcher script
- `ZaparooProject/zaparoo-frontend` — frontend binary and menu core
- `ZaparooProject/Main_MiSTer` — latest stable `MiSTer_Zaparoo` binary

Downloader installs only the MiSTer files it needs. Main updates independently of frontend releases so regular upstream MiSTer changes reach users promptly.

## Maintainer notes

The database rebuilds on pushes to `main`, on a schedule, and when run manually from GitHub Actions.

Manual runs can target specific `zaparoo-core`, `zaparoo-frontend`, or stable `Main_MiSTer` release tags. Otherwise the workflow uses the latest release from each repo.
