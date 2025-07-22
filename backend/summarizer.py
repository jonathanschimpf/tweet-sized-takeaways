import os
import re
import aiohttp
from bs4 import BeautifulSoup
from .extract import extract_og_tags, extract_paragraph_like_block


HF_API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
CHARACTER_THRESHOLD = 100  # Minimum native content before using HF


async def fetch_html(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()


async def get_best_summary(text: str) -> str:
    if not text.strip():
        return "🚫 No valid content extracted from the page."

    # Use only first ~1000 characters to stay within HF prompt constraints
    prompt = text[:1024]

    headers = {
        "Authorization": f"Bearer {os.getenv('HF_API_TOKEN')}",
        "Content-Type": "application/json",
    }
    payload = {"inputs": prompt}

    async with aiohttp.ClientSession() as session:
        async with session.post(HF_API_URL, headers=headers, json=payload) as resp:
            if resp.status == 200:
                result = await resp.json()
                if isinstance(result, list) and result and "summary_text" in result[0]:
                    return result[0]["summary_text"]
                return "🤖 Hugging Face response malformed."
            return f"🛑 Hugging Face error {resp.status}: {await resp.text()}"


def extract_og_image(html: str) -> str:
    image, _ = extract_og_tags(html)
    return image


def summarize_text(html: str) -> str:
    """
    Attempts to extract native content blocks suitable for summarization.
    Returns long text blob (not truncated).
    """
    return extract_paragraph_like_block(html)


async def summarize_with_fallback(html: str) -> dict:
    """
    Attempts native extraction, then uses Hugging Face if needed.
    Returns summary, image, and flag.
    """
    extracted = extract_paragraph_like_block(html)
    og_image = extract_og_image(html)

    if len(extracted.strip()) >= CHARACTER_THRESHOLD:
        return {
            "summary": extracted.strip(),
            "used_huggingface": False,
            "og_image": og_image,
        }

    # Not enough native content — try AI summarization
    summary = await get_best_summary(extracted)
    return {
        "summary": summary,
        "used_huggingface": True,
        "og_image": og_image,
    }


def sanitize_html_for_summary(html: str) -> str:
    """
    Removes navigation, accessibility, header/footer, and other clutter before summarizing.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove common clutter tags
    for tag in soup(
        ["script", "style", "nav", "header", "footer", "noscript", "aside"]
    ):
        tag.decompose()

    # Remove divs/spans/etc. with nav/accessibility classes or IDs
    for attr in ["id", "class"]:
        for bad in ["skip", "accessibility", "nav", "menu", "footer", "header"]:
            for el in soup.find_all(attrs={attr: re.compile(bad, re.I)}):
                el.decompose()

    # Get visible text
    text = soup.get_text(separator=" ", strip=True)

    # Final cleanup
    text = re.sub(r"\s+", " ", text)
    text = re.sub(
        r"(Navigation Menu|Skip to main content|Keyboard shortcuts|Accessibility links).*",
        "",
        text,
        flags=re.I,
    )

    return text.strip()
