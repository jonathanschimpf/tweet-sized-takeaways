# ✅ MAIN FASTAPI BACKEND ENTRYPOINT — PEGASUS-ONLY VERSION

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

import os
from pathlib import Path
from urllib.parse import urlparse

# ✅ INIT FastAPI
app = FastAPI()

# ✅ MOUNT PUBLIC IMAGE ASSETS
app.mount(
    "/images", StaticFiles(directory=os.path.join("public", "images")), name="images"
)

# ✅ LOAD .env
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
print(f"🔐 Hugging Face token loaded? {'Yes' if HF_API_TOKEN else 'No'}")
print("✅ .env path:", os.path.abspath(".env"))

# ✅ INTERNAL MODULES
from .summarizer import (
    fetch_html,
    extract_og_image,
    get_best_summary,
    sanitize_html_for_summary,
    extract_social_content_for_hf,
)

from .extract import (
    extract_og_tags,
    extract_paragraph_like_block,
)

from .blacklist import get_blacklist_category, is_cookie_gated

from .fallbacks import get_fallback_og
from .summarizer import get_ordered_threads_fallback  # ✅ BRINGS IN ORDERED LOOP


# from .screenshot import take_screenshot — NEVER WAS USED LOL


# ✅ CORS CONFIG
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

# ✅ STATIC FILES FOR PUBLIC ASSETS
public_path = os.path.join(os.path.dirname(__file__), "..", "public")
app.mount("/static", StaticFiles(directory=public_path), name="static")


# ✅ HEALTH CHECK
@app.api_route("/", methods=["GET", "HEAD"])
def read_root():
    return {"message": "Backend is live"}


# ✅ INPUT MODEL
class URLInput(BaseModel):
    url: str


# ✅ TWEET TRIMMER
def trim_to_280(text: str) -> str:
    return text.strip()[:277] + "..." if len(text.strip()) > 280 else text.strip()


# ✅ FALLBACK IMAGE HANDLER
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def get_social_fallback(url: str) -> str:
    hostname = urlparse(url).hostname or ""

    if "threads.net" in hostname or "threads.com" in hostname:
        return f"{BASE_URL}{get_ordered_threads_fallback()}"  # ✅ use the cycler

    if "facebook.com" in hostname:
        return f"{BASE_URL}/images/og-fallbacks/social.jpg"

    return f"{BASE_URL}{get_fallback_og('weird')}"


# ✅ MAIN SUMMARIZATION ROUTE
@app.post("/summarize")
async def summarize(input: URLInput):
    print(f"🔵 URL received: {input.url}")

    try:
        html = await fetch_html(input.url)
        print("🟢 HTML fetched successfully")
        og_image = extract_og_image(html)  # ✅ ensure this always runs
        og_image, og_desc = extract_og_tags(html)

        og_image, og_desc = extract_og_tags(html)
        hostname = urlparse(input.url).hostname or ""
        is_threads = "threads.net" in hostname or "threads.com" in hostname

        # ✅ FORCE THREADS TO USE FALLBACK IMAGE
        if og_desc and len(og_desc.strip()) >= 30:
            print("🟠 Using og:description")
            final_og_image = (
                get_social_fallback(input.url)
                if is_threads
                else og_image or get_social_fallback(input.url)
            )
            return {
                "summary": trim_to_280(og_desc),
                "used_huggingface": False,
                "og_image": final_og_image,
            }

        native = extract_paragraph_like_block(html)
        print(f"🟡 Native text extracted: {native[:300]}")
        if len(native.strip()) >= 100:
            print("🟠 Using native scrape")
            final_og_image = (
                get_social_fallback(input.url)
                if is_threads
                else og_image or get_social_fallback(input.url)
            )
            return {
                "summary": trim_to_280(native),
                "used_huggingface": False,
                "og_image": final_og_image,
            }

        print("🔁 Falling back to Hugging Face T5")
        summary = await get_best_summary(native)
        if summary and len(summary.strip()) >= 30:
            final_og_image = (
                get_social_fallback(input.url)
                if is_threads
                else og_image or get_social_fallback(input.url)
            )
            return {
                "summary": trim_to_280(summary),
                "used_huggingface": True,
                "og_image": final_og_image,
            }

        print("🧸 All fallbacks failed — returning generic message.")
        final_og_image = get_social_fallback(input.url)
        return {
            "summary": "🧸 Hugging Face couldn't find enough readable text.",
            "used_huggingface": False,
            "og_image": final_og_image,
        }

    except Exception as e:
        print(f"🔥 ERROR in /summarize: {e}")
        return {
            "summary": "❌ An error occurred while summarizing the page.",
            "used_huggingface": False,
            "og_image": get_social_fallback(input.url),
        }


# ✅ MANUAL FORCED HF T5/PEGASUS ROUTE
@app.post("/summarize/hf")
async def summarize_with_hf(input: URLInput):
    print(f"🤖 FORCED HF: {input.url}")

    try:
        html = await fetch_html(input.url)
<<<<<<< HEAD
        text = extract_social_content_for_hf(html, input.url)

=======
        prompt = extract_social_content_for_hf(html, input.url)

        # ✨ DEBUG LOG: SHOW PROMPT
        print("\n🧹 Using sanitized HTML content\n")
        print("📝 HF RAW PROMPT >>>")
        print(f"summarize: {prompt}")
        print("<<< END PROMPT\n")

        # 🔁 TRY PEGASUS UP TO 3 TIMES
        max_retries = 3
        summary = None
        attempt = 0

        while attempt < max_retries:
            attempt += 1
            print(f"🔁 Pegasus attempt {attempt}...")
            summary = await get_best_summary(prompt)
            if summary and len(summary.strip()) >= 30:
                break

        print(f"✅ Pegasus returned after {attempt} attempt(s):\n{summary}\n")

        hostname = urlparse(input.url).hostname or ""
        is_threads = "threads.net" in hostname or "threads.com" in hostname
        final_og_image = (
            get_social_fallback(input.url)
            if is_threads
            else extract_og_image(html) or get_social_fallback(input.url)
        )
>>>>>>> 17c7ed5 (Pegasus upgrade — Bye BART — you can't come with to the remote '.venv')

        return {
            "summary": trim_to_280(summary),
            "used_huggingface": True,
            "og_image": final_og_image,
        }

    except Exception as e:
        print(f"💥 FORCED HF ERROR: {e}")
        return {
            "summary": "🧸 Hugging Face couldn't read this article right now.",
            "used_huggingface": False,
            "og_image": get_social_fallback(input.url),
        }
