import os
import re
import sys
import json
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dotenv import load_dotenv
from itertools import cycle

# ---- PEGASUS PROMPT HELPERS ----
from .pegasusprompt import (
    build_pegasus_prompt,
    enforce_source_vocab,
    trim_to_280,
)

# ---- ENV / DEBUG ----
load_dotenv()
DEBUG_HF = os.getenv("DEBUG_HF", "0") == "1"

# ---- LIMITS ----
INPUT_CHAR_CAP = 500  # hard cap for text we send into the prompt

# ---- HF MODEL ROLL (your requested order) ----
HF_MODEL_ROLL = [
    "google/pegasus-cnn_dailymail",  # short, safer summarizer
    "facebook/bart-large-cnn",  # deterministic-ish when input is short
]
PIPELINE_BASE = "https://api-inference.huggingface.co/pipeline/text2text-generation"
MODELS_BASE = "https://api-inference.huggingface.co/models"

# ---- THREADS FALLBACK IMAGE CYCLER ----
THREADS_OG_DIR = "public/images/og-fallbacks/threads"
_threads_fallback_cycle = None


def get_ordered_threads_fallback() -> str:
    """Return next numbered Threads fallback image path (relative to /images)."""
    global _threads_fallback_cycle
    if _threads_fallback_cycle is None:
        files = sorted(
            f
            for f in os.listdir(THREADS_OG_DIR)
            if f.lower().endswith((".jpg", ".png")) and f[0].isdigit()
        )
        if not files:
            return "/images/og-fallbacks/weirdlink.jpg"
        _threads_fallback_cycle = cycle(files)
    return f"/images/og-fallbacks/threads/{next(_threads_fallback_cycle)}"


def get_social_fallback(url: str) -> str:
    hostname = urlparse(url).hostname or ""
    if "threads.net" in hostname or "threads.com" in hostname:
        return get_ordered_threads_fallback()
    return f"{os.getenv('BASE_URL')}/images/og-fallbacks/weirdlink.jpg"


# ---- DEBUG PROMPT LOGGER ----
def log_hf_prompt(prompt: str):
    print("\n📝 HF RAW PROMPT >>>")
    print(prompt)
    print("<<< END PROMPT\n")
    sys.stdout.flush()


