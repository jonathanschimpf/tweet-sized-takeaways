import os
import re
import aiohttp
import sys
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# ✅ IMPORT BLOCKLIST TERMS (CASE-INSENSITIVE PARTIAL MATCHES)
from .barts_hallucination_blocklist import BLOCKED_SUMMARIES

load_dotenv()

HF_API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"

# ✅ LOG EXACTLY WHAT HF SEES
def log_hf_prompt(prompt: str):
    print("\n📝 HF RAW PROMPT >>>")
    print(prompt)
    print("<<< END PROMPT\n")
    sys.stdout.flush()

# ✅ CLEAN META/FB/IG/THREADS CAPTIONS
def clean_social_caption(text: str) -> str:
    text = re.sub(r'@[\w.]+', '', text)
    text = re.sub(r'#[\w.]+', '', text)
    text = re.sub(r'Liked by .*', '', text)
    text = re.sub(r'\d+\s+likes', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b\d{1,2}[smhdw] ago\b', '', text)
    text = re.sub(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ✅ FETCH RAW HTML
async def fetch_html(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

# ✅ GET BART SUMMARY — STRIPS PARTIAL HALLUCINATIONS BUT PRESERVES GOOD CONTENT
async def get_best_summary(text: str) -> str:
    if not text.strip():
        return "🚫 There's honestly nothing to summarize on that link. 🚫"

    full_prompt = text.strip()[:1024]
    log_hf_prompt(full_prompt)

    headers = {
        "Authorization": f"Bearer {os.getenv('HF_API_TOKEN')}",
        "Content-Type": "application/json",
    }
    payload = {"inputs": full_prompt}

    async with aiohttp.ClientSession() as session:
        async with session.post(HF_API_URL, headers=headers, json=payload) as resp:
            if resp.status == 200:
                result = await resp.json()
                if isinstance(result, list) and result and "summary_text" in result[0]:
                    summary = result[0]["summary_text"].strip()
                    print("🧠 HF RETURNED >>>", summary)

                    removed_fragments = []

                    for blocked in BLOCKED_SUMMARIES:
                        pattern = re.compile(re.escape(blocked), flags=re.IGNORECASE)
                        if re.search(pattern, summary):
                            summary = pattern.sub("", summary)
                            removed_fragments.append(blocked)

                    if removed_fragments:
                        print(f"🚫 REMOVED HALLUCINATED FRAGMENTS >>> {removed_fragments}")
                        summary = re.sub(r"\s{2,}", " ", summary).strip()

                    return summary

                return "🤖 Hugging Face response malformed."
            return f"🛑 Hugging Face error {resp.status}: {await resp.text()}"

# ✅ EXTRACT OG IMAGE
def extract_og_image(html: str) -> str:
    from .extract import extract_og_tags
    image, _ = extract_og_tags(html)
    return image

# ✅ REMOVE JUNK FOR FALLBACK SUMMARY
def sanitize_html_for_summary(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "aside"]):
        tag.decompose()

    for attr in ["id", "class"]:
        for bad in ["skip", "accessibility", "nav", "menu", "footer", "header"]:
            for el in soup.find_all(attrs={attr: re.compile(bad, re.I)}):
                el.decompose()

    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(
        r"(Navigation Menu|Skip to main content|Keyboard shortcuts|Accessibility links).*",
        "",
        text,
        flags=re.I,
    )

    return text.strip()

# ✅ NEW: ENHANCED SOCIAL CONTENT EXTRACTOR FOR HF
def extract_social_content_for_hf(html: str, url: str) -> str:
    """
    Enhanced content extraction for social platforms:
    Prioritize og:description, then fallback to sanitized HTML.
    """
    soup = BeautifulSoup(html, "html.parser")

    # 📸 Instagram
    if "instagram.com" in url.lower():
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

    # 🧵 Facebook & Threads
    elif any(platform in url.lower() for platform in ["facebook.com", "threads.net"]):
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            content = og_desc["content"].strip()
            if len(content) > 30:
                print(f"📱 Using social og:description: {content[:100]}...")
                return content

    # 🧹 Final fallback
    print("🧹 Using sanitized HTML content")
    return sanitize_html_for_summary(html)
