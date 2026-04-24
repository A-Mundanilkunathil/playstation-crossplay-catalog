# PS Plus Extra + PS4/PS5 Crossplay Catalog

Local pipeline + static web UI for browsing games that are:

1. Currently on the PlayStation Plus **Extra** subscription catalog (no extra purchase needed).
2. Support online multiplayer with **PS4 ↔ PS5 crossplay**.

Each game card can show labels: genres (FPS, RPG, ...), player count, splitscreen support, and online co-op support. A **Show labels** toggle at the top reveals/hides the badges.

## Setup

```sh
cd /Users/stephanievu/ps-plus-crossplay
make install                         # creates .venv and installs deps
cp .env.example .env                 # then edit .env and paste your RAWG key
```

Get a free RAWG key at https://rawg.io/apidocs (2-minute signup).

## Run

```sh
make refresh   # fetch sources, join, enrich, write games.json
make serve     # open http://localhost:8000
```

Re-run `make refresh` when Sony rotates the Extra lineup (roughly monthly).

## Data sources

| Source | What we use |
|---|---|
| [gamescriptions.com](https://gamescriptions.com/subscription/service/ps_extra) | PS Plus Extra catalog — game titles, release dates, and `schedule_removal` dates so we filter to what's currently available. |
| [Wikipedia cross-platform play list](https://en.wikipedia.org/wiki/List_of_video_games_that_support_cross-platform_play) | Authoritative but incomplete list of PS4↔PS5 crossplay games. |
| `overrides/known_crossplay.csv` | Hand-maintained list of PS Plus Extra titles with confirmed PS4/PS5 crossplay that Wikipedia misses. |
| [RAWG API](https://rawg.io/apidocs) | Per-game metadata: genres, splitscreen/online co-op flags, player count, cover image. |

Original plan mentioned [Squirrels/ps-plus-games-api](https://github.com/Squirrels/ps-plus-games-api) as the catalog source — it turns out to only cover the monthly **Essential** freebies, not the Extra tier. GameScriptions has the full Extra catalog plus schedule data.

## Manual overrides

If a game is dropped by fuzzy matching, has wrong metadata, or is a crossplay game Wikipedia doesn't list:

- **`overrides/known_crossplay.csv`** — add titles with confirmed PS4↔PS5 crossplay. Title must match the PS Plus Extra catalog spelling.
- **`overrides/aliases.csv`** — map PS Plus title → canonical crossplay title when fuzzy matching fails.
- **`overrides/metadata.csv`** — hand-written flags that win over RAWG (columns: `title,online_coop,splitscreen,players,genres`; genres are `|`-separated).

After each `make refresh`, check `review.tsv` (only written when there are borderline matches) for titles to confirm.

## Known tradeoffs

- **Wikipedia coverage is narrow** — out of 372 currently-available Extra games, only ~10 match the Wikipedia crossplay list without manual augmentation. The `known_crossplay.csv` override is the intended extensibility point.
- **RAWG tags are user-submitted** — `splitscreen` / `online-co-op` are hints, not truth. `metadata.csv` is the fix for titles RAWG gets wrong.
- **GameScriptions is community-maintained** — if it goes stale or formats change, the RSC-stream parser in `pipeline/fetch_psplus.py` will need updating.
