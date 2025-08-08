import os
import re
import aiohttp
import sys
import random
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dotenv import load_dotenv
from itertools import cycle

# ✅ ENV LOADING
load_dotenv()

# ✅ HUGGING FACE API (PEGASUS)
HF_API_URL = "https://api-inference.huggingface.co/models/google/pegasus-xsum"

# ✅ → 🧵 THREADS FALLBACK IMAGE SUPPORT 🪡
THREADS_OG_DIR = "public/images/og-fallbacks/threads"
_threads_fallback_cycle = None  # GLOBAL CYCLER


def get_ordered_threads_fallback() -> str:
    global _threads_fallback_cycle

    if _threads_fallback_cycle is None:
        files = sorted(
            [
                f
                for f in os.listdir(THREADS_OG_DIR)
                if f.lower().endswith((".jpg", ".png")) and f[0].isdigit()
            ]
        )
        if not files:
            return "/images/og-fallbacks/weirdlink.jpg"
        _threads_fallback_cycle = cycle(files)

    next_file = next(_threads_fallback_cycle)
    return f"/images/og-fallbacks/threads/{next_file}"


def get_social_fallback(url: str) -> str:
    hostname = urlparse(url).hostname or ""
    if "threads.net" in hostname or "threads.com" in hostname:
        return get_ordered_threads_fallback()
    return f"{os.getenv('BASE_URL')}/images/og-fallbacks/weirdlink.jpg"


# ✅ DEBUG PROMPT LOGGER
def log_hf_prompt(prompt: str):
    print("\n📝 HF RAW PROMPT >>>")
    print(prompt)
    print("<<< END PROMPT\n")
    sys.stdout.flush()


# ✅ CLEAN RAW CAPTIONS
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


# ✅ FETCH HTML
async def fetch_html(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()


# ✅ PEGASUS SUMMARIZER (CLEANED)
async def get_best_summary(text: str) -> str:
    if not text.strip():
        return "🚫 There's honestly nothing to summarize on that link. 🚫"

    prompt = "summarize: " + text.strip()[:1024]
    log_hf_prompt(prompt)

    headers = {
        "Authorization": f"Bearer {os.getenv('HF_API_TOKEN')}",
        "Content-Type": "application/json",
    }
    payload = {"inputs": prompt}

    async with aiohttp.ClientSession() as session:
        async with session.post(HF_API_URL, headers=headers, json=payload) as resp:
            if resp.status == 200:
                result = await resp.json()
                print("🧠 Hugging Face raw response:", result)

                if isinstance(result, list) and result and "summary_text" in result[0]:
                    summary = result[0]["summary_text"].strip()
                    print("🧠 HF RETURNED >>>", summary)

                    return (
                        summary[:277].rstrip() + "..."
                        if len(summary) > 280
                        else summary
                    )
                return "🤖 Hugging Face response malformed."
            return f"🛑 Hugging Face error {resp.status}: {await resp.text()}"


# ✅ OG IMAGE EXTRACTOR
def extract_og_image(html: str) -> str:
    from .extract import extract_og_tags

    image, _ = extract_og_tags(html)
    return image


# ✅ FALLBACK SANITIZER
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


# ✅ SOCIAL-FIRST SCRAPER
def extract_social_content_for_hf(html: str, url: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    url_lower = url.lower()

    if "instagram.com" in url_lower:
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            content = og_desc["content"].strip()
            if len(content) > 30 and content.lower() != "instagram":
                print(f"📱 Using Instagram og:description: {content[:100]}...")
                return content
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title_content = og_title["content"].strip()
            if len(title_content) > 20 and title_content.lower() != "instagram":
                print(f"📱 Using Instagram og:title: {title_content[:100]}...")
                return title_content

    elif any(platform in url_lower for platform in ["facebook.com", "threads.net"]):
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            content = og_desc["content"].strip()
            if len(content) > 30:
                print(f"📱 Using social og:description: {content[:100]}...")
                return content

    print("🧹 Using sanitized HTML content")
    return sanitize_html_for_summary(html)
