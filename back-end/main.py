from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import requests, re, os
from dotenv import load_dotenv

# --- LOAD ENV VARS ---
load_dotenv()
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
HF_HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}
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

# --- BLACKLIST DOMAINS ---
BLACKLISTED_DOMAINS = {
    "news": [
        "washingtonpost.com",
        "nytimes.com",
        "bloomberg.com",
        "cnbc.com",
    ],
    "social": [
        "instagram.com",
        "facebook.com",
        "threads.net",
        "tiktok.com",
        "linkedin.com",
        "x.com",
        "twitter.com",
    ],
}

# --- COOKIE WALL DOMAINS ---
COOKIE_WALL_DOMAINS = [
    "docs.google.com",
]

# --- REQUEST MODEL ---
class URLInput(BaseModel):
    url: str

# --- BLACKLIST CATEGORY CHECK ---
def get_blacklist_category(domain):
    for category, domains in BLACKLISTED_DOMAINS.items():
        if any(d in domain for d in domains):
            return category
    return None

# --- CLEAN TEXT EXTRACTOR ---
def extract_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for script in soup(["script", "style", "noscript"]):
        script.extract()
    text = soup.get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()

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
    if domain in COOKIE_WALL_DOMAINS:
        print("🍪 Cookie/session-gated domain — skipping.")
        return {
            "summary": "💥 This site is gatekeeping content behind cookies/sessions. Summarize it yourself. ✨",
            "og_image": "",
        }

    # --- HANDLE SOCIAL/NEWS BLACKLISTS ---
    if blacklist_category in ["social", "news"]:
        try:
            response = requests.get(url, timeout=10)
            html = response.text
            soup = BeautifulSoup(html, "html.parser")
            og_image = ""
            for tag in soup.find_all("meta"):
                if tag.get("property") == "og:image":
                    og_image = tag.get("content")
                    break
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

        elif blacklist_category == "news":
            print("🚫 News media domain — skipping summarization.")
            return {
                "summary": "We can’t summarize this one — blame the paywalls, trackers, or both. 🧱💸",
                "og_image": og_image,
            }

    # --- FETCH HTML ---
    try:
        response = requests.get(url, timeout=10)
        html = response.text
        print(f"✅ HTML fetched (len: {len(html)})")
    except Exception as e:
        print(f"❌ Failed to fetch page: {e}")
        return {"summary": "❌ Could not fetch the provided URL.", "og_image": ""}

    # --- EXTRACT OG TAGS ---
    soup = BeautifulSoup(html, "html.parser")
    og_image, og_title, og_desc = "", "", ""
    for tag in soup.find_all("meta"):
        if tag.get("property") == "og:image":
            og_image = tag.get("content")
        elif tag.get("property") == "og:title":
            og_title = tag.get("content")
        elif tag.get("property") == "og:description":
            og_desc = tag.get("content")

    print(f"🧠 og:title: {og_title}")
    print(f"🧠 og:description: {og_desc}")
    print(f"🖼️ og:image: {og_image}")

    # --- EXTRACT BODY TEXT ---
    text = extract_text(html)
    print(f"📄 Text extract length: {len(text)}")

    # --- FALLBACK TO OG IF TEXT TOO SHORT ---
    if len(text) < 100:
        print("⚠️ Not enough text for summarization. Falling back to OG tags.")
        return {
            "summary": og_desc or og_title or "⚠️ Hugging Face can't seem to summarize this content.",
            "og_image": og_image,
        }

    # --- CALL HUGGING FACE ---
    try:
        print("🤖 Sending to Hugging Face summarizer...")
        payload = {"inputs": text}
        hf_response = requests.post(HF_API_URL, headers=HF_HEADERS, json=payload, timeout=20)
        hf_response.raise_for_status()
        response_json = hf_response.json()
        print(f"✅ HF raw response: {response_json}")
        summary_text = response_json[0]["summary_text"]
        return {"summary": summary_text, "og_image": og_image}
    except Exception as e:
        print(f"💥 HUGGING FACE ERROR: {e}")
        print("🧠 Falling back to og:description or og:title...")
        return {
            "summary": og_desc or og_title or "⚠️ Hugging Face couldn't summarize this page.",
            "og_image": og_image,
        }