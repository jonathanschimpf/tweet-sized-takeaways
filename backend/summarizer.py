# backend/summarizer.py
# ------------------------------------------------------------
# OPEN GRAPH FIRST. HF SUMMARIZATION IS OPTIONAL + EXPLICIT.
# NO SOCIAL FALLBACK. TWO IMAGE FALLBACKS ONLY.
# ------------------------------------------------------------

import os
import re
import sys
import json
import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from urllib.parse import urlparse

from .fallbacks import (
    next_threads_fallback,
    next_twitter_fallback,
    next_weirdlink_pair,
)
from .text_cleanup import (
    build_pegasus_prompt,
    enforce_source_vocab,
    trim_to_280,
)

load_dotenv()

# ------------------------------------------------------------
# DEBUGGING
# ------------------------------------------------------------
# SET ONE OF THESE IN backend/.env IF YOU WANT NOISE:
#   DEBUG_SUMMARY=1          (GENERAL FLOW LOGS)
#   DEBUG_OG=1               (OG TAG LOGS + CLEANING)
#   DEBUG_HF=1               (HF PROMPT + HF CALL LOGS)
#
# EXAMPLE:
#   DEBUG_OG=1
#   DEBUG_SUMMARY=1
# ------------------------------------------------------------

DEBUG_SUMMARY = os.getenv("DEBUG_SUMMARY", "0") == "1"
DEBUG_OG = os.getenv("DEBUG_OG", "0") == "1"
DEBUG_HF = os.getenv("DEBUG_HF", "0") == "1"


def _dbg(msg: str):
    if DEBUG_SUMMARY or DEBUG_OG or DEBUG_HF:
        print(msg)
        sys.stdout.flush()


def _dbg_og(msg: str):
    if DEBUG_OG:
        print(msg)
        sys.stdout.flush()


def _dbg_hf(msg: str):
    if DEBUG_HF:
        print(msg)
        sys.stdout.flush()


def _cap(s: str, n: int = 240) -> str:
    s = (s or "").replace("\n", " ").strip()
    return (s[:n] + "…") if len(s) > n else s


# ------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------

INPUT_CHAR_CAP = 500
SHORT_COPY_LEN = 25

HF_MODEL_ROLL = [
    "google/pegasus-cnn_dailymail",
    "facebook/bart-large-cnn",
]

PIPELINE_BASE = "https://api-inference.huggingface.co/pipeline/text2text-generation"
MODELS_BASE = "https://api-inference.huggingface.co/models"

DEFAULT_HEADERS = {
    # SOME SITES (INCLUDING META PROPERTIES) BEHAVE BETTER WITH A UA.
    "User-Agent": "Tweet-Sized-Takeaways/1.0 (+local dev)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ------------------------------------------------------------
# REGEX (COMPILED ONCE)
# ------------------------------------------------------------
# TARGETS IG OG:DESCRIPTION PREFIX LIKE:
#   "schimpfstagram on December 11, 2025: "
# ALSO HANDLES:
#   "username on Dec 11, 2025:"
#   "username on September 1, 2025"
# ------------------------------------------------------------

IG_PREFIX_RE = re.compile(
    r"^\s*[A-Za-z0-9_.]+\s+on\s+"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|"
    r"January|February|March|April|May|June|July|August|September|"
    r"October|November|December)"
    r"\s+\d{1,2},?\s+\d{4}:?\s*",
    re.IGNORECASE,
)

IG_STATS_PREFIX_RE = re.compile(
    r"^\s*(?:[\d,.]+(?:\.\d+)?[KMB]?\s+likes?,\s*)?"
    r"[\d,.]+(?:\.\d+)?[KMB]?\s+comments?\s*[-–—]\s*",
    re.IGNORECASE,
)

LIKED_BY_RE = re.compile(r"Liked by .*?(?: and \d+ others)?", re.IGNORECASE)
LIKES_COUNT_RE = re.compile(r"\b\d[\d,]*\s+likes\b", re.IGNORECASE)
TIME_AGO_RE = re.compile(r"\b\d{1,2}[smhdw]\s+ago\b", re.IGNORECASE)
DATE_RE = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]* "
    r"\d{1,2},?\s+\d{4}\b",
    re.IGNORECASE,
)

MENTION_RE = re.compile(r"@[\w.]+")
HASHTAG_RE = re.compile(r"#[\w.]+")
WHITESPACE_RE = re.compile(r"\s+")


# ------------------------------------------------------------
# TEXT CLEANING
# ------------------------------------------------------------

