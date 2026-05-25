# backend/fallbacks.py
# ------------------------------------------------------------
# SIMPLE PUBLIC/ FALLBACK IMAGE LOOPS (THREADS + WEIRDLINK)
# - Cycles through JPG, JPEG, PNG images in each folder
# - Sorts numerically by the leading number in the filename
# - Loops 0..N, then repeats
# - Returns a /images URL (public/images is mounted at /images)
# ------------------------------------------------------------

from pathlib import Path
import re
from collections import defaultdict

_PUBLIC = Path("public")
_BASE = _PUBLIC / "images" / "og-fallbacks"

_NUM = re.compile(r"^(\d+)")


def _numeric_key(p: Path) -> int:
    m = _NUM.match(p.name)
    return int(m.group(1)) if m else 0


def _load(folder: str):
    d = _BASE / folder
    exts = ("*.jpg", "*.jpeg", "*.png")
    files = []
    for ext in exts:
        files.extend(d.glob(ext))
    return sorted(files, key=_numeric_key)


# Load once
_THREADS = _load("threads")
_WEIRDLINK = _load("weirdlink")

# Simple round-robin indexes
_idx = defaultdict(int)


def _next(items: list[Path], key: str) -> str:
    if not items:
        return "/images/og-fallbacks/social.jpg"  # Absolute fallback
    i = _idx[key]
    p = items[i]
    _idx[key] = (i + 1) % len(items)
    return "/" + p.relative_to(_PUBLIC).as_posix()


def next_threads_fallback() -> str:
    return _next(_THREADS, "threads")


def next_weirdlink_fallback() -> str:
    return _next(_WEIRDLINK, "weirdlink")


# ------------- SAVED THESE WEIRD TAKEAWAYS BECAUSE ------------------

WEIRDLINK_TAKEAWAYS = [
    "This link is weird. Here's a vibe instead.",
    "¯\\_(ツ)_/¯ Not much to summarize.",
    "The devs behind this domain were drinking haterade while putting this together. 😢",
    "We checked. The text ghosted us.",
    "It's giving… mysterious teaser energy.",
    "Visuals: 10/10. Summary: on vacation.",
    "Blocked from reaching their <meta> — it's up to you...",
    "404 for words, can't vibecode through this.",
    "Short on text, long on mood.",
    "<meta name=description>",
]


d
