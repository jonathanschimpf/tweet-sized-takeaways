# THIS IS A GREAT STOPPING POINT FOR THE LOGIC
# IN ALL CAPS: MAIN FASTAPI BACKEND ENTRYPOINT

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

import os
from pathlib import Path
from urllib.parse import urlparse

# LOAD .env VARIABLES
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
print(f"🔐 Hugging Face token loaded? {'Yes' if HF_API_TOKEN else 'No'}")
print("✅ .env path:", os.path.abspath(".env"))

# INTERNAL MODULES
from .summarizer import (
    fetch_html,
    extract_og_image,
    get_best_summary,
    sanitize_html_for_summary,
)
from .extract import (
    extract_og_tags,
    extract_paragraph_like_block,
)
from .blacklist import get_blacklist_category, is_cookie_gated
from .fallbacks import get_fallback_og
from .screenshot import take_screenshot
from .ocr_fallback import (
    extract_text_from_image,
    clean_extracted_text,
    summarize_with_bart,
    remove_hallucinated_brands,
)


# INITIALIZE FastAPI
app = FastAPI()

# CORS CONFIG
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tweet-sized-takeaways.netlify.app",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# STATIC FILES (FOR SCREENSHOTS + PUBLIC ASSETS)
public_path = os.path.join(os.path.dirname(__file__), "..", "public")
app.mount("/static", StaticFiles(directory=public_path), name="static")


# HEALTH CHECK
@app.api_route("/", methods=["GET", "HEAD"])
def read_root():
    return {"message": "Backend is live"}


# Pydantic MODEL
class URLInput(BaseModel):
    url: str


# 280 CHAR TRIMMER
def trim_to_280(text: str) -> str:
    return text.strip()[:277] + "..." if len(text.strip()) > 280 else text.strip()


# CUSTOM SOCIAL MEDIA CHECK
def is_social_platform(url: str) -> bool:
    hostname = urlparse(url).hostname or ""
    return any(social in hostname for social in ["facebook.com", "threads.net"])


# MAIN SUMMARIZATION ENDPOINT
@app.post("/summarize")
async def summarize(input: URLInput):
    print(f"🔵 URL received: {input.url}")

    try:
        html = await fetch_html(input.url)
        print("🟢 HTML fetched successfully")

        # TRY OG TAGS
        og_image, og_desc = extract_og_tags(html)
        if og_desc and len(og_desc.strip()) >= 30:
            print("🟠 Using og:description")
            return {
                "summary": trim_to_280(og_desc),
                "used_huggingface": False,
                "og_image": og_image or get_social_fallback(input.url),
            }

        # TRY NATIVE TEXT SCRAPE
        native = extract_paragraph_like_block(html)
        print(f"🟡 Native text extracted: {native[:300]}")
        if len(native.strip()) >= 100:
            print("🟠 Using native scrape")
            return {
                "summary": trim_to_280(native),
                "used_huggingface": False,
                "og_image": og_image or get_social_fallback(input.url),
            }

        # TRY HUGGING FACE
        print("🔁 Falling back to Hugging Face")
        summary = await get_best_summary(native)
        if summary and len(summary.strip()) >= 30:
            return {
                "summary": trim_to_280(summary),
                "used_huggingface": True,
                "og_image": og_image or get_social_fallback(input.url),
            }

        # FINAL FALLBACK – SCREENSHOT → OCR → BART or image caption
        print("🧠 Final fallback: screenshot → OCR → BART or image caption")
        screenshot_path = await take_screenshot(input.url)
        screenshot_full_path = os.path.join(
            public_path, "screenshots", screenshot_path.name
        )

        ocr_text = extract_text_from_image(screenshot_full_path)
        ocr_clean = clean_extracted_text(ocr_text)

        if len(ocr_clean.split()) >= 10:
            print("🔤 OCR succeeded, trying BART summarization")
            bart_summary = summarize_with_bart(ocr_clean)
            final_output = remove_hallucinated_brands(bart_summary)

            if len(final_output.strip()) >= 30:
                return {
                    "summary": trim_to_280(final_output),
                    "used_huggingface": False,
                    "og_image": f"/static/screenshots/{screenshot_path.name}",
                }

        # FALLBACK TO IMAGE CAPTIONING
        print("🖼️ OCR too weak — using vision model for caption")
        caption = caption_image(screenshot_full_path)

        return {
            "summary": trim_to_280(caption),
            "used_huggingface": False,
            "og_image": f"/static/screenshots/{screenshot_path.name}",
        }

    except Exception as e:
        print(f"🔥 ERROR in /summarize: {e}")
        return {
            "summary": "❌ An error occurred while summarizing the page.",
            "used_huggingface": False,
            "og_image": get_social_fallback(input.url),
        }


# MANUAL HUGGING FACE FORCED ROUTE
@app.post("/summarize/hf")
async def summarize_with_hf(input: URLInput):
    print(f"🤖 FORCED HF: {input.url}")

    try:
        html = await fetch_html(input.url)
        text = sanitize_html_for_summary(html)

        if len(text.strip()) < 100:
            return {
                "summary": "🧨 Hugging Face couldn't read that to work out a summary for you. Refer to the initial take.",
                "used_huggingface": False,
                "og_image": extract_og_image(html) or get_social_fallback(input.url),
            }

        summary = await get_best_summary(text)
        return {
            "summary": trim_to_280(summary),
            "used_huggingface": True,
            "og_image": extract_og_image(html) or get_social_fallback(input.url),
        }

    except Exception as e:
        print(f"💥 FORCED HF ERROR: {e}")
        return {
            "summary": "🧨 Hugging Face couldn't read this article right now.",
            "used_huggingface": False,
            "og_image": get_social_fallback(input.url),
        }


# SOCIAL FALLBACK IMAGE RESOLVER
from urllib.parse import urlparse
import os

# GET BASE URL FOR STATIC LINKS
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# SOCIAL FALLBACK IMAGE RESOLVER
from urllib.parse import urlparse
import os

# GET BASE URL FOR STATIC LINKS
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# SOCIAL FALLBACK IMAGE RESOLVER
def get_social_fallback(url: str) -> str:
    hostname = urlparse(url).hostname or ""
    
    if "threads.net" in hostname or "threads.com" in hostname:
        return f"{BASE_URL}/static/images/og-fallbacks/threads-og-image-fallback.jpg"
    
    if "facebook.com" in hostname:
        return f"{BASE_URL}/static/images/og-fallbacks/social.jpg"
    
    return f"{BASE_URL}{get_fallback_og('weird')}"


