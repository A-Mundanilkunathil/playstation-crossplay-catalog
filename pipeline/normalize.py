import re
import unicodedata

_ROMAN = {
    " ii": " 2", " iii": " 3", " iv": " 4", " v": " 5", " vi": " 6",
    " vii": " 7", " viii": " 8", " ix": " 9", " x": " 10",
}

_EDITION_SUFFIXES = re.compile(
    r"[:\-–—]\s*(deluxe|standard|gold|ultimate|legendary|definitive|"
    r"complete|enhanced|remastered|remaster|goty|game of the year|"
    r"anniversary|champions|director'?s cut|digital|platinum|special|"
    r"collector'?s)\s+edition.*$",
    re.IGNORECASE,
)

_PARENS_VIDEO_GAME = re.compile(r"\s*\(video game\)\s*", re.IGNORECASE)
_PARENS_YEAR = re.compile(r"\s*\(\d{4}\)\s*")
_TRADEMARKS = re.compile(r"[™®©]")
_NON_ALNUM = re.compile(r"[^a-z0-9& :]+")
_MULTI_SPACE = re.compile(r"\s+")


def canonical(title: str) -> str:
    if not title:
        return ""
    s = unicodedata.normalize("NFKD", title)
    s = _TRADEMARKS.sub("", s)
    s = s.lower()
    s = _PARENS_VIDEO_GAME.sub(" ", s)
    s = _PARENS_YEAR.sub(" ", s)
    s = _EDITION_SUFFIXES.sub("", s)
    padded = f" {s} "
    for roman, digit in _ROMAN.items():
        padded = padded.replace(roman, digit)
    s = padded.strip()
    s = _NON_ALNUM.sub(" ", s)
    s = _MULTI_SPACE.sub(" ", s).strip()
    return s
