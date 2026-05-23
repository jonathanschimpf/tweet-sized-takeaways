# backend/fallbacks.py
# ------------------------------------------------------------
# Fallback pools:
#   - Threads: random images in public/images/og-fallbacks/threads
#   - Twitter/X: random branded images for gated x.com/twitter.com links
#   - Weirdlink: cycles images + paired one-liners in public/images/og-fallbacks/weirdlink
# ------------------------------------------------------------

from pathlib import Path
from enum import Enum
from collections import defaultdict
import random
import re


class FallbackCategory(str, Enum):
    THREADS = "threads"
    TWITTER = "twitter"
    WEIRD = "weird"
    DEFAULT = "weird"


# Base paths
_PUBLIC = Path("public")
_BASE = _PUBLIC / "images" / "og-fallbacks"

_THREADS_DIR = _BASE / "threads"  # e.g. 10_threads-og-image-fallback.jpg
_TWITTER_DIR = _BASE / "twitter-x"
_WEIRDLINK_DIR = _BASE / "weirdlink"  # e.g. 01-weirdlink-og-image-fallback.jpg

_EXTS = ("*.jpg", "*.jpeg", "*.png")
_NUM = re.compile(r"^(\d+)")


def _numeric_key(p: Path) -> int:
    m = _NUM.match(p.name)
    return int(m.group(1)) if m else 0


def _load_images(folder: Path) -> list[Path]:
    files: list[Path] = []
    for ext in _EXTS:
        files.extend(folder.glob(ext))
    return sorted(files, key=_numeric_key)


# Load once
_THREADS_FILES = _load_images(_THREADS_DIR)
_TWITTER_FILES = _load_images(_TWITTER_DIR)
_WEIRDLINK_FILES = _load_images(_WEIRDLINK_DIR)

TWITTER_TAKEAWAYS = [
    "RIP Twitter 🪦",
    "March 21, 2006 – July 23, 2023 🕊️ Long live Twitter",
    "Twitter died so X could overcomplicate everything ☄️",
    "The blue bird era hit different 🌎",
    "Threads is now what Twitter was then 🧵",
    "Retweet if you remember when the platform was civilized ↺",
    "Goodnight little blue bird 🌙",
    "From tweets to whatever this is now ⚡",
    "The timeline used to feel human 🐦",
    "Before algorithms ate everything 📡",
]
TWITTER_TAKEAWAY = TWITTER_TAKEAWAYS[0]
_TWITTER_BRAND_FALLBACKS = [
    "/images/twitter-died.png",
    "/images/twitter-died-jetblack.png",
    "/images/x-overlap-twitter.png",
    "/images/tweet-sized-takeaway-logo-take/tweet-sized-takeaway-twitter-x-logo.jpg",
    "/images/tweet-sized-takeaway-logo-take/tweet-sized-takeaway-twitter-x-logo.png",
    "/images/tweet-sized-takeaway-logo-take/tweet-sized-takeaway-twitter-x-master-logo-2048.png",
    "/images/tweet-sized-takeaway-logo-take/tweet-sized-takeaway-twitter-x-master-logo_2048-11111.png",
    "/images/tweet-sized-takeaway-logo-take/tweet-sized-takeaway-twitter-x-master-logo_2048-1a1a1a.png",
    "/images/tweet-sized-takeaway-logo-take/tweet-sized-takeaway-twitter-x-master-logo_2048-flat-black.png",
    "/images/tweet-sized-takeaway-logo-take/twitter-bird-blue-logo.png",
]

# One shared index per loop
_idx = defaultdict(int)


def _bump(key: str, span: int) -> int:
    i = _idx[key]
    _idx[key] = (i + 1) % max(1, span)
    return i


def next_threads_fallback() -> str:
    """Return a random Threads fallback image URL."""
    n = len(_THREADS_FILES)
    if not n:
        # absolute safety, but still a valid path under /images; pick threads dir root if empty
        return "/images/og-fallbacks/threads/threads-og-image-fallback.jpg"
    p = random.choice(_THREADS_FILES)
    return "/" + p.relative_to(_PUBLIC).as_posix()


def next_twitter_fallback() -> tuple[str, str]:
    """Return a random Twitter/X fallback image URL plus random gated-platform copy."""
    takeaway = random.choice(TWITTER_TAKEAWAYS)
    if _TWITTER_FILES:
        p = random.choice(_TWITTER_FILES)
        return "/" + p.relative_to(_PUBLIC).as_posix(), takeaway
    return random.choice(_TWITTER_BRAND_FALLBACKS), takeaway


# ------------ Weirdlink copy -------------
WEIRDLINK_TAKEAWAYS = [
    "This link is weird. Here's a vibe instead.",
    "¯\\_(ツ)_/¯ Not much to summarize.",
    "The devs behind this domain were drinking haterade while putting this together.",
    "We checked. The text ghosted us.",
    "It's giving… mysterious teaser energy.",
    "Visuals: 10/10. Summary: on vacation.",
    "Blocked from reaching their <meta> — it's up to you...",
    "404 for words, can't vibecode through this.",
    "Short on text, long on mood.",
    "<meta name=description>",
    "Meta soup, no entrée.",
    "<head> is serving vibes, not words.",
    "All tags, no talk.",
    "Reading robots… robots said no.",
    "OG tags waving, content MIA.",
    "JavaScript-only gates. We're outside.",
    "Anti-scrape shields at 100%.",
    "Shadow DOM, shadow summary.",
    "Minified everything, including the meaning.",
    "Title says “Home.” That's it.",
    "Viewport set, viewpoint missing.",
    "<meta http-equiv=refresh> into the void.",
    "Canonical link to nowhere useful.",
    "x-robots-tag: please go away.",
    "Content-Security-Policy: do not perceive.",
    "Nosniff? I can't even sniff a sentence.",
    "Meta description placeholder energy.",
    "Single-page app skeleton. Flesh TBD.",
    "Unicode confetti, zero sentences.",
    "Head full, body ghosted.",
]


def next_weirdlink_pair() -> tuple[str, str]:
    """
    Advance the Weird loop ONCE and return (image_url, quip) from the SAME step.
    """
    n_img = len(_WEIRDLINK_FILES)
    n_q = len(WEIRDLINK_TAKEAWAYS)
    span = max(1, n_img, n_q)

    i = _bump("weird", span)

    if n_img:
        p = _WEIRDLINK_FILES[i % n_img]
        img_url = "/" + p.relative_to(_PUBLIC).as_posix()
    else:
        img_url = "/images/og-fallbacks/weirdlink/weirdlink.jpg"

    quip = (
        WEIRDLINK_TAKEAWAYS[i % n_q]
        if n_q
        else "This link is weird. Here's a vibe instead."
    )
    return img_url, quip
