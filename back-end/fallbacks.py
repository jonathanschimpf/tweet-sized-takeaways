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
    FallbackCategory.SOCIAL: "back-end/static/og-fallbacks/social.jpg",
    FallbackCategory.NEWS: "back-end/static/og-fallbacks/news.jpg",
    FallbackCategory.COOKIE: "back-end/static/og-fallbacks/cookie.jpg",
    FallbackCategory.WEIRD: "back-end/static/og-fallbacks/weirdlink.jpg",
}


# --- OG FALLBACK GETTER ---
def get_fallback_og(category: str) -> str:
    category_key = FallbackCategory(category) if category in FallbackCategory.__members__.values() else FallbackCategory.DEFAULT
    return FALLBACK_OG_IMAGES.get(category_key, FALLBACK_OG_IMAGES[FallbackCategory.DEFAULT])
    