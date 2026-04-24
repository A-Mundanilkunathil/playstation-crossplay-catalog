import csv
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

SOURCE_URL = (
    "https://en.wikipedia.org/wiki/"
    "List_of_video_games_that_support_cross-platform_play"
)
CACHE_PATH = Path("cache/wikipedia_crossplay.html")
KNOWN_PATH = Path("overrides/known_crossplay.csv")
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)

# Columns in the Wikipedia table that count as "PC" crossplay.
_PC_COL_MARKERS = ("Windows PC", "Linux", "Mac")


def _download(force: bool = False) -> str:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CACHE_PATH.exists() and not force:
        return CACHE_PATH.read_text()
    resp = requests.get(SOURCE_URL, headers={"User-Agent": UA}, timeout=30)
    resp.raise_for_status()
    CACHE_PATH.write_text(resp.text)
    return resp.text


def fetch(force_refresh: bool = False) -> list[dict]:
    """
    Returns a list of {title, platforms, source} where platforms is a
    set of the crossplay-supporting platforms listed on Wikipedia for
    that game, normalized to {"PC", "PS4", "PS5", "XBO", "XBSX", "Switch"}.
    """
    html = _download(force=force_refresh)
    tables = pd.read_html(StringIO(html))
    df = max(tables, key=lambda t: t.shape[0])
    df.columns = ["|".join(str(c) for c in col).strip("|") for col in df.columns]

    title_col = next(c for c in df.columns if c.startswith("Title"))
    ps4_col = next(c for c in df.columns if "PS4" in c)
    ps5_col = next(c for c in df.columns if "PS5" in c)
    xbo_col = next(c for c in df.columns if c.endswith("|XBO|XBO"))
    xbsx_col = next((c for c in df.columns if "XBSX" in c), None)
    switch_col = next((c for c in df.columns if c.endswith("Switch|Switch")), None)
    pc_cols = [c for c in df.columns if any(m in c for m in _PC_COL_MARKERS)]

    out: list[dict] = []
    seen: set[str] = set()
    for _, row in df.iterrows():
        raw_title = str(row[title_col]).split("[")[0].strip()
        if not raw_title or raw_title in seen:
            continue
        plats: set[str] = set()
        if pd.notna(row[ps4_col]):
            plats.add("PS4")
        if pd.notna(row[ps5_col]):
            plats.add("PS5")
        if pd.notna(row[xbo_col]):
            plats.add("XBO")
        if xbsx_col and pd.notna(row[xbsx_col]):
            plats.add("XBSX")
        if switch_col and pd.notna(row[switch_col]):
            plats.add("Switch")
        if any(pd.notna(row[c]) for c in pc_cols):
            plats.add("PC")
        if not plats:
            continue
        seen.add(raw_title)
        out.append(
            {"title": raw_title, "platforms": sorted(plats), "source": "wikipedia"}
        )

    for row in _load_known():
        t = row["title"]
        if t in seen:
            continue
        seen.add(t)
        plats_raw = (row.get("platforms") or "PS4,PS5").strip()
        plats = [p.strip() for p in plats_raw.split(",") if p.strip()]
        out.append({"title": t, "platforms": sorted(plats), "source": "known_override"})
    return out


def _load_known() -> list[dict]:
    if not KNOWN_PATH.exists():
        return []
    with KNOWN_PATH.open() as f:
        return [r for r in csv.DictReader(f) if (r.get("title") or "").strip()]


if __name__ == "__main__":
    games = fetch()
    print(f"fetched {len(games)} crossplay games")
    from collections import Counter

    combos = Counter()
    for g in games:
        p = set(g["platforms"])
        if {"PS4", "PS5"} <= p:
            combos["PS4+PS5"] += 1
        if {"PS5", "PC"} <= p:
            combos["PS5+PC"] += 1
        if {"PS4", "PS5", "PC"} <= p:
            combos["PS4+PS5+PC"] += 1
    for k, v in combos.items():
        print(f"  {k}: {v}")
