from backend.bs4 import BeautifulSoup
import re


def extract_og_tags(html: str) -> tuple[str, str]:
    """
    Extract Open Graph image and description if available.
    """
    soup = BeautifulSoup(html, "html.parser")
    og_image = soup.find("meta", property="og:image")
    og_desc = soup.find("meta", property="og:description")

    image = og_image["content"] if og_image and og_image.has_attr("content") else ""
    desc = og_desc["content"] if og_desc and og_desc.has_attr("content") else ""

    return image, desc


def extract_paragraph_like_block(html: str) -> str:
    """
    Fallback HTML block extractor for pages without good metadata.
    Prioritize character count for summarization (not word count).
    """
    soup = BeautifulSoup(html, "html.parser")

    # First: <main> or <article> if decently long
    for tag in ["main", "article"]:
        node = soup.find(tag)
        if node:
            text = node.get_text(separator=" ", strip=True)
            if len(text) >= 280:  # CHARACTERS not words
                return text

    # Second: divs with decent content
    divs = soup.find_all("div")
    candidates = []
    for div in divs:
        txt = div.get_text(separator=" ", strip=True)
        if 280 <= len(txt) <= 3000 and "block user" not in txt.lower():
            candidates.append(txt)

    if candidates:
        return max(candidates, key=len)

    # Last: first 5 paragraphs
    paragraphs = soup.find_all("p")
    blob = " ".join(p.get_text(strip=True) for p in paragraphs[:5])
    return blob
