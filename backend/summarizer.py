# ✅ SUMMARIZER.PY (REVISED TO BLOCK CNN.COM HF HALLUCINATION, PREFER RAW CAPTIONS, TRIM FOR HF)

import os
import re
import aiohttp
import sys
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

HF_API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"

# HALLUCINATION BLOCKLIST
BLOCKED_SUMMARIES = {
    "CNN.com will feature iReporter photos in a weekly Travel Snapshots gallery. Please submit your best shots of the U.S. for next week. Visit CNN.com/Travel next Wednesday for a new gallery of snapshots. Click here for more travel photos."
}

# LOG EXACTLY WHAT HF SEES
def log_hf_prompt(prompt: str):
    print("\n📝 HF RAW PROMPT >>>")
    print(prompt)
    print("<<< END PROMPT\n")
    sys.stdout.flush()

# CLEAN META/FB/IG/THREADS CAPTIONS
def clean_social_caption(text: str) -> str:
    text = re.sub(r'@[\w.]+', '', text)
    text = re.sub(r'#[\w.]+', '', text)
    text = re.sub(r'Liked by .*', '', text)
    text = re.sub(r'\d+\s+likes', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b\d{1,2}[smhdw] ago\b', '', text)
    text = re.sub(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# FETCH RAW HTML
async def fetch_html(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()

# GET BART SUMMARY
async def get_best_summary(text: str) -> str:
    if not text.strip():
        return "🚫 There's honestly nothing to summarize on that link. 🚫"

    prompt = text.strip()[:1024]
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
                if isinstance(result, list) and result and "summary_text" in result[0]:
                    summary = result[0]["summary_text"].strip()
                    if summary in BLOCKED_SUMMARIES:
                        print("🚫 BLOCKED HALLUCINATED SUMMARY (CNN.com travel blurb)")
                        return ""  # force fallback
                    return summary
                return "🤖 Hugging Face response malformed."
            return f"🛑 Hugging Face error {resp.status}: {await resp.text()}"

# EXTRACT OG IMAGE
def extract_og_image(html: str) -> str:
    from .extract import extract_og_tags
    image, _ = extract_og_tags(html)
    return image

# REMOVE JUNK FOR FALLBACK SUMMARY
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
