import requests, re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dotenv import load_dotenv
import os

# --- LOAD ENV VARS ---
load_dotenv()
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
HF_HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}

# --- CLEAN VISIBLE TEXT FROM HTML ---
def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()
    text = soup.get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()

# --- EXTRACT OG TAGS FROM PAGE ---
def extract_og_tags(html: str):
    soup = BeautifulSoup(html, "html.parser")
    og_image, og_title, og_desc = "", "", ""
    for tag in soup.find_all("meta"):
        prop = tag.get("property")
        content = tag.get("content")
        if prop == "og:image":
            og_image = content
        elif prop == "og:title":
            og_title = content
        elif prop == "og:description":
            og_desc = content
    return og_image, og_title, og_desc

# --- FETCH HTML FROM A URL ---
def fetch_html(url: str, timeout=10) -> str:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text

# --- SUMMARIZE TEXT VIA HUGGING FACE ---
def summarize_text(text: str) -> str:
    payload = {"inputs": text}
    try:
        response = requests.post(HF_API_URL, headers=HF_HEADERS, json=payload, timeout=20)
        response.raise_for_status()
        response_json = response.json()
        print(f"✅ HF raw response: {response_json}")
        return response_json[0]["summary_text"]
    except Exception as e:
        raise RuntimeError(f"💥 Hugging Face summarization failed: {e}")
