from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from urllib.parse import urlparse
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from blacklist import get_blacklist_category, is_cookie_gated
from fallbacks import get_fallback_og
from summarizer import extract_text, extract_all_metadata, fetch_html, summarize_text
import os, time, re

# --- APP ---
app = FastAPI()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- STATIC FILES ---
public_path = os.path.join(os.path.dirname(__file__), "..", "public")
print(f"\U0001f4c1 Serving static files from: {public_path}")
app.mount("/static", StaticFiles(directory=public_path), name="static")

# --- ENV VARS ---
load_dotenv()
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
print(f"\U0001f512 Hugging Face Token Present? {bool(HF_API_TOKEN)}")


class URLInput(BaseModel):
    url: str


@app.post("/summarize")
async def summarize_link(input: URLInput):
    url = input.url.strip()
    if not url.startswith("http"):
        url = "https://" + url

    print(f"\n📥 Summarizing: {url}")
    domain = urlparse(url).netloc
    blacklist_category = get_blacklist_category(domain)

    if is_cookie_gated(domain):
        return {
            "summary": "✨ This site is gatekeeping content behind cookies/sessions. Summarize it yourself. ✨",
            "og_image": get_fallback_og("cookie"),
        }

    if blacklist_category in ["social", "news"]:
        summary = {
            "social": "A summary for a social media post? Seriously? Go use the app. ✌️✨",
            "news": "We can’t summarize this one — blame the paywalls, trackers, or both. 🧱💸",
        }.get(blacklist_category, "")
        return {
            "summary": summary,
            "og_image": get_fallback_og(blacklist_category),
        }

    try:
        html = await fetch_html(url)
    except Exception as e:
        print(f"❌ Fetch error: {e}")
        return {"summary": "🤷‍♂️", "og_image": get_fallback_og("weird")}

    og_image, *_, head_text = extract_all_metadata(html)
    if len(head_text) > 100:
        return {
            "summary": head_text,
            "og_image": og_image or get_fallback_og("weird"),
        }

    body_text = extract_text(html)
    if len(body_text) < 100:
        return {
            "summary": head_text
            or "🌀 No clue. This page might've been built on vibes.",
            "og_image": og_image or get_fallback_og("weird"),
        }

    try:
        summary = await summarize_text(body_text)
        return {
            "summary": summary,
            "og_image": og_image or get_fallback_og("weird"),
            "used_huggingface": True,
        }
    except Exception as e:
        print(f"💥 HF fallback error: {e}")
        return {
            "summary": head_text or "🌀 Something broke. Vibes only.",
            "og_image": og_image or get_fallback_og("weird"),
            "used_huggingface": False,
        }


@app.post("/summarize/hf")
async def summarize_with_hf(input: URLInput):
    url = input.url.strip()
    if not url.startswith("http"):
        url = "https://" + url

    print(f"\n🤗 FORCED HF: {url}")
    try:
        html = await fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")
        main_content = soup.select_one("main") or soup.select_one("article")

        if main_content:
            print("📍 Using <main> or <article>")
            raw_text = main_content.get_text(separator=" ", strip=True)
        else:
            print("📍 Using <p> fallback")
            raw_text = " ".join(
                p.get_text(strip=True)
                for p in soup.find_all("p")
                if len(p.get_text(strip=True).split()) > 5
            )

        text = re.sub(r"\s+", " ", raw_text).strip()
        if len(text) < 100:
            og_image, *_ = extract_all_metadata(html)
            return {
                "summary": "🤷‍♂️ Not enough readable content for AI to skim.",
                "used_huggingface": True,
                "og_image": og_image or get_fallback_og("weird"),
            }

        summary = await summarize_text(text)
        og_image, *_ = extract_all_metadata(html)
        return {
            "summary": summary,
            "used_huggingface": True,
            "og_image": og_image or get_fallback_og("weird"),
        }

    except Exception as e:
        print(f"💥 FORCED HF ERROR: {e}")
        og_image, *_ = extract_all_metadata(html)
        return {
            "summary": "🧨 Hugging Face couldn’t read this article right now.",
            "used_huggingface": False,
            "og_image": og_image or get_fallback_og("weird"),
        }
