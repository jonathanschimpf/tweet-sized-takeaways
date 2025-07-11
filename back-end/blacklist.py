from fallbacks import FallbackCategory

# --- BLACKLISTED DOMAINS ---
BLACKLISTED_DOMAINS = {
    FallbackCategory.NEWS: [
        "washingtonpost.com",
        "nytimes.com",
        "bloomberg.com",
        "cnbc.com",
        "foxnews.com",
    ],
    FallbackCategory.SOCIAL: [
        "instagram.com",
        "facebook.com",
        "threads.net",
        "threads.com",
        "tiktok.com",
        "linkedin.com",
        "twitter.com",
    ],
}

# --- COOKIE WALL DOMAINS ---
COOKIE_WALL_DOMAINS = [
    "docs.google.com",
]


# --- CLEAN + NORMALIZE DOMAIN INPUT ---
def normalize_domain(domain: str) -> str:
    domain = domain.lower().strip()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


# --- BLACKLIST CATEGORY CHECK ---
def get_blacklist_category(domain: str):
    domain = normalize_domain(domain)
    for category, domains in BLACKLISTED_DOMAINS.items():
        if domain in domains:
            return category
    return None


# --- CHECK IF COOKIE-GATED ---
def is_cookie_gated(domain: str):
    return normalize_domain(domain) in COOKIE_WALL_DOMAINS
