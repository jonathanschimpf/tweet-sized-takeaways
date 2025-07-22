from backend.fastapi import FastAPI
from backend.fastapi.middleware.cors import CORSMiddleware
from backend.fastapi.staticfiles import StaticFiles
from backend.pydantic import BaseModel
from backend.dotenv import load_dotenv

from backend.summarizer import (
    fetch_html,
    extract_og_image,
    get_best_summary,
    sanitize_html_for_summary,
)
from backend.extract import (
    extract_og_tags,
    extract_paragraph_like_block,
)
from backend.blacklist import get_blacklist_category, is_cookie_gated
from backend.fallbacks import get_fallback_og
from backend.screenshot import take_screenshot

import os
from pathlib import Path

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

public_path = os.path.join(os.path.dirname(__file__), "..", "public")
app.mount("/static", StaticFiles(directory=public_path), name="static")

load_dotenv()
HF_API_TOKEN = os.getenv("HF_API_TOKEN")


class URLInput(BaseModel):
    url: str


@app.post("/summarize")
async def summarize(input: URLInput):
    print(f"🔵 URL received: {input.url}")

    try:
        html = await fetch_html(input.url)
        print("🟢 HTML fetched successfully")

        og_image, og_desc = extract_og_tags(html)

        if og_desc and len(og_desc.strip()) >= 30:
            print("🟠 Using og:description")
            return {
                "summary": og_desc.strip(),
                "used_huggingface": False,
                "og_image": og_image,
            }

        native = extract_paragraph_like_block(html)
        print(f"🟡 Native text extracted: {native[:300]}")

        if len(native.strip()) >= 280:
            print("🟠 Using native scrape")
            return {
                "summary": native.strip(),
                "used_huggingface": False,
                "og_image": og_image,
            }

        print("🔁 Falling back to Hugging Face")
        summary = await get_best_summary(native)

        # ✅ Final fallback to Playwright screenshot
        if not og_image:
            print("📸 OG image missing — capturing screenshot")
            screenshot_path = await take_screenshot(input.url)
            og_image = f"/static/screenshots/{screenshot_path.name}"
        else:
            print("🖼️ OG image available — skipping screenshot")

        return {
            "summary": summary,
            "used_huggingface": True,
            "og_image": og_image,
        }

    except Exception as e:
        print(f"🔥 ERROR in /summarize: {e}")
        return {
            "summary": "❌ An error occurred while summarizing the page.",
            "used_huggingface": False,
            "og_image": get_fallback_og("weird"),
        }


@app.post("/summarize/hf")
async def summarize_with_hf(input: URLInput):
    print(f"🤖 FORCED HF: {input.url}")

    try:
        html = await fetch_html(input.url)
        text = sanitize_html_for_summary(html)

        if len(text.strip()) < 100:
            return {
                "summary": "🧨 Hugging Face couldn’t find enough readable text.",
                "used_huggingface": False,
                "og_image": extract_og_image(html),
            }

        summary = await get_best_summary(text)
        return {
            "summary": summary,
            "used_huggingface": True,
            "og_image": extract_og_image(html),
        }

    except Exception as e:
        print(f"💥 FORCED HF ERROR: {e}")
        return {
            "summary": "🧨 Hugging Face couldn’t read this article right now.",
            "used_huggingface": False,
            "og_image": get_fallback_og("weird"),
        }