TRAILING_ELLIPSIS_RE = re.compile(r"(?:\s*(?:\.{3,}|…)+\s*)+$")
TRAILING_PUNCT_RE = re.compile(r"\s+[^\w\s]+$")


def end_on_solid_word(text: str) -> str:
    if not text:
        return ""

    text = TRAILING_ELLIPSIS_RE.sub("", text).strip()
    text = TRAILING_PUNCT_RE.sub("", text).strip()

    return text


def clean_social_caption(text: str) -> str:
    if not text:
        return ""

    raw = text

    text = IG_STATS_PREFIX_RE.sub("", text, count=1)

    m = IG_PREFIX_RE.match(text)
    if m:
        _dbg_og(f"🧼 IG_PREFIX_RE MATCH -> '{_cap(m.group(0), 120)}'")
        text = IG_PREFIX_RE.sub("", text, count=1)
    else:
        _dbg_og("🧼 IG_PREFIX_RE NO MATCH")

    text = MENTION_RE.sub("", text)
    text = HASHTAG_RE.sub("", text)
    text = LIKED_BY_RE.sub("", text)
    text = LIKES_COUNT_RE.sub("", text)
    text = TIME_AGO_RE.sub("", text)
    text = DATE_RE.sub("", text)

    text = WHITESPACE_RE.sub(" ", text).strip()

    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1].strip()

    text = end_on_solid_word(text)

    if DEBUG_OG:
        _dbg_og(f"🧼 CLEAN_SOCIAL_CAPTION RAW    -> '{_cap(raw)}'")
        _dbg_og(f"🧼 CLEAN_SOCIAL_CAPTION CLEAN  -> '{_cap(text)}'")

    return text

# ------------------------------------------------------------
# FETCH
# ------------------------------------------------------------


def _normalize_fetch_url(url: str) -> str:
    url = (url or "").strip()
    if url and not re.match(r"^[a-z][a-z0-9+.-]*://", url, re.I):
        return f"https://{url}"
    return url


async def fetch_html(url: str) -> str:
    url = _normalize_fetch_url(url)
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(
        timeout=timeout, headers=DEFAULT_HEADERS
    ) as session:
        try:
            async with session.get(url, allow_redirects=True) as resp:
                _dbg(f"🌐 FETCH {url} -> STATUS {resp.status}")
                if resp.status != 200:
                    body = await resp.text()
                    _dbg(f"🌐 FETCH NON-200 BODY (CAP) -> '{_cap(body)}'")
                    return body or ""
                return await resp.text()
        except Exception as e:
            _dbg(f"🌐 FETCH EXCEPTION -> {e}")
            return ""


# ------------------------------------------------------------
# VALIDATION / HELPERS
# ------------------------------------------------------------


def _valid_content(s: str) -> bool:
    if not s:
        return False

    s_clean = s.strip().strip("\"'.").lower()
    if s_clean in {"instagram", "facebook", "threads", "twitter", "x"}:
        return False

    if _looks_like_threads_chrome(s_clean):
        return False

    if len(s_clean) < 30:
        return False

    return len(re.findall(r"[A-Za-z]{3,}", s)) >= 6


def _looks_like_threads_chrome(text: str) -> bool:
    lower = (text or "").lower()
    nav_hits = sum(
        phrase in lower
        for phrase in (
            "home search",
            "create notifications profile",
            "back thread",
            "like comment repost share",
            "log in or sign up for threads",
            "see what people are talking about",
            "instagram log in with username",
            "threads terms",
        )
    )
    return nav_hits >= 2


def _is_twitter_url(url: str) -> bool:
    url = (url or "").strip()
    parseable = url if re.match(r"^[a-z][a-z0-9+.-]*://", url, re.I) else f"https://{url}"
    host = (urlparse(parseable).netloc or "").lower()
    host = host[4:] if host.startswith("www.") else host
    return (
        host == "x.com"
        or host.endswith(".x.com")
        or host == "twitter.com"
        or host.endswith(".twitter.com")
    )


def _cap_to(text: str, n: int) -> str:
    if len(text) <= n:
        return text
    cut = text[:n]
    m = re.match(r"(?s)(.*?[.!?])\s", cut)
    return m.group(1).strip() if m else cut.strip()


def _get_hf_token() -> str:
    # YOUR IOS NOTE USES HF_ACCESS_TOKEN, SO SUPPORT THAT FIRST.
    # (KEEP HF_API_TOKEN AS FALLBACK SO OLD ENV FILES STILL WORK.)
    return (os.getenv("HF_ACCESS_TOKEN") or os.getenv("HF_API_TOKEN") or "").strip()


