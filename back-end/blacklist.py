# --- BLACKLISTED DOMAINS ---
BLACKLISTED_DOMAINS = {
    "news": [
        "washingtonpost.com",
        "nytimes.com",
        "bloomberg.com",
        "cnbc.com",
    ],
    "social": [
        "instagram.com",
        "facebook.com",
        "threads.net",
        "tiktok.com",
        "linkedin.com",
        "x.com",
        "twitter.com",
    ],
}

# --- COOKIE WALL DOMAINS ---
COOKIE_WALL_DOMAINS = [
    "docs.google.com",
]

# --- BLACKLIST CATEGORY CHECK ---
def get_blacklist_category(domain: str):
    for category, domains in BLACKLISTED_DOMAINS.items():
        if any(d in domain for d in domains):
            return category
    return None


# --- CHECK IF COOKIE-GATED ---
def is_cookie_gated(domain: str):
    return domain in COOKIE_WALL_DOMAINS
