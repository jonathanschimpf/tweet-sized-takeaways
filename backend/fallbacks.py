# ✅ UPDATED fallbacks.py — WITH THREADS FALLBACK LOOP 🧵

import os
import random
from enum import Enum


# ✅ FALLBACK CATEGORIES ENUM
class FallbackCategory(str, Enum):
    SOCIAL = "social"
    NEWS = "news"
    COOKIE = "cookie"
    GOV = "gov"
    THREADS = "threads"  # 🧵 META IS SPECIAL — RANDOMIZED FALLBACKS LIVE BELOW
    WEIRD = "weird"
    DEFAULT = "weird"


# ✅ STATIC FALLBACK IMAGE PATHS (used for all categories except THREADS which is randomized)
FALLBACK_OG_IMAGES = {
    FallbackCategory.SOCIAL: "/images/og-fallbacks/social.jpg",
    FallbackCategory.NEWS: "/images/og-fallbacks/news.jpg",
    FallbackCategory.COOKIE: "/images/og-fallbacks/cookie.jpg",
    FallbackCategory.GOV: "/images/og-fallbacks/bigbrotherIswatchingyou.jpg",
    FallbackCategory.THREADS: "/images/og-fallbacks/threads-og-image-fallback.jpg",  # ✅ default if random fails
    FallbackCategory.WEIRD: "/images/og-fallbacks/weirdlink.jpg",
}


# ✅ STATIC CATEGORY LOOKUP FALLBACK
def get_fallback_og(category: str) -> str:
    category_key = (
        FallbackCategory(category)
        if category in FallbackCategory.__members__.values()
        else FallbackCategory.DEFAULT
    )
    return FALLBACK_OG_IMAGES.get(
        category_key, FALLBACK_OG_IMAGES[FallbackCategory.DEFAULT]
    )


# ✅ RANDOM THREADS IMAGE LOOP 🧵
THREADS_OG_DIR = os.path.join("public", "images", "og-fallbacks")


def get_random_threads_fallback() -> str:
    try:
        filenames = [
            f"/images/og-fallbacks/{f}"
            for f in os.listdir(THREADS_OG_DIR)
            if f.startswith("threads-og-image-fallback")
            and f.endswith((".jpg", ".jpeg", ".png"))
        ]
        print(f"🧵 Found {len(filenames)} Threads fallback image(s).")
        return (
            random.choice(filenames)
            if filenames
            else FALLBACK_OG_IMAGES[FallbackCategory.THREADS]
        )
    except Exception as e:
        print(f"⚠️ Failed to get Threads fallback: {e}")
        return FALLBACK_OG_IMAGES[FallbackCategory.THREADS]