# ------------------------------------------------------------
# HF (ONLY WHEN CALLED)
# ------------------------------------------------------------


async def get_best_summary(meta_text: str, default_weird_msg: str | None = None) -> str:
    meta_text = (meta_text or "").strip()

    if not meta_text:
        msg = default_weird_msg or next_weirdlink_pair()[1]
        _dbg_hf(f"🌀 HF CALLED WITH EMPTY META -> RETURNING WEIRD MSG: '{_cap(msg)}'")
        return msg

    if len(meta_text) <= SHORT_COPY_LEN:
        _dbg_hf(f"🧾 HF PASSTHROUGH SHORT ({len(meta_text)} CHARS)")
        return meta_text

    capped = _cap_to(meta_text, INPUT_CHAR_CAP)
    prompt = build_pegasus_prompt(capped)

    _dbg_hf("📝 HF PROMPT (CAP) -> " + _cap(prompt, 500))

    token = _get_hf_token()
    if not token:
        msg = default_weird_msg or next_weirdlink_pair()[1]
        _dbg_hf("⚠️  HF TOKEN MISSING (HF_ACCESS_TOKEN / HF_API_TOKEN) -> FALLBACK")
        return msg

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload = {
        "inputs": prompt,
        "parameters": {
            "do_sample": False,
            "num_beams": 5,
            "max_new_tokens": 60,
            "no_repeat_ngram_size": 3,
            "early_stopping": True,
        },
        "options": {"wait_for_model": True},
    }

    timeout = aiohttp.ClientTimeout(total=25)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for model in HF_MODEL_ROLL:
            for base in (PIPELINE_BASE, MODELS_BASE):
                url = f"{base}/{model}"
                try:
                    _dbg_hf(f"🤖 HF POST -> {url}")
                    async with session.post(url, headers=headers, json=payload) as r:
                        if r.status != 200:
                            body = await r.text()
                            _dbg_hf(f"⚠️  HF {r.status} (CAP) -> '{_cap(body)}'")
                            continue

                        data = await r.json()
                        if (
                            not isinstance(data, list)
                            or not data
                            or not isinstance(data[0], dict)
                        ):
                            _dbg_hf(f"⚠️  HF UNEXPECTED JSON SHAPE -> {type(data)}")
                            continue

                        text = data[0].get("summary_text") or data[0].get(
                            "generated_text"
                        )
                        if text:
                            out = trim_to_280(
                                enforce_source_vocab(text.strip(), capped)
                            )
                            _dbg_hf(
                                f"✅ HF SUCCESS ({len(out)} CHARS) -> '{_cap(out)}'"
                            )
                            return out
                except Exception as e:
                    _dbg_hf(f"⚠️  HF EXCEPTION -> {e}")
                    continue

    msg = default_weird_msg or next_weirdlink_pair()[1]
    _dbg_hf(f"🧸 HF FAILED ENTIRELY -> FALLBACK: '{_cap(msg)}'")
    return msg


# ------------------------------------------------------------
# HTML SANITIZATION (LAST RESORT TEXT SOURCE)
# ------------------------------------------------------------


