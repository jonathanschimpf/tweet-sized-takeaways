from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from urllib.parse import urlparse
from dotenv import load_dotenv
from blacklist import get_blacklist_category, is_cookie_gated, normalize_domain
from fallbacks import get_fallback_og
from summarizer import extract_text, extract_all_metadata, fetch_html, summarize_text
import os, time

# --- APP ---
app = FastAPI()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- [BYE-BYE STATIC LET'S GO PUBLIC] ---
# 'public' DIR AT ROOT
# RESOLVE STATIC PATH TO PROJECT ROOT
public_path = os.path.join(os.path.dirname(__file__), "..", "public")
app.mount("/", StaticFiles(directory=public_path), name="public")



# --- ENV VARS ---
load_dotenv()
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
print(f"🔐 Hugging Face Token Present? {bool(HF_API_TOKEN)}")


# --- REQUEST BODY ---
class URLInput(BaseModel):
    url: str


# --- DEDUPE TEXT PARTS ---
def dedupe_and_combine(parts: list[str]) -> str:
    seen = set()
    combined = []

    for part in parts:
        cleaned = part.strip() if part else None
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            combined.append(cleaned)

    return " · ".join(combined)


# --- MAIN ROUTE ---
@app.post("/summarize")
async def summarize_link(input: URLInput):
    url = input.url.strip()
    if not url.startswith("http"):
        url = "https://" + url

    print(f"\n📥 Summarizing: {url}")
    domain = urlparse(url).netloc
    print(f"🌐 Host: {domain}")
    blacklist_category = get_blacklist_category(domain)

    # --- COOKIE-GATED ---
    if is_cookie_gated(domain):
        print("🍪 Cookie/session-gated domain — skipping.")
        return {
            "summary": "✨ This site is gatekeeping content behind cookies/sessions. Summarize it yourself. ✨",
            "og_image": get_fallback_og("cookie"),
        }

    # --- BLACKLIST: SOCIAL / NEWS ---
    if blacklist_category in ["social", "news"]:
        fallback_image = get_fallback_og(blacklist_category)

        if blacklist_category == "social":
            print("🚫 Social media domain — returning snark fallback.")
            return {
                "summary": "A summary for a social media post? Seriously? Go use the app. ✌️✨",
                "og_image": fallback_image,
            }

        if blacklist_category == "news":
            print("🚫 News media domain — skipping summarization.")
            return {
                "summary": "We can’t summarize this one — blame the paywalls, trackers, or both. 🧱💸",
                "og_image": fallback_image,
            }

    # --- FETCH HTML ---
    try:
        t0 = time.time()
        html = await fetch_html(url)
        print(f"✅ HTML fetched (len: {len(html)}) in {time.time() - t0:.2f}s")
    except Exception as e:
        print(f"❌ Failed to fetch page: {e}")
        return {
            "summary": "Hugging Face thinks that link is weird... 🙃",
            "og_image": get_fallback_og("weird"),
        }

    # --- METADATA ---
    og_image, og_title, og_desc, meta_desc, page_title, h1_text, head_text = extract_all_metadata(html)

    print("\n--- HEAD METADATA DEBUG ---")
    print(f"🧠 og:title: {og_title}")
    print(f"🧠 og:description: {og_desc}")
    print(f"🧠 <meta name='description'>: {meta_desc}")
    print(f"🧠 <title>: {page_title}")
    print(f"🧠 <h1>: {h1_text}")
    print(f"🖼️ og:image: {og_image}")
    print(f"🧠 COMBINED HEAD TEXT: {head_text}")

    # --- SMART SHORTCUT: USE HEAD TEXT IF CLEAN ---
    if len(head_text) > 100:
        print("⚡ Using combined head metadata as summary (skipping HF).")
        return {
            "summary": head_text,
            "og_image": og_image or get_fallback_og("weird"),
        }

    # --- TEXT EXTRACTION ---
    text = extract_text(html)
    print(f"📄 Text extract length: {len(text)}")

    # --- FALLBACK IF NOT ENOUGH TEXT ---
    if len(text) < 100:
        print("⚠️ Not enough text. Returning best available head metadata.")
        summary = head_text or "🌀 No clue. This page might’ve been built on vibes."
        print("⚡ Using combined head metadata as summary (skipping HF).")
        return {
            "summary": summary,
            "og_image": og_image or get_fallback_og("weird"),
        }

    # --- HUGGING FACE SUMMARIZATION ---
    try:
        print("🤖 Sending to Hugging Face summarizer...")
        t1 = time.time()
        summary_text = await summarize_text(text)
        print(f"✅ Hugging Face response in {time.time() - t1:.2f}s")
        return {
            "summary": summary_text,
            "og_image": og_image or get_fallback_og("weird"),
        }
    except Exception as e:
        print(f"💥 HUGGING FACE ERROR: {e}")
        fallback_summary = head_text or "🌀 Something broke. Vibes only."
        return {
            "summary": fallback_summary,
            "og_image": og_image or get_fallback_og("weird"),
        }
