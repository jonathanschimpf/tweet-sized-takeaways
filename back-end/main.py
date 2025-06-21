from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests, re, hashlib, os, time

load_dotenv()
HF_API_TOKEN = os.getenv("HF_ACCESS_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
HF_HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SummaryRequest(BaseModel):
    html: str

cache = {}
CACHE_EXPIRY = 3600
use_cache = True

def hash_input(content): return hashlib.sha256(content.encode()).hexdigest()

def extract_text_and_og_image(html):
    soup = BeautifulSoup(html, "html.parser")
    og_title = soup.find("meta", property="og:title")
    og_desc = soup.find("meta", property="og:description")
    og_image = soup.find("meta", property="og:image")

    title = og_title.get("content", "") if og_title else ""
    desc = og_desc.get("content", "") if og_desc else ""
    image_url = og_image.get("content", "") if og_image else None

    combined_text = (title + " " + desc).strip()

    if not combined_text:
        h1 = soup.find("h1")
        p_tags = soup.find_all("p")
        if h1:
            combined_text += h1.get_text(strip=True) + " "
        combined_text += " ".join(p.get_text(strip=True) for p in p_tags)

    return combined_text.strip(), image_url

@app.post("/summarize")
def summarize(request: SummaryRequest):
    input_value = request.html.strip()

    try:
        html = requests.get(input_value, timeout=5).text if input_value.startswith("http") else input_value
    except Exception as e:
        return {"summary": f"❌ URL fetch failed: {str(e)}"}

    text, og_image = extract_text_and_og_image(html)
    if not text:
        return {"summary": "⚠️ No usable content found", "og_image": og_image}

    if len(text) < 100:
        return {"summary": text[:280], "og_image": og_image}

    hashkey = hash_input(text)
    if use_cache and hashkey in cache:
        cached = cache[hashkey]
        if time.time() - cached["timestamp"] < CACHE_EXPIRY:
            return {"summary": cached["summary"], "cached": True, "og_image": cached.get("og_image")}

    try:
        # LIMIT TOKEN CONTEXT TO ~1024 tokens (~4k chars)
        input_trimmed = text[:4000]
        hf_response = requests.post(HF_API_URL, headers=HF_HEADERS, json={"inputs": input_trimmed})
        if hf_response.status_code != 200:
            return {"summary": f"❌ HF error {hf_response.status_code}", "og_image": og_image}

        raw_output = hf_response.json()[0]["summary_text"].strip()

        # BASIC SANITY CHECK: Reject if model injects unknown URLs or .com/.org not in input
        suspicious = False
        if any(domain in raw_output.lower() for domain in [".com", ".org", ".net"]):
            if not any(domain in text.lower() for domain in [".com", ".org", ".net"]):
                suspicious = True

        if suspicious:
            return {
                "summary": text[:280],
                "og_image": og_image,
                "warning": "🤖 Model added unexpected link or domain. Fallback used."
            }

        cache[hashkey] = {
            "summary": raw_output,
            "timestamp": time.time(),
            "og_image": og_image
        }
        return {"summary": raw_output, "cached": False, "og_image": og_image}

    except Exception as e:
        return {"summary": f"❌ HF exception: {str(e)}", "og_image": og_image}

@app.post("/clear-cache")
def clear_cache():
    cache.clear()
    return {"status": "✅ Cache cleared."}
