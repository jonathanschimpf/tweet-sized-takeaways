from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
import re
import os

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Blacklist
# /////--- BLACKLIST ----////
BLACKLISTED_DOMAINS = ["washingtonpost.com", "nytimes.com", "bloomberg.com", "cnbc.com"]

# Hugging Face API
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}


class URLInput(BaseModel):
    url: str


@app.post("/summarize")
def summarize_link(input: URLInput):
    url = input.url.strip()
    print(f"\n📥 Summarizing: {url}")

    # Check blacklist
    if any(domain in url for domain in BLACKLISTED_DOMAINS):
        print("🚫 Blacklisted domain — skipping summarization.")
        return {"summary": "⚠️ This source can't be summarized due to restrictions.", "og_image": ""}

    try:
        print(f"🌐 Host: {requests.utils.urlparse(url).netloc}")
        response = requests.get(url, timeout=10)
        html = response.text
    except Exception as e:
        print(f"❌ Failed to fetch page: {e}")
        return {"summary": "❌ Could not fetch the provided URL.", "og_image": ""}

    # --- Extract og:image ---
    soup = BeautifulSoup(html, "html.parser")
    og_image = ""
    og_title = ""
    og_desc = ""
    for tag in soup.find_all("meta"):
        if tag.get("property") == "og:image":
            og_image = tag.get("content")
        elif tag.get("property") == "og:title":
            og_title = tag.get("content")
        elif tag.get("property") == "og:description":
            og_desc = tag.get("content")

    if og_image:
        print(f"🖼️ og:image: {og_image}")

    # --- Extract text content ---
    text = extract_text(html)
    print(f"📄 Text Length: {len(text)}")

    # --- Try Hugging Face summarization ---
    if len(text) < 100:
        print("⚠️ Not enough text for summarization. Falling back to OG tags.")
        return {
            "summary": og_desc or og_title or "⚠️ Hugging Face can't seem to summarize this content.",
            "og_image": og_image,
        }

    payload = {"inputs": text}
    try:
        print("🤖 Sending to Hugging Face summarizer... (Attempt 1)")
        hf_response = requests.post(HF_API_URL, headers=HEADERS, json=payload, timeout=20)
        hf_response.raise_for_status()
        summary_text = hf_response.json()[0]["summary_text"]
        return {"summary": summary_text, "og_image": og_image}
    except Exception as e:
        print(f"💥 HUGGING FACE ERROR: {e}")
        print("🧠 Falling back to og:description or og:title...")
        return {
            "summary": og_desc or og_title or "⚠️ Hugging Face can't seem to summarize this content.",
            "og_image": og_image,
        }


def extract_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for script in soup(["script", "style", "noscript"]):
        script.extract()
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text
