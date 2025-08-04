from .fallbacks import FallbackCategory

# --- BLACKLISTED DOMAINS ---
BLACKLISTED_DOMAINS = {
    FallbackCategory.NEWS: [
        "washingtonpost.com",
        "nytimes.com",
        "cnbc.com",
        "foxnews.com",
    ],
    
    FallbackCategory.GOV: [
        # US Federal Agencies
        "usa.gov",
        "whitehouse.gov",
        "congress.gov",
        "senate.gov",
        "house.gov",
        "nasa.gov",
        "fbi.gov",
        "cia.gov",
        "irs.gov",
        "ssa.gov",
        "dod.gov",
        "va.gov",
        "usda.gov",
        "epa.gov",
        "cdc.gov",
        "hhs.gov",
        "dhs.gov",
        "cbp.gov",
        "uscis.gov",
        "ice.gov",
        "justice.gov",
        "ed.gov",
        "dot.gov",
        "energy.gov",
        "bls.gov",
        "state.gov",
        "treasury.gov",
        "military.gov",
        # Military
        "army.mil",
        "navy.mil",
        "marines.mil",
        "airforce.mil",
        "spaceforce.mil",
        "coastguard.mil",
        # State-level examples
        "dmv.state",
        "pa.gov",
        "ny.gov",
        "ca.gov",
        "tx.gov",
        "fl.gov",
        "ohio.gov",
        "mass.gov",
        "illinois.gov",
        "michigan.gov",
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

    # First check exact matches
    for category, domains in BLACKLISTED_DOMAINS.items():
        if domain in domains:
            return category

    # Then check for known official endings
    if domain.endswith(".gov") or domain.endswith(".mil") or domain.endswith(".state"):
        return FallbackCategory.GOV

    return None


# --- CHECK IF COOKIE-GATED ---
def is_cookie_gated(domain: str):
    return normalize_domain(domain) in COOKIE_WALL_DOMAINS
