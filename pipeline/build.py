import csv
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from pipeline import (
    enrich_rawg,
    fetch_crossplay,
    fetch_crossplaygames,
    fetch_psplus,
)
from pipeline.normalize import canonical

load_dotenv()

OUTPUT_PATH = Path("games.json")
METADATA_OVERRIDE_PATH = Path("overrides/metadata.csv")

CROSSPLAY_RAWG_TAG = "cross-platform-multiplayer"
MP_TAGS = {"online-pvp", "online-co-op", "online-multiplayer"}
PS_RELEVANT = {"PS4", "PS5", "PC", "XBO", "XBSX", "Switch"}

# Map RAWG tag slugs + GameScriptions genre tokens → camera/perspective labels.
# Derivation looks at both sources so that Wikipedia-only games (no PS+
# metadata) still get classified via RAWG.
VIEW_TYPE_RULES = {
    "First-Person": {"first-person", "fps"},
    "Third-Person": {"third-person", "third-person-perspective"},
    "Top-Down/Isometric": {"isometric", "top-down", "top-down/isometric"},
    "Side-Scroller/2D": {"2d", "side-scroller", "side-view", "platformer"},
    "Fixed Camera": {"fixed-camera"},
    "VR": {"vr", "virtual-reality"},
}


def _derive_view_types(tags: list[str], psplus_genres: list[str]) -> list[str]:
    signals = {t.lower().replace(" ", "-") for t in tags}
    signals |= {t.lower().replace(" ", "-") for t in psplus_genres}
    out: list[str] = []
    for label, matches in VIEW_TYPE_RULES.items():
        if signals & matches:
            out.append(label)
    # "Platformer" genre alone should not count as Side-Scroller (some
    # platformers are 3D). Require an explicit 2D / side signal when
    # matched only via "platformer".
    if (
        "Side-Scroller/2D" in out
        and not (signals & {"2d", "side-scroller", "side-view"})
    ):
        out.remove("Side-Scroller/2D")
    return out

RAWG_PLATFORM_MAP = {
    "PlayStation 4": "PS4",
    "PlayStation 5": "PS5",
    "PC": "PC",
    "Xbox One": "XBO",
    "Xbox Series S/X": "XBSX",
    "Nintendo Switch": "Switch",
    "macOS": "PC",
    "Linux": "PC",
}


def _load_metadata_overrides() -> dict[str, dict]:
    if not METADATA_OVERRIDE_PATH.exists():
        return {}
    out: dict[str, dict] = {}
    with METADATA_OVERRIDE_PATH.open() as f:
        for row in csv.DictReader(f):
            title = (row.get("title") or "").strip()
            if not title:
                continue
            cleaned: dict = {}
            for k in ("online_coop", "splitscreen"):
                v = (row.get(k) or "").strip().lower()
                if v in ("true", "1", "yes"):
                    cleaned[k] = True
                elif v in ("false", "0", "no"):
                    cleaned[k] = False
            players = (row.get("players") or "").strip()
            if players.isdigit():
                cleaned["players"] = int(players)
            genres = (row.get("genres") or "").strip()
            if genres:
                cleaned["genres"] = [
                    g.strip() for g in genres.split("|") if g.strip()
                ]
            out[title] = cleaned
    return out


def _apply_overrides(game: dict, overrides: dict[str, dict]) -> dict:
    o = overrides.get(game["title"])
    if not o:
        return game
    return {**game, **{k: v for k, v in o.items() if v is not None}}


def _rawg_platform_set(rawg: dict) -> set[str]:
    out = set()
    for name in rawg.get("platforms") or []:
        norm = RAWG_PLATFORM_MAP.get(name)
        if norm:
            out.add(norm)
    return out


def _slug_title_guess(slug: str) -> str:
    """Cheap slug→title reversal; overridden by JSON-LD name on detail fetch."""
    import re as _re

    s = _re.sub(r"-\d+$", "", slug)
    return " ".join(w.capitalize() for w in s.split("-"))


