from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from urllib.parse import urlparse
from dotenv import load_dotenv
import requests
import os

from summarizer import (
    extract_text,
    extract_og_tags,
    fetch_html,
    summarize_text,
)
from blacklist import get_blacklist_category, is_cookie_gated

# --- LOAD ENV VARS ---
load_dotenv()
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
print(f"🔐 Hugging Face Token Present? {bool(HF_API_TOKEN)}")

# --- FASTAPI INIT ---
app = FastAPI()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- REQUEST MODEL ---
class URLInput(BaseModel):
    url: str

# --- MAIN ROUTE ---
@app.post("/summarize")
def summarize_link(input: URLInput):
    url = input.url.strip()
    print(f"\n📥 Summarizing: {url}")

    # --- PARSE DOMAIN ---
    domain = urlparse(url).netloc
    print(f"🌐 Host: {domain}")
    blacklist_category = get_blacklist_category(domain)

    # --- HANDLE COOKIE WALL ---
    if is_cookie_gated(domain):
        print("🍪 Cookie/session-gated domain — skipping.")
        return {
            "summary": "💥 This site is gatekeeping content behind cookies/sessions. Summarize it yourself. ✨",
            "og_image": "",
        }

    # --- HANDLE SOCIAL/NEWS BLACKLISTS ---
    if blacklist_category in ["social", "news"]:
        try:
            html = fetch_html(url)
            og_image, *_ = extract_og_tags(html)
            print(f"🖼️ og:image (from blacklist): {og_image}")
        except Exception as e:
            print(f"❌ Could not fetch OG image from blacklisted URL: {e}")
            og_image = ""

        if blacklist_category == "social":
            print("🚫 Social media domain — returning snark fallback.")
            return {
                "summary": "A summary for a social media post? Seriously? Go use the app. ✌️✨",
                "og_image": og_image,
            }

        if blacklist_category == "news":
            print("🚫 News media domain — skipping summarization.")
            return {
                "summary": "We can’t summarize this one — blame the paywalls, trackers, or both. 🧱💸",
                "og_image": og_image,
            }

    # --- FETCH HTML ---
    try:
        html = fetch_html(url)
        print(f"✅ HTML fetched (len: {len(html)})")
    except Exception as e:
        print(f"❌ Failed to fetch page: {e}")
        return {"summary": "❌ Could not fetch the provided URL.", "og_image": ""}

    # --- EXTRACT OG + TEXT ---
    og_image, og_title, og_desc = extract_og_tags(html)
    print(f"🧠 og:title: {og_title}")
    print(f"🧠 og:description: {og_desc}")
    print(f"🖼️ og:image: {og_image}")

    text = extract_text(html)
    print(f"📄 Text extract length: {len(text)}")

    # --- FALLBACK TO OG IF TEXT TOO SHORT ---
    if len(text) < 100:
        print("⚠️ Not enough text for summarization. Falling back to OG tags.")
        return {
            "summary": og_desc or og_title or "⚠️ Hugging Face can't seem to summarize this content.",
            "og_image": og_image,
        }

    # --- CALL HF MODEL ---
    try:
        print("🤖 Sending to Hugging Face summarizer...")
        summary_text = summarize_text(text)
        return {"summary": summary_text, "og_image": og_image}
    except Exception as e:
        print(f"💥 HUGGING FACE ERROR: {e}")
        print("🧠 Falling back to og:description or og:title...")
        return {
            "summary": og_desc or og_title or "⚠️ Hugging Face couldn't summarize this page.",
            "og_image": og_image,
        }
