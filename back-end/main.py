from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import requests, os, re, hashlib

load_dotenv()
HF_API_TOKEN = os.getenv("HF_ACCESS_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
HF_HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}

app = FastAPI()

# CORS FOR LOCAL DEV
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# URL BODY INPUT
class URLInput(BaseModel):
    url: str

# /////--- BLACKLIST ----////
BLACKLISTED_DOMAINS = ["washingtonpost.com", "nytimes.com", "bloomberg.com", "cnbc.com"]

# ==== HTML EXTRACTION ====
def extract_text_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    [script.decompose() for script in soup(["script", "style", "noscript"])]
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text)

# ==== OG:IMAGE HANDLER ====
def extract_og_image(html):
    match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
    return match.group(1) if match else None

# ==== SUMMARIZE VIA HUGGINGFACE ====
def summarize_text(text):
    try:
        response = requests.post(
            HF_API_URL,
            headers=HF_HEADERS,
            json={"inputs": text[:4000]},  # TRIM INPUT
            timeout=20
        )
        response.raise_for_status()
        result = response.json()
        if isinstance(result, list) and "summary_text" in result[0]:
            return result[0]["summary_text"]
        return "⚠️ Hugging Face returned unexpected response format."
    except Exception as e:
        print(f"💥 HUGGING FACE ERROR: {e}")
        return "⚠️ Hugging Face can't seem to summarize this content."

# ==== FASTAPI ENDPOINT ====
@app.post("/summarize")
def summarize(input: URLInput):
    url = input.url.strip()
    print(f"\n📥 Summarizing: {url}")

    # CHECK BLACKLIST
    for domain in BLACKLISTED_DOMAINS:
        if domain in url:
            print(f"🚫 BLOCKED DOMAIN: {domain}")
            return {
                "summary": "❌ Sorry, this source blocks access for summarization.",
                "og_image": None,
            }

    try:
        host = requests.utils.urlparse(url).netloc
        print(f"🌐 Host: {host}")
        response = requests.get(url, timeout=10)
        html = response.text
        print("⏳ Attempt 1 to fetch content...")
    except Exception as e:
        print(f"❌ Failed to fetch page: {e}")
        return {"summary": "❌ Could not fetch the provided URL."}

    # TEXT + IMAGE EXTRACTION
    text = extract_text_from_html(html)
    print(f"📄 Text Length: {len(text)}")
    og_image = extract_og_image(html)
    if og_image:
        print(f"🖼️ og:image: {og_image}")

    # SEND TO SUMMARIZER
    print("🤖 Sending to Hugging Face summarizer... (Attempt 1)")
    summary = summarize_text(text)

    return {"summary": summary, "og_image": og_image}