def _build_master(
    ps_games: list[dict],
    wiki_crossplay: list[dict],
    cg_index: dict[str, str],
) -> dict[str, dict]:
    """Merge PS+ Extra + Wikipedia + crossplaygames.com slugs by canonical title."""
    master: dict[str, dict] = {}
    for g in ps_games:
        key = canonical(g["title"])
        master[key] = {
            "title": g["title"],
            "release_year": g.get("release_year"),
            "psplus_genres": g.get("genres_psplus") or [],
            "in_extra": True,
            "wiki_platforms": None,
        }
    for g in wiki_crossplay:
        key = canonical(g["title"])
        if key in master:
            master[key]["wiki_platforms"] = set(g["platforms"])
        else:
            master[key] = {
                "title": g["title"],
                "release_year": None,
                "psplus_genres": [],
                "in_extra": False,
                "wiki_platforms": set(g["platforms"]),
            }
    for key, slug in cg_index.items():
        if key in master:
            continue
        master[key] = {
            "title": _slug_title_guess(slug),
            "release_year": None,
            "psplus_genres": [],
            "in_extra": False,
            "wiki_platforms": None,
        }
    return master


def _classify(
    key: str,
    entry: dict,
    rawg: dict,
    cg_index: dict[str, str],
) -> tuple[set[str], list[str]] | None:
    """Return (crossplay_platforms, sources) or None if game has no signal."""
    sources: list[str] = []
    cp: set[str] = set()

    # Signal: Wikipedia list (or known_crossplay override)
    wiki_plats = entry.get("wiki_platforms")
    if wiki_plats:
        sources.append("wikipedia")
        cp |= wiki_plats

    # Signal: crossplaygames.com detail page
    cg_negative = False
    cg_slug = cg_index.get(key)
    if cg_slug:
        try:
            cg_result = fetch_crossplaygames.check(cg_slug)
            cg_plats = fetch_crossplaygames.normalized_platforms(cg_result)
            if cg_plats:
                sources.append("crossplaygames")
                cp |= cg_plats
                # If we stubbed a title from the slug, upgrade to the
                # real name from JSON-LD.
                cg_name = cg_result.get("name")
                if cg_name and not entry.get("wiki_platforms") and not entry["in_extra"]:
                    entry["title"] = cg_name
            elif (
                cg_result.get("supported") is False
                or cg_result.get("cross_gen_only")
            ):
                cg_negative = True
        except Exception as e:
            print(f"     warn: crossplaygames fetch failed for {entry['title']}: {e}")

    # RAWG signals are only applied to PS+ Extra games — for the wider
    # catalog we trust Wikipedia's per-row platform info instead.
    if entry["in_extra"]:
        tags = set(rawg.get("tags") or [])
        rawg_plats = _rawg_platform_set(rawg)
        if CROSSPLAY_RAWG_TAG in tags and (
            {"PS4", "PS5"} <= rawg_plats or {"PS5", "PC"} <= rawg_plats
        ):
            sources.append("rawg_tag")
            cp |= rawg_plats & PS_RELEVANT
        if (
            CROSSPLAY_RAWG_TAG not in tags
            and (MP_TAGS & tags)
            and {"PS4", "PS5"} <= rawg_plats
        ):
            sources.append("rawg_platforms")
            cp |= rawg_plats & PS_RELEVANT

    if cg_negative:
        sources = [s for s in sources if s not in ("rawg_platforms", "rawg_tag")]

    if not sources or not cp:
        return None
    return cp, sources


def _in_any_target_combo(cp: set[str]) -> bool:
    return {"PS4", "PS5"} <= cp or {"PS5", "PC"} <= cp


