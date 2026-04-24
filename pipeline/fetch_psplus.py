import json
import re
from datetime import date
from pathlib import Path

import requests

SOURCE_URL = "https://gamescriptions.com/subscription/service/ps_extra"
CACHE_PATH = Path("cache/gamescriptions_ps_extra.html")
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)


def _download(force: bool = False) -> str:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CACHE_PATH.exists() and not force:
        return CACHE_PATH.read_text()
    resp = requests.get(SOURCE_URL, headers={"User-Agent": UA}, timeout=30)
    resp.raise_for_status()
    CACHE_PATH.write_text(resp.text)
    return resp.text


def _extract_rsc_payload(html: str) -> str:
    pushes = re.findall(
        r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)', html
    )
    return "".join(json.loads('"' + p + '"') for p in pushes)


def _iter_game_objects(payload: str):
    i = 0
    while True:
        start = payload.find('{"game_id":', i)
        if start < 0:
            return
        depth = 0
        in_str = False
        esc = False
        j = start
        while j < len(payload):
            c = payload[j]
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = not in_str
            elif not in_str:
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            yield json.loads(payload[start : j + 1])
                        except json.JSONDecodeError:
                            pass
                        break
            j += 1
        i = j + 1


def _is_currently_available(raw_services, today: date) -> bool:
    for s in raw_services or []:
        if s.get("service") != "ps_extra":
            continue
        rel = s.get("schedule_release")
        rem = s.get("schedule_removal")
        if not rel:
            continue
        rel_d = date.fromisoformat(rel)
        rem_d = date.fromisoformat(rem) if rem else None
        if rel_d <= today and (rem_d is None or rem_d >= today):
            return True
    return False


def fetch(force_refresh: bool = False) -> list[dict]:
    html = _download(force=force_refresh)
    payload = _extract_rsc_payload(html)
    by_id: dict[int, dict] = {}
    for g in _iter_game_objects(payload):
        by_id[g["game_id"]] = g
    today = date.today()
    games = []
    for g in by_id.values():
        if g.get("game_status") != "public":
            continue
        if not _is_currently_available(g.get("services_raw"), today):
            continue
        genre_str = g.get("game_genre") or ""
        genres = [p.strip() for p in genre_str.split(",") if p.strip()]
        games.append(
            {
                "title": g["game_name"],
                "genres_psplus": genres,
                "release_year": g.get("release_year"),
            }
        )
    games.sort(key=lambda x: x["title"].lower())
    return games


if __name__ == "__main__":
    games = fetch()
    print(f"fetched {len(games)} currently-available PS Plus Extra games")
    for g in games[:10]:
        print(f"  - {g['title']} ({g['release_year']}) | {g['genres_psplus']}")
