import json
import re
import time
from pathlib import Path

import requests

from pipeline.normalize import canonical

SITEMAP_URLS = [
    "https://crossplaygames.com/games-sitemap1.xml",
    "https://crossplaygames.com/games-sitemap2.xml",
    "https://crossplaygames.com/games-sitemap3.xml",
]
CACHE_SITEMAP = Path("cache/crossplaygames_slugs.json")
CACHE_DETAILS = Path("cache/crossplaygames")
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)

_SLUG_TRAIL = re.compile(r"-\d+$")


def _slug_title_key(slug: str) -> str:
    trimmed = _SLUG_TRAIL.sub("", slug)
    return canonical(trimmed.replace("-", " "))


def load_slug_index(force: bool = False) -> dict[str, str]:
    """Returns map: canonical title -> slug."""
    if CACHE_SITEMAP.exists() and not force:
        return json.loads(CACHE_SITEMAP.read_text())
    out: dict[str, str] = {}
    for url in SITEMAP_URLS:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=30)
        resp.raise_for_status()
        for m in re.finditer(
            r"<loc>https://crossplaygames\.com/games/([^<]+)</loc>", resp.text
        ):
            slug = m.group(1)
            key = _slug_title_key(slug)
            # Prefer slugs without trailing -N suffix when both exist.
            if key not in out or not _SLUG_TRAIL.search(slug):
                out[key] = slug
    CACHE_SITEMAP.parent.mkdir(parents=True, exist_ok=True)
    CACHE_SITEMAP.write_text(json.dumps(out))
    return out


def _fetch_detail(slug: str) -> str:
    cache = CACHE_DETAILS / f"{slug}.html"
    if cache.exists():
        return cache.read_text()
    url = f"https://crossplaygames.com/games/{slug}"
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    resp.raise_for_status()
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(resp.text)
    time.sleep(0.2)
    return resp.text


def check(slug: str) -> dict:
    """
    Returns {supported, platforms, cross_gen_only} parsed from the page's
    JSON-LD + body text. `cross_gen_only` is True when the page text says
    the game is only cross-gen (save transfer) and not online crossplay —
    this catches false positives like Hogwarts Legacy.
    """
    html = _fetch_detail(slug)
    supported = None
    m = re.search(
        r'"name":\s*"Crossplay Supported"[^}]*?"value":\s*(true|false)', html
    )
    if m:
        supported = m.group(1) == "true"

    platforms: list[str] = []
    m = re.search(
        r'"name":\s*"Crossplay Platforms"[^}]*?"value":\s*(\[[^\]]*\])', html
    )
    if m:
        try:
            platforms = json.loads(m.group(1).replace(r"\/", "/"))
        except json.JSONDecodeError:
            platforms = []

    cross_gen_only = bool(
        re.search(r"(is|are)\s+only\s+cross[- ]gen", html, re.I)
        or re.search(r"does\s+not\s+support\s+cross[- ]?play", html, re.I)
    )
    return {
        "supported": supported,
        "platforms": platforms,
        "cross_gen_only": cross_gen_only,
    }


_PLATFORM_NORMALIZE = {
    "PS4": "PS4",
    "PS5": "PS5",
    "Xbox One": "XBO",
    "XBox Series S/X": "XBSX",
    "Xbox Series S/X": "XBSX",
    "Nintendo Switch": "Switch",
    "Switch": "Switch",
    "Steam (PC)": "PC",
    "Windows PC": "PC",
    "Steam": "PC",
    "PC": "PC",
    "Mac": "PC",
    "Linux": "PC",
}


def normalized_platforms(result: dict) -> set[str]:
    """Return crossplay platforms from a detail-page result, normalized to
    the same vocab as fetch_crossplay. Empty if supported==False or
    cross_gen_only==True (negative signals → exclude)."""
    if not result.get("supported"):
        return set()
    if result.get("cross_gen_only"):
        return set()
    out: set[str] = set()
    for name in result.get("platforms") or []:
        norm = _PLATFORM_NORMALIZE.get(name)
        if norm:
            out.add(norm)
    return out


def has_ps4_ps5_crossplay(result: dict) -> bool:
    plats = normalized_platforms(result)
    return "PS4" in plats and "PS5" in plats


if __name__ == "__main__":
    idx = load_slug_index()
    print(f"sitemap: {len(idx)} slugs")
    for title in ["hogwarts legacy", "street fighter 6", "mortal kombat 1"]:
        slug = idx.get(canonical(title))
        if not slug:
            print(f"  - {title}: not in sitemap")
            continue
        r = check(slug)
        print(
            f"  - {title} -> {slug}: "
            f"supported={r['supported']} plats={r['platforms']} "
            f"cross_gen_only={r['cross_gen_only']} "
            f"→ ps4↔ps5 crossplay={has_ps4_ps5_crossplay(r)}"
        )