# ---- SCRUB SOCIAL CAPTIONS (handy utility) ----
def clean_social_caption(text: str) -> str:
    text = re.sub(r"@[\w.]+", "", text)
    text = re.sub(r"#[\w.]+", "", text)
    text = re.sub(r"Liked by .*", "", text)
    text = re.sub(r"\d+\s+likes", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d{1,2}[smhdw] ago\b", "", text)
    text = re.sub(
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b",
        "",
        text,
    )
    return re.sub(r"\s+", " ", text).strip()


# ---- FETCH HTML (used by main.py) ----
async def fetch_html(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()


# ---- OOV DEBUGGER ----
def _oov_tokens(candidate: str, source: str):
    src_vocab = set(
        t.lower() for t in re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?", source or "")
    )
    cand = re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?", candidate or "")
    return [t for t in cand if t.lower() not in src_vocab]


def _cap_to(text: str, n: int) -> str:
    if len(text) <= n:
        return text
    cut = text[:n]
    # try to cut at sentence/word boundary
    for sep in [r"(?s)(.*?[.!?])\s", r"(.*)\s"]:
        m = re.match(sep, cut)
        if m and m.group(1):
            return m.group(1).strip()
    return cut.strip()


def _valid_content(s: str) -> bool:
    if not s:
        return False
    s_clean = s.strip().strip("\"'.").lower()
    if s_clean in {"instagram", "facebook", "threads", "twitter", "x"}:
        return False
    if len(s_clean) < 30:
        return False
    wordlike = re.findall(r"[A-Za-z]{3,}", s)
    return len(wordlike) >= 6


# ---- PEGASUS CALL (meta -> prompt -> HF -> clamp -> trim) ----
async def get_best_summary(meta_text: str) -> str:
    meta_text = (meta_text or "").strip()
    if not meta_text:
        return "🚫 There's honestly nothing to summarize on that link. 🚫"

    # HARD CAP the input that goes into the prompt
    capped_meta = _cap_to(meta_text, INPUT_CHAR_CAP)

    prompt = build_pegasus_prompt(capped_meta)
    log_hf_prompt(prompt)

    headers = {
        "Authorization": f"Bearer {os.getenv('HF_API_TOKEN')}",
        "Content-Type": "application/json",
    }
    gen_params = {
        "do_sample": False,
        "num_beams": 5,
        "early_stopping": True,
        "max_new_tokens": 60,
        "no_repeat_ngram_size": 3,
        "length_penalty": 1.0,
    }

    async with aiohttp.ClientSession() as session:
        for model in HF_MODEL_ROLL:
            payload = {
                "inputs": prompt,
                "parameters": gen_params,
                "options": {"wait_for_model": True},
            }

            # 1) Try the pipeline endpoint
            url = f"{PIPELINE_BASE}/{model}"
            try:
                async with session.post(url, headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        text = None
                        if (
                            isinstance(data, list)
                            and data
                            and isinstance(data[0], dict)
                        ):
                            text = data[0].get("generated_text") or data[0].get(
                                "summary_text"
                            )
                        if text:
                            raw = text.strip()
                            clamped = enforce_source_vocab(raw, capped_meta)
                            if DEBUG_HF:
                                removed = _oov_tokens(raw, capped_meta)
                                if removed:
                                    print(
                                        f"🧹 OOV removed ({len(removed)}): {removed[:20]}"
                                    )
                            return trim_to_280(clamped)
                    elif resp.status == 404:
                        print(f"⚠️  HF {model} (pipeline) -> 404 Not Found")
                    else:
                        body = await resp.text()
                        print(f"⚠️  HF {model} (pipeline) -> {resp.status}: {body}")
            except Exception as e:
                print(f"⚠️  HF {model} (pipeline) exception: {e}")

            # 2) Fallback to legacy /models endpoint
            url = f"{MODELS_BASE}/{model}"
            try:
                async with session.post(url, headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        text = None
                        if (
                            isinstance(data, list)
                            and data
                            and isinstance(data[0], dict)
                        ):
                            text = data[0].get("generated_text") or data[0].get(
                                "summary_text"
                            )
                        if text:
                            raw = text.strip()
                            clamped = enforce_source_vocab(raw, capped_meta)
                            if DEBUG_HF:
                                removed = _oov_tokens(raw, capped_meta)
                                if removed:
                                    print(
                                        f"🧹 OOV removed ({len(removed)}): {removed[:20]}"
                                    )
                            return trim_to_280(clamped)
                    elif resp.status == 404:
                        print(f"⚠️  HF {model} -> 404 Not Found")
                    else:
                        body = await resp.text()
                        print(f"⚠️  HF {model} -> {resp.status}: {body}")
            except Exception as e:
                print(f"⚠️  HF {model} exception: {e}")

    return "🧸 Hugging Face couldn't read this article right now."


# ---- OG IMAGE EXTRACTOR ----
def extract_og_image(html: str) -> str:
    from .extract import extract_og_tags

    image, _ = extract_og_tags(html)
    return image


# ---- SANITIZER ----
def sanitize_html_for_summary(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(
        ["script", "style", "nav", "header", "footer", "noscript", "aside"]
    ):
        tag.decompose()
    for attr in ["id", "class"]:
        for bad in ["skip", "accessibility", "nav", "menu", "footer", "header"]:
            for el in soup.find_all(attrs={attr: re.compile(bad, re.I)}):
                el.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(
        r"(Navigation Menu|Skip to main content|Keyboard shortcuts|Accessibility links).*$",
        "",
        text,
        flags=re.I,
    )
    return text.strip()


# ---- SOCIAL-FIRST META/OG DESC PICKER ----
def extract_social_content_for_hf(html: str, url: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    url_lower = url.lower()

    # Instagram: prefer og:description, then og:title, then JSON-LD caption
    if "instagram.com" in url_lower:
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            content = clean_social_caption(og_desc["content"].strip())
            if _valid_content(content) and content.lower() != "instagram":
                print(f"📱 Using Instagram og:description: {content[:100]}...")
                return content

        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            content = og_title["content"].strip()
            if _valid_content(content) and content.lower() != "instagram":
                print(f"📱 Using Instagram og:title: {content[:100]}...")
                return content

        # JSON-LD fallback (some IG pages embed caption here)
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(s.string or "")
                if isinstance(data, list) and data:
                    data = data[0]
                if isinstance(data, dict):
                    for key in ("caption", "description", "headline", "articleBody"):
                        val = data.get(key)
                        if isinstance(val, str):
                            val = clean_social_caption(val.strip())
                            if _valid_content(val):
                                print(
                                    f"📱 Using Instagram JSON-LD {key}: {val[:100]}..."
                                )
                                return val
            except Exception:
                pass

    # Facebook / Threads: og:description usually good
    elif any(p in url_lower for p in ["facebook.com", "threads.net", "threads.com"]):
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            content = clean_social_caption(og_desc["content"].strip())
            if _valid_content(content):
                print(f"📱 Using social og:description: {content[:100]}...")
                return content

    # Generic fallback: sanitized page text, but only if it’s real content
    print("🧹 Using sanitized HTML content")
    sanitized = sanitize_html_for_summary(html)
    return sanitized if _valid_content(sanitized) else ""
