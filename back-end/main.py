from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import requests, re, hashlib, os, time

load_dotenv()

HF_API_TOKEN = os.getenv("HF_ACCESS_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
HF_HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}

app = FastAPI()

# ENABLE CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----//////----- BLOCK LIST ----//////-----
BLOCKED_HOSTS = {
    "www.washingtonpost.com",
    "washingtonpost.com",
}
# ------------------------------------------

# REQUEST MODEL
class SummaryRequest(BaseModel):
    url: str

# CACHE
cache = {}

# PARSE CONTENT
def extract_text_and_og_image(html):
    soup = BeautifulSoup(html, "html.parser")

    # Get all <p> content
    paragraphs = soup.find_all("p")
    text = " ".join(p.get_text() for p in paragraphs if p.get_text().strip())

    # Fallback: use og:description if no <p> content
    if not text:
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            text = og_desc["content"]

    # Try to extract og:image
    og_image = None
    og_tag = soup.find("meta", property="og:image")
    if og_tag and og_tag.get("content"):
        og_image = og_tag["content"]

    return text.strip(), og_image

# HASH INPUT FOR CACHE
def hash_input(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

# HEADERS + SESSION
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

def create_retry_session():
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# MAIN SUMMARIZATION ENDPOINT
@app.post("/summarize")
def summarize(request: SummaryRequest):
    url = request.url
    host = urlparse(url).netloc
    print(f"\n📥 Summarizing: {url}")
    print(f"🌐 Host: {host}")

    # BLOCK CHECK
    if host in BLOCKED_HOSTS:
        print(f"🚫 Blocked domain: {host}")
        return {
            "summary": "⚠️ Sorry, this domain is known to block automated summarization.",
            "og_image": None
        }

    session = create_retry_session()
    html = None

    for attempt in range(2):
        try:
            print(f"⏳ Attempt {attempt + 1} to fetch content...")
            response = session.get(url, headers=HEADERS, timeout=(5, 30))
            response.raise_for_status()
            html = response.text
            break
        except requests.exceptions.RequestException as e:
            print(f"❌ FETCH ERROR (attempt {attempt + 1}): {e}")
            if attempt == 1:
                return {
                    "summary": f"⚠️ Failed to load content from {host}. Try another link.",
                    "og_image": None
                }

    # EXTRACT TEXT + OG IMAGE
    text, og_image = extract_text_and_og_image(html)
    print(f"📄 Text Length: {len(text)}")
    print(f"🖼️ og:image: {og_image if og_image else 'None'}")

    if not text:
        return {
            "summary": "⚠️ No usable content found on this page.",
            "og_image": og_image
        }

    # LIMIT TO 3000 CHARACTERS
    if len(text) > 3000:
        text = text[:3000]

    hashkey = hash_input(text)
    if hashkey in cache:
        print("⚡ Using cached summary")
        return {**cache[hashkey], "cached": True}

    # SEND TO HUGGING FACE
    try:
        print("🤖 Sending to Hugging Face summarizer...")
        response = requests.post(
            HF_API_URL,
            headers=HF_HEADERS,
            json={"inputs": text},
            timeout=20
        )
        response.raise_for_status()
        result = response.json()

        if isinstance(result, list) and "summary_text" in result[0]:
            summary = result[0]["summary_text"]
        else:
            raise ValueError(f"Unexpected Hugging Face response: {result}")

    except Exception as e:
        print(f"💥 HUGGING FACE ERROR: {e}")
        return {
            "summary": "⚠️ Hugging Face can't seem to summarize this content.",
            "og_image": og_image
        }

    cache[hashkey] = {
        "summary": summary,
        "timestamp": time.time(),
        "og_image": og_image,
    }

    return {
        "summary": summary,
        "cached": False,
        "og_image": og_image,
    }

# CACHE CLEARING ENDPOINT
@app.post("/clear-cache")
def clear_cache():
    cache.clear()
    return {"status": "🧹 Cache cleared."}
