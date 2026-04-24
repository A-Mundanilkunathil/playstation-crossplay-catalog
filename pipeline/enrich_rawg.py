import json
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

CACHE_DIR = Path("cache/rawg")
API_BASE = "https://api.rawg.io/api/games"

SPLITSCREEN_SLUGS = {
    "split-screen",
    "splitscreen",
    "local-co-op",
    "local-multiplayer",
    "couch-co-op",
}
ONLINE_COOP_SLUGS = {
    "online-co-op",
    "co-op",
    "cooperative",
    "online-multi-player",
    "multiplayer",
}
PLAYER_COUNT_RE = re.compile(r"^(\d+)-players?$")


def _slugify(title: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")
    return s[:200]


def _search(title: str, api_key: str) -> dict | None:
    cache_path = CACHE_DIR / f"{_slugify(title)}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    resp = requests.get(
        API_BASE,
        params={"search": title, "key": api_key, "page_size": 5},
        timeout=30,
    )
    if resp.status_code == 429:
        time.sleep(5)
        resp = requests.get(
            API_BASE,
            params={"search": title, "key": api_key, "page_size": 5},
            timeout=30,
        )
    resp.raise_for_status()
    data = resp.json()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(data))
    return data


def _pick_best(results: list[dict], title: str) -> dict | None:
    if not results:
        return None
    t_low = title.lower()
    for r in results:
        if (r.get("name") or "").lower() == t_low:
            return r
    return results[0]


def _flags_from_tags(tags: list[dict]) -> dict:
    slugs = {t.get("slug", "") for t in tags or []}
    players = None
    for s in slugs:
        m = PLAYER_COUNT_RE.match(s)
        if m:
            n = int(m.group(1))
            players = max(players or 0, n)
    return {
        "splitscreen": bool(slugs & SPLITSCREEN_SLUGS),
        "online_coop": bool(slugs & ONLINE_COOP_SLUGS),
        "players": players,
    }


def _empty() -> dict:
    return {
        "genres": [],
        "tags": [],
        "platforms": [],
        "splitscreen": None,
        "online_coop": None,
        "players": None,
        "rawg_id": None,
        "rawg_slug": None,
        "background_image": None,
    }


def enrich(title: str) -> dict:
    api_key = os.environ.get("RAWG_API_KEY", "").strip()
    if not api_key:
        return _empty()
    data = _search(title, api_key)
    best = _pick_best((data or {}).get("results", []), title)
    if not best:
        return _empty()
    genres = [g.get("name") for g in best.get("genres") or [] if g.get("name")]
    tags = [t.get("slug") for t in best.get("tags") or [] if t.get("slug")]
    platforms = [
        p.get("platform", {}).get("name")
        for p in best.get("platforms") or []
        if p.get("platform", {}).get("name")
    ]
    flags = _flags_from_tags(best.get("tags") or [])
    return {
        "genres": genres,
        "tags": tags,
        "platforms": platforms,
        **flags,
        "rawg_id": best.get("id"),
        "rawg_slug": best.get("slug"),
        "background_image": best.get("background_image"),
    }


if __name__ == "__main__":
    import sys

    q = sys.argv[1] if len(sys.argv) > 1 else "Destiny 2"
    print(json.dumps(enrich(q), indent=2))
