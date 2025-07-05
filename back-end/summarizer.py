from bs4 import BeautifulSoup
import re, aiohttp, os
from dotenv import load_dotenv

load_dotenv()
HF_API_TOKEN = os.getenv("HF_API_TOKEN")


# --- FETCH HTML ---
async def fetch_html(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0",
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=15) as response:
            response.raise_for_status()
            return await response.text()


# --- DEDUPE AND COMBINE HEAD STRINGS ---
def dedupe_and_combine(parts: list[str]) -> str:
    seen = set()
    combined = []
    for part in parts:
        cleaned = part.strip() if part else None
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            combined.append(cleaned)
    return " · ".join(combined)


# --- EXTRACT OPEN GRAPH TAGS ---
def extract_og_tags(html: str):
    soup = BeautifulSoup(html, "html.parser")

    og_image = soup.find("meta", property="og:image")
    og_title = soup.find("meta", property="og:title")
    og_desc = soup.find("meta", property="og:description")
    meta_desc = soup.find("meta", attrs={"name": "description"})
    title_tag = soup.find("title")
    h1_tag = soup.find("h1")

    # SAFE EXTRACT
    og_image = og_image["content"] if og_image else None
    og_title = og_title["content"] if og_title else None
    og_desc = og_desc["content"] if og_desc else None
    meta_desc = meta_desc["content"] if meta_desc else None
    title = title_tag.string.strip() if title_tag and title_tag.string else None
    h1 = h1_tag.get_text(strip=True) if h1_tag else None

    # PRIORITIZE og:title, og:description, meta description, then fallback tags
    head_parts = [og_title, og_desc, meta_desc, title, h1]
    head_text = dedupe_and_combine(head_parts)

    return og_image, og_title, og_desc, meta_desc, title, h1, head_text


# --- EXTRACT BODY TEXT ---
def extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # REMOVE NON-CONTENT TAGS
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
        tag.decompose()

    # REMOVE IMAGE TAGS
    for img in soup.find_all("img"):
        img.decompose()

    # REMOVE SHORT OR URL-LIKE STRINGS
    text = soup.get_text(separator=" ", strip=True)
    cleaned = re.sub(r"\s+", " ", text)

    # STRIP OUT IMAGE FILENAMES OR .png/.jpg PATHS
    cleaned = re.sub(r"https?:\/\/\S+\.(?:png|jpe?g|webp|gif)(\?\S*)?", "", cleaned)

    return cleaned


# --- SUMMARIZE TEXT (HF API) ---
async def summarize_text(text: str) -> str:
    if not HF_API_TOKEN:
        raise Exception("Hugging Face API token missing")

    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"inputs": text[:4000]}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api-inference.huggingface.co/models/facebook/bart-large-cnn",
            headers=headers,
            json=payload,
            timeout=30,
        ) as response:
            result = await response.json()
            if isinstance(result, list) and "summary_text" in result[0]:
                return result[0]["summary_text"]
            raise Exception(f"Hugging Face Error: {result}")


# --- RETURN ALL OG/META TAGS + COMBINED HEAD TEXT ---
def extract_all_metadata(html: str):
    og_image, og_title, og_desc, meta_desc, title, h1, head_text = extract_og_tags(html)
    return og_image, og_title, og_desc, meta_desc, title, h1, head_text
