from enum import Enum


class FallbackCategory(str, Enum):
    SOCIAL = "social"
    NEWS = "news"
    COOKIE = "cookie"
    WEIRD = "weird"
    GOV = "gov"
    THREADS = "threads"  # 🧵 ONLY META PLATFORM WHERE SCRAPING GETS WEIRD ON IMAGES 🫥
    DEFAULT = "weird"


# --- FALLBACK OG IMAGES SANS /static ---
FALLBACK_OG_IMAGES = {
    FallbackCategory.SOCIAL: "/images/og-fallbacks/social.jpg",
    FallbackCategory.NEWS: "/images/og-fallbacks/news.jpg",
    FallbackCategory.COOKIE: "/images/og-fallbacks/cookie.jpg",
    FallbackCategory.GOV: "/images/og-fallbacks/bigbrotherIswatchingyou.jpg",
    FallbackCategory.THREADS: "/images/og-fallbacks/threads-og-image-fallback.jpg",  # 🧵 HAVE SOME THREADS LOGOS
    FallbackCategory.WEIRD: "/images/og-fallbacks/weirdlink.jpg",
}


# --- OG FALLBACK GETTER ---
def get_fallback_og(category: str) -> str:
    category_key = (
        FallbackCategory(category)
        if category in FallbackCategory.__members__.values()
        else FallbackCategory.DEFAULT
    )
    return FALLBACK_OG_IMAGES.get(
        category_key, FALLBACK_OG_IMAGES[FallbackCategory.DEFAULT]
    )