def main() -> None:
    print("[1/5] fetching PS Plus Extra catalog…")
    ps_games = fetch_psplus.fetch()
    print(f"     -> {len(ps_games)} currently-available Extra games")

    print("[2/5] fetching Wikipedia crossplay + known_crossplay overrides…")
    wiki_crossplay = fetch_crossplay.fetch()
    print(f"     -> {len(wiki_crossplay)} rows in wider crossplay catalog")

    print("[3/5] loading crossplaygames.com slug index…")
    cg_index = fetch_crossplaygames.load_slug_index()
    print(f"     -> {len(cg_index)} slugs")

    if not os.environ.get("RAWG_API_KEY"):
        print("[!] RAWG_API_KEY not set — aborting; this pipeline needs RAWG.")
        return

    master = _build_master(ps_games, wiki_crossplay, cg_index)
    print(f"[4/5] enriching {len(master)} unique titles via RAWG (cached)…")

    overrides = _load_metadata_overrides()
    qualifying: list[dict] = []

    for i, (key, entry) in enumerate(master.items()):
        if (i + 1) % 50 == 0:
            print(f"     …{i + 1}/{len(master)}")
        rawg = enrich_rawg.enrich(entry["title"])
        result = _classify(key, entry, rawg, cg_index)
        if result is None:
            continue
        cp, sources = result
        if not _in_any_target_combo(cp):
            continue

        auth = {"wikipedia", "rawg_tag", "crossplaygames"}
        confidence = "high" if set(sources) & auth else "medium"

        view_types = _derive_view_types(
            rawg.get("tags") or [], entry.get("psplus_genres") or []
        )

        record = {
            "title": entry["title"],
            "genres": rawg["genres"] or entry["psplus_genres"],
            "tags": rawg["tags"],
            "platforms": rawg["platforms"],
            "splitscreen": rawg["splitscreen"],
            "online_coop": rawg["online_coop"],
            "players": rawg["players"],
            "rawg_id": rawg["rawg_id"],
            "rawg_slug": rawg["rawg_slug"],
            "background_image": rawg["background_image"],
            "release_year": entry["release_year"],
            "sources": sources,
            "confidence": confidence,
            "crossplay_platforms": sorted(cp),
            "in_extra": entry["in_extra"],
            "view_types": view_types,
        }
        qualifying.append(_apply_overrides(record, overrides))

    # Dedup by final canonical title — the JSON-LD name upgrade for slug-only
    # games can produce two records that canonicalize the same once upgraded
    # (e.g. Wikipedia "Mortal Kombat 11" + slug `mortal-kombat-11-2`).
    merged: dict[str, dict] = {}
    for r in qualifying:
        k = canonical(r["title"])
        if k not in merged:
            merged[k] = r
        else:
            existing = merged[k]
            existing["sources"] = sorted(set(existing["sources"]) | set(r["sources"]))
            existing["crossplay_platforms"] = sorted(
                set(existing["crossplay_platforms"]) | set(r["crossplay_platforms"])
            )
            if r["in_extra"]:
                existing["in_extra"] = True
            if r["confidence"] == "high":
                existing["confidence"] = "high"
    qualifying = list(merged.values())
    qualifying.sort(key=lambda r: r["title"].lower())

    print(f"[5/5] writing games.json with {len(qualifying)} qualifying games…")
    OUTPUT_PATH.write_text(json.dumps(qualifying, indent=2))

    combos = {
        "PS4+PS5 (Extra)": 0,
        "PS5+PC (Extra)": 0,
        "PS4+PS5+PC (Extra)": 0,
        "PS5+PC (all)": 0,
        "PS4+PS5+PC (all)": 0,
    }
    for r in qualifying:
        p = set(r["crossplay_platforms"])
        if {"PS4", "PS5"} <= p and r["in_extra"]:
            combos["PS4+PS5 (Extra)"] += 1
        if {"PS5", "PC"} <= p and r["in_extra"]:
            combos["PS5+PC (Extra)"] += 1
        if {"PS4", "PS5", "PC"} <= p and r["in_extra"]:
            combos["PS4+PS5+PC (Extra)"] += 1
        if {"PS5", "PC"} <= p:
            combos["PS5+PC (all)"] += 1
        if {"PS4", "PS5", "PC"} <= p:
            combos["PS4+PS5+PC (all)"] += 1
    for k, v in combos.items():
        print(f"     {k}: {v}")


if __name__ == "__main__":
    main()
