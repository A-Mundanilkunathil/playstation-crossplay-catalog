import csv
import re
from pathlib import Path

from rapidfuzz import fuzz, process

from pipeline.normalize import canonical

ALIASES_PATH = Path("overrides/aliases.csv")
REVIEW_PATH = Path("review.tsv")

HIGH_CUTOFF = 93
LOW_CUTOFF = 86

_TRAILING_NUM = re.compile(r"(?:^|\s)(\d+)(?:\s|$)")


def _trailing_numbers(s: str) -> set[str]:
    """Numbers that appear as standalone tokens — sequel markers like '2' in 'risk of rain 2'."""
    return set(_TRAILING_NUM.findall(s))


def _numbers_compatible(a: str, b: str) -> bool:
    """Reject matches where sequel numbers disagree ('mortal kombat 1' vs 'mortal kombat 11')."""
    na, nb = _trailing_numbers(a), _trailing_numbers(b)
    if not na and not nb:
        return True
    return na == nb


def _load_aliases() -> dict[str, str]:
    if not ALIASES_PATH.exists():
        return {}
    out: dict[str, str] = {}
    with ALIASES_PATH.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            src = (row.get("psplus_title") or "").strip()
            dst = (row.get("canonical_title") or "").strip()
            if src and dst:
                out[canonical(src)] = canonical(dst)
    return out


def join(psplus: list[dict], crossplay: list[dict]) -> list[dict]:
    """
    Returns the subset of `psplus` games whose titles match a crossplay entry.
    Writes a review.tsv of borderline fuzzy matches (82-92 score) so the
    user can confirm them into overrides/aliases.csv.
    """
    aliases = _load_aliases()

    cx_canon_to_title = {canonical(c["title"]): c["title"] for c in crossplay}
    cx_canon_keys = list(cx_canon_to_title.keys())

    matched: list[dict] = []
    review_rows: list[tuple[str, str, float]] = []

    for g in psplus:
        orig = g["title"]
        key = canonical(orig)
        key = aliases.get(key, key)

        if key in cx_canon_to_title:
            matched.append({**g, "crossplay_title": cx_canon_to_title[key]})
            continue

        # token_sort_ratio is stricter than WRatio about word presence,
        # which avoids false positives like "A Hat in Time" ~ "A Realm Reborn".
        best = process.extractOne(
            key,
            cx_canon_keys,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=LOW_CUTOFF,
        )
        if best is None:
            continue
        cand, score, _ = best
        if not _numbers_compatible(key, cand):
            continue
        if score >= HIGH_CUTOFF:
            matched.append({**g, "crossplay_title": cx_canon_to_title[cand]})
        else:
            review_rows.append((orig, cx_canon_to_title[cand], score))

    _write_review(review_rows)
    return matched


def _write_review(rows: list[tuple[str, str, float]]) -> None:
    if not rows:
        if REVIEW_PATH.exists():
            REVIEW_PATH.unlink()
        return
    rows.sort(key=lambda r: -r[2])
    with REVIEW_PATH.open("w") as f:
        f.write("psplus_title\tcandidate_crossplay_title\tscore\n")
        for orig, cand, score in rows:
            f.write(f"{orig}\t{cand}\t{score:.1f}\n")


if __name__ == "__main__":
    from pipeline import fetch_crossplay, fetch_psplus

    p = fetch_psplus.fetch()
    c = fetch_crossplay.fetch()
    m = join(p, c)
    print(f"PS+ Extra: {len(p)}  |  Crossplay: {len(c)}  |  Matched: {len(m)}")
    for g in m[:10]:
        print(f"  - {g['title']}  ~  {g['crossplay_title']}")