def sanitize_html_for_summary(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")

    for tag in soup(
        ["script", "style", "nav", "header", "footer", "aside", "noscript"]
    ):
        tag.decompose()

    text = soup.get_text(" ", strip=True)
    text = WHITESPACE_RE.sub(" ", text).strip()
    cleaned = clean_social_caption(text)

    _dbg_og(f"🧹 SANITIZE_HTML TEXT (CAP) -> '{_cap(text)}'")
    _dbg_og(f"🧹 SANITIZE_HTML CLEAN (CAP) -> '{_cap(cleaned)}'")

    return cleaned


# ------------------------------------------------------------
# SOCIAL EXTRACTION (OG FIRST, ALWAYS CLEANED)
# NOTE: THIS FUNCTION IS USED TO PRODUCE THE INPUT TEXT (OG DESC/TITLE)
# BEFORE HF IS EVER INVOLVED.
# ------------------------------------------------------------


def extract_social_content_for_hf(html: str, url: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    url_l = (url or "").lower()

    _dbg_og(f"🔎 EXTRACT_SOCIAL_CONTENT URL -> {url}")

    def cleaned(val: str) -> str:
        return clean_social_caption((val or "").strip())

    # INSTAGRAM
    if "instagram.com" in url_l:
        for prop in ("og:description", "og:title"):
            tag = soup.find("meta", property=prop)
            if tag and tag.get("content"):
                raw = tag["content"]
                text = cleaned(raw)
                _dbg_og(f"📌 IG {prop.upper()} RAW   -> '{_cap(raw)}'")
                _dbg_og(f"📌 IG {prop.upper()} CLEAN -> '{_cap(text)}'")

                if _valid_content(text) or len(text) <= SHORT_COPY_LEN:
                    _dbg_og(f"✅ PICKED {prop} ({len(text)} CHARS)")
                    return text
                else:
                    _dbg_og(f"⛔ REJECTED {prop} (NOT VALID)")

        # JSON-LD (RARELY PRESENT FOR IG NOW, BUT KEEP IT)
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(s.string or "")
                if isinstance(data, list) and data:
                    data = data[0]
                if not isinstance(data, dict):
                    continue

                for k in ("caption", "description", "articleBody", "headline"):
                    if isinstance(data.get(k), str):
                        raw = data[k]
                        text = cleaned(raw)
                        _dbg_og(f"📌 IG JSON-LD {k.upper()} RAW   -> '{_cap(raw)}'")
                        _dbg_og(f"📌 IG JSON-LD {k.upper()} CLEAN -> '{_cap(text)}'")

                        if _valid_content(text) or len(text) <= SHORT_COPY_LEN:
                            _dbg_og(f"✅ PICKED JSON-LD {k} ({len(text)} CHARS)")
                            return text
                        else:
                            _dbg_og(f"⛔ REJECTED JSON-LD {k} (NOT VALID)")
            except Exception as e:
                _dbg_og(f"⚠️  JSON-LD PARSE ERROR -> {e}")
                pass

    # FACEBOOK / THREADS (AND GENERIC META OG:DESCRIPTION)
    if any(p in url_l for p in ("facebook.com", "threads.net", "threads.com")):
        tag = soup.find("meta", property="og:description")
        if tag and tag.get("content"):
            raw = tag["content"]
            text = cleaned(raw)
            _dbg_og(f"📌 SOCIAL OG:DESCRIPTION RAW   -> '{_cap(raw)}'")
            _dbg_og(f"📌 SOCIAL OG:DESCRIPTION CLEAN -> '{_cap(text)}'")

            if _valid_content(text) or len(text) <= SHORT_COPY_LEN:
                _dbg_og(f"✅ PICKED SOCIAL OG:DESCRIPTION ({len(text)} CHARS)")
                return text
            else:
                _dbg_og("⛔ REJECTED SOCIAL OG:DESCRIPTION (NOT VALID)")

    # FALLBACK: SANITIZED PAGE TEXT (LAST RESORT)
    _dbg_og("🧹 FALLING BACK TO SANITIZED HTML TEXT")
    sanitized = sanitize_html_for_summary(html)
    if _valid_content(sanitized):
        _dbg_og(f"✅ PICKED SANITIZED HTML ({len(sanitized)} CHARS)")
        return sanitized

    _dbg_og("⛔ NO VALID TEXT FOUND -> RETURNING EMPTY STRING")
    return ""


# ------------------------------------------------------------
# IMAGE EXTRACTION
# ------------------------------------------------------------


def extract_og_image(html: str, url: str) -> tuple[str, str | None]:
    _dbg_og(f"🖼️  EXTRACT_OG_IMAGE URL -> {url}")

    if _is_twitter_url(url):
        img, msg = next_twitter_fallback()
        _dbg_og(f"🖼️  TWITTER FALLBACK IMAGE -> '{_cap(img)}'")
        _dbg_og(f"🖼️  TWITTER FALLBACK MSG -> '{_cap(msg)}'")
        return img, msg

    try:
        from .extract import extract_og_tags

        img, title = extract_og_tags(html, url)
        _dbg_og(f"🖼️  extract_og_tags IMG (CAP) -> '{_cap(img)}'")
        _dbg_og(f"🖼️  extract_og_tags TITLE (CAP) -> '{_cap(title)}'")
        if img:
            return img, None
    except Exception as e:
        _dbg_og(f"⚠️  extract_og_tags ERROR -> {e}")
        pass

    if "threads" in (url or "").lower():
        img = next_threads_fallback()
        _dbg_og(f"🖼️  THREADS FALLBACK IMAGE -> '{_cap(img)}'")
        return img, None

    img, msg = next_weirdlink_pair()
    _dbg_og(f"🖼️  WEIRDLINK FALLBACK IMAGE -> '{_cap(img)}'")
    _dbg_og(f"🖼️  WEIRDLINK FALLBACK MSG (CAP) -> '{_cap(msg)}'")
    return img, msg
