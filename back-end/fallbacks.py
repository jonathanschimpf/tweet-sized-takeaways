# fallbacks.py

from enum import Enum

class FallbackCategory(str, Enum):
    SOCIAL = "social"
    NEWS = "news"
    COOKIE = "cookie"
    WEIRD = "weird"
    DEFAULT = "weird"


# --- FALLBACK OG IMAGES ---
FALLBACK_OG_IMAGES = {
    FallbackCategory.SOCIAL: "public/og-fallbacks/social.jpg",
    FallbackCategory.NEWS: "public/og-fallbacks/news.jpg",
    FallbackCategory.COOKIE: "public/og-fallbacks/cookie.jpg",
    FallbackCategory.WEIRD: "public/og-fallbacks/weirdlink.jpg",
}


# --- OG FALLBACK GETTER ---
def get_fallback_og(category: str) -> str:
    category_key = FallbackCategory(category) if category in FallbackCategory.__members__.values() else FallbackCategory.DEFAULT
    return FALLBACK_OG_IMAGES.get(category_key, FALLBACK_OG_IMAGES[FallbackCategory.DEFAULT])
    