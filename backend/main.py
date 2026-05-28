# backend/main.py
# ✅ MAIN FASTAPI BACKEND ENTRYPOINT — lean, no length guards

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

import os
from pathlib import Path

# ---------- App & static mounts ----------

app = FastAPI()

# Public assets are served from /images (public/images -> /images)
app.mount(
    "/images", StaticFiles(directory=os.path.join("public", "images")), name="images"
)

# Also expose /public at /static (kept for any existing uses)
public_path = os.path.join(os.path.dirname(__file__), "..", "public")
app.mount("/static", StaticFiles(directory=public_path), name="static")

# ---------- Env ----------
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
print(f"🔐 Hugging Face token loaded? {'Yes' if HF_API_TOKEN else 'No'}")
print("✅ .env path:", os.path.abspath(".env"))

# ---------- Internal modules ----------
from .summarizer import (
    fetch_html,
    get_best_summary,  # builds strict prompt internally
    extract_social_content_for_hf,  # picks og:description/og:title or sanitized text
    extract_og_image,  # returns (og_or_loop_img, weird_quip_if_used | None)
)
from .extract import (
    detect_platform,
    extract_media_metadata,
    extract_og_tags,
    extract_paragraph_like_block,
)

# ---------- CORS ----------
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


# ---------- Health ----------
@app.api_route("/", methods=["GET", "HEAD"])
def read_root():
    return {"message": "Backend is live"}


# ---------- Models ----------
class URLInput(BaseModel):
    url: str


# ---------- Helpers ----------
def trim_to_280(text: str) -> str:
    text = (text or "").strip()
    junk = ".,;:!?…'\""

    if len(text) <= 280:
        return text.rstrip(junk)

    cut = text[:280].strip()

    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]

    return cut.rstrip(junk)


def _debug_payload(**kwargs):
    debug = {"debug": True}
    debug.update(kwargs)
    return debug


# =========================
# MAIN SUMMARIZATION ROUTE
# =========================
@app.post("/summarize")
async def summarize(input: URLInput):
    url = input.url.strip()
    print(f"🔵 URL received: {url}")
    platform = detect_platform(url)

    try:
        html = await fetch_html(url)
        print("🟢 HTML fetched successfully")

        # 1) OG tags
        og_image_from_tags, og_desc = extract_og_tags(html, url)
        media = extract_media_metadata(html, url)

        # 2) Stable image fallback for THIS call
        loop_img, fallback_msg = extract_og_image(html, url)
        final_img = og_image_from_tags or loop_img
        image_source = "og_tags" if og_image_from_tags else "fallback"
        if final_img and not media.get("poster_image"):
            media["poster_image"] = final_img

        debug_base = _debug_payload(
            url_received=url,
            platform=platform,
            html_length=len(html or ""),
            og_image_from_tags=og_image_from_tags or "",
            fallback_image=loop_img or "",
            fallback_message=fallback_msg or "",
            final_image=final_img or "",
            image_source=image_source,
            media_poster_image=media.get("poster_image", ""),
        )

        # 3) If author provided ANY og:description, use it
        if og_desc and og_desc.strip():
            print("🟠 Using og:description")
            return {
                "summary": trim_to_280(og_desc),
                "used_huggingface": False,
                "og_image": final_img,
                "media": media,
                "debug": {
                    **debug_base,
                    "summary_source": "og_description",
                    "og_description": og_desc,
                    "native_text_length": None,
                    "native_text_sample": "",
                },
            }

        # 4) Next: native paragraph-like scrape (if anything came back)
        native = (extract_paragraph_like_block(html) or "").strip()
        print(f"🟡 Native text extracted: {native[:300]}")
        if native:
            print("🟠 Using native scrape")
            return {
                "summary": trim_to_280(native),
                "used_huggingface": False,
                "og_image": final_img,
                "media": media,
                "debug": {
                    **debug_base,
                    "summary_source": "native_scrape",
                    "og_description": og_desc or "",
                    "native_text_length": len(native),
                    "native_text_sample": native[:500],
                },
            }

        # 5) Stop here. /summarize is metadata/native-only; HF is explicit via /summarize/hf.
        print("🧸 No OG/meta/native text found — returning non-HF fallback.")
        return {
            "summary": fallback_msg or "There is literally no page text to summarize!",
            "used_huggingface": False,
            "og_image": final_img,
            "media": media,
            "debug": {
                **debug_base,
                "summary_source": "fallback_message",
                "og_description": og_desc or "",
                "native_text_length": 0,
                "native_text_sample": "",
            },
        }

    except Exception as e:
        print(f"🔥 ERROR in /summarize: {e}")
        # Show a deterministic image even on exception
        try:
            img, fallback_msg = extract_og_image("", url)
        except Exception:
            img = "/images/og-fallbacks/weirdlink/weirdlink.jpg"
            fallback_msg = None
        return {
            "summary": fallback_msg or "❌ An error occurred while summarizing the page.",
            "used_huggingface": False,
            "og_image": img,
            "debug": _debug_payload(
                url_received=url,
                platform=platform,
                error=str(e),
                summary_source="exception_fallback",
                final_image=img,
                image_source="exception_fallback",
                fallback_message=fallback_msg or "",
            ),
            "media": {
                "platform": "web",
                "kind": "link",
                "is_video": False,
                "is_reel": False,
                "is_carousel": False,
                "poster_image": img,
                "content_type": "",
                "signals": [],
            },
        }


# =========================
# MANUAL PEGASUS ROUTE
# =========================
@app.post("/summarize/hf")
async def summarize_with_hf(input: URLInput):
    url = input.url.strip()
    print(f"🤖 FORCED HF: {url}")

    try:
        html = await fetch_html(url)
        media = extract_media_metadata(html, url)

        # Choose image + quip once
        og_img_from_tags, _ = extract_og_tags(html, url)
        final_img, weird_msg = extract_og_image(html, url)
        if og_img_from_tags:
            final_img, weird_msg = og_img_from_tags, None  # OG wins
        if final_img and not media.get("poster_image"):
            media["poster_image"] = final_img

        # Source text for Pegasus
        source_text = extract_social_content_for_hf(html, url)

        # Try HF a few times; accept WeirdLink default or any non‑empty HF text
        max_retries = 3
        summary = None
        for attempt in range(1, max_retries + 1):
            print(f"🔁 Pegasus attempt {attempt}...")
            summary = await get_best_summary(source_text, default_weird_msg=weird_msg)
            if summary == weird_msg or (summary and summary.strip()):
                break

        print(f"✅ Pegasus returned after {attempt} attempt(s):\n{summary}\n")

        used_hf = not (summary == weird_msg)

        return {
            "summary": trim_to_280(summary or "🤷‍♂️ No summary available."),
            "used_huggingface": used_hf,
            "og_image": final_img,
            "media": media,
        }

    except Exception as e:
        print(f"💥 FORCED HF ERROR: {e}")
        try:
            img, fallback_msg = extract_og_image("", url)
        except Exception:
            img = "/images/og-fallbacks/weirdlink/weirdlink.jpg"
            fallback_msg = None
        return {
            "summary": fallback_msg or "🧸 Hugging Face couldn't read this article right now.",
            "used_huggingface": False,
            "og_image": img,
            "media": {
                "platform": "web",
                "kind": "link",
                "is_video": False,
                "is_reel": False,
                "is_carousel": False,
                "poster_image": img,
                "content_type": "",
                "signals": [],
            },
        }
