# backend/extract.py
# ------------------------------------------------------------
# Pure OG/meta extractor (no fallback loops here)
# - extract_og_tags(html, url) -> (og_image or "", og_description or "")
# - extract_paragraph_like_block(html) -> str (light heuristic)
# ------------------------------------------------------------

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import re
from typing import Any, Tuple


IG_STATS_PREFIX_RE = re.compile(
    r"^\s*(?:[\d,.]+(?:\.\d+)?[KMB]?\s+likes?,\s*)?"
    r"[\d,.]+(?:\.\d+)?[KMB]?\s+comments?\s*[-–—]\s*",
    re.IGNORECASE,
)

IG_AUTHOR_DATE_PREFIX_RE = re.compile(
    r"^\s*[A-Za-z0-9_.]+\s+on\s+"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|"
    r"January|February|March|April|May|June|July|August|September|"
    r"October|November|December)"
    r"\s+\d{1,2},?\s+\d{4}:?\s*",
    re.IGNORECASE,
)


# ---- OG/TWITTER TAG EXTRACTOR ----
def extract_og_tags(html: str, url: str = "") -> Tuple[str, str]:
    """
    Extract Open Graph/Twitter IMAGE + DESCRIPTION from raw HTML.
    - If no image is found, return "" (caller handles fallback).
    - Description may come from og:description or twitter:description.
    """
    soup = BeautifulSoup(html or "", "html.parser")
    platform = detect_platform(url)
    is_meta_platform = platform in {"instagram", "facebook", "threads"}

    if platform == "twitter":
        return "", ""

    def _first_meta_content(keys: list[str]) -> str:
        for key in keys:
            tag = soup.find("meta", attrs={"property": key})
            if tag and tag.get("content"):
                val = tag["content"].strip()
                if val:
                    return val
            tag = soup.find("meta", attrs={"name": key})
            if tag and tag.get("content"):
                val = tag["content"].strip()
                if val:
                    return val
        return ""

    # Instagram's OG image can be a square crop. Use full-size media only when it
    # comes from the exact post object for this shortcode; otherwise trust OG/Twitter.
    img = ""
    if platform == "instagram":
        img = _first_instagram_post_image(html or "", url)
    elif platform == "facebook":
        img = _facebook_formatted_background_image(html or "", url)
    if not img:
        img = _first_meta_content(
            ["og:image", "og:image:secure_url", "twitter:image", "twitter:image:src"]
        )

    # Absolutize if needed (relative or protocol‑relative)
    if img and url:
        try:
            img = urljoin(url, img)
        except Exception:
            pass

    # Description: try OG then Twitter then standard meta description
    desc = _first_meta_content(["og:description", "twitter:description"])
    if not desc:
        tag = soup.find("meta", attrs={"name": "description"})
        if tag and tag.get("content"):
            desc = tag["content"].strip()

    if is_meta_platform:
        desc = clean_meta_description(desc)

    # IMPORTANT: do not choose a fallback image here; return "" so caller can decide
    return (img or "", desc or "")


def clean_meta_description(desc: str) -> str:
    """
    Meta properties often prefix OG descriptions with engagement stats, author/date
    boilerplate, and login/share chrome. Strip that so the app shows the post copy.
    """
    text = (desc or "").strip()
    text = IG_STATS_PREFIX_RE.sub("", text, count=1)
    text = IG_AUTHOR_DATE_PREFIX_RE.sub("", text, count=1)
    text = re.sub(
        r"^\s*[\d,.]+(?:\.\d+)?[KMB]?\s+(?:likes?|reactions?)\s*[-–—]\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^\s*See\s+posts,\s+photos\s+and\s+more\s+on\s+Facebook\.?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^\s*(?:See|View)\s+.+?\s+(?:post|posts|photos?|videos?)\s+on\s+(?:Facebook|Instagram|Threads)\.?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\s*(?:Log in|Sign up)\s+to\s+(?:view|see).*$", "", text, flags=re.IGNORECASE
    )
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    if _looks_like_threads_chrome(text):
        return ""

    quoted = re.match(r"""^["'](.+?)["']\.?$""", text)
    if quoted:
        text = quoted.group(1).strip()

    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1].strip()

    return text


def detect_platform(url: str) -> str:
    url = (url or "").strip()
    parseable = url if re.match(r"^[a-z][a-z0-9+.-]*://", url, re.I) else f"https://{url}"
    parsed = urlparse(parseable)
    host = (parsed.netloc or "").lower()
    host = host[4:] if host.startswith("www.") else host
    if host == "instagram.com" or host.endswith(".instagram.com"):
        return "instagram"
    if host == "facebook.com" or host.endswith(".facebook.com") or host == "fb.watch":
        return "facebook"
    if host in {"threads.net", "threads.com"} or host.endswith(
        (".threads.net", ".threads.com")
    ):
        return "threads"
    if host in {"x.com", "twitter.com"} or host.endswith((".x.com", ".twitter.com")):
        return "twitter"
    return "web"


def extract_media_metadata(html: str, url: str = "") -> dict[str, Any]:
    """
    Return structured media hints without replacing OG image behavior.
    The image remains the poster/preview; these flags tell the UI how to frame it.
    """
    soup = BeautifulSoup(html or "", "html.parser")
    url_l = (url or "").lower()
    platform = detect_platform(url)
    text_blob = html or ""

    media: dict[str, Any] = {
        "platform": platform,
        "kind": "link",
        "is_video": False,
        "is_reel": False,
        "is_carousel": False,
        "poster_image": "",
        "content_type": "",
        "signals": [],
    }

    def add_signal(signal: str):
        if signal not in media["signals"]:
            media["signals"].append(signal)

    og_type = _first_meta_content_from_soup(
        soup, ["og:type", "twitter:card", "medium", "og:video:type"]
    ).lower()
    if og_type:
        media["content_type"] = og_type
        if "video" in og_type or og_type in {"player", "summary_large_image"}:
            add_signal(f"meta:{og_type}")

    if re.search(r"/(?:reel|reels)/", url_l):
        media["is_video"] = True
        media["is_reel"] = True
        add_signal("url:reel")

    instagram_post = (
        _find_instagram_post_object(html or "", url)
        if platform == "instagram"
        else None
    )
    carousel = (
        instagram_post.get("carousel_media")
        if isinstance(instagram_post, dict)
        else _extract_json_array_after_key(text_blob, "carousel_media")
    )
    carousel_has_video = False
    if isinstance(carousel, list) and len(carousel) > 1:
        media["is_carousel"] = True
        add_signal("json:carousel_media")
        carousel_has_video = _instagram_carousel_has_video(carousel)

    sidecar = _extract_json_object_after_key(text_blob, "edge_sidecar_to_children")
    edges = sidecar.get("edges") if isinstance(sidecar, dict) else None
    if isinstance(edges, list) and len(edges) > 1:
        media["is_carousel"] = True
        add_signal("json:sidecar")
        carousel_has_video = carousel_has_video or _instagram_sidecar_has_video(edges)

    if carousel_has_video:
        media["is_video"] = True
        add_signal("json:carousel-video")

    video_url = _first_meta_content_from_soup(
        soup,
        [
            "og:video",
            "og:video:url",
            "og:video:secure_url",
            "twitter:player",
            "twitter:player:stream",
        ],
    )
    if video_url and not _is_still_instagram_carousel(
        platform, media, carousel_has_video
    ):
        media["is_video"] = True
        add_signal("meta:video-url")

    if re.search(r"/(?:videos?|watch)/", url_l) or "fb.watch" in url_l:
        media["is_video"] = True
        add_signal("url:video")

    json_says_video = bool(
        re.search(r'"(?:is_video|isVideo)"\s*:\s*true', text_blob, re.IGNORECASE)
    )
    json_has_video_asset = bool(
        re.search(
            r'"(?:video_versions|video_url|playable_url|dash_manifest)"\s*:',
            text_blob,
            re.IGNORECASE,
        )
    )
    if (json_says_video or json_has_video_asset) and not _is_still_instagram_carousel(
        platform, media, carousel_has_video
    ):
        media["is_video"] = True
        add_signal("json:is_video" if json_says_video else "json:video")

    poster = ""
    if platform == "instagram":
        poster = _first_instagram_post_image(html or "", url)
    elif platform == "facebook":
        poster = _facebook_formatted_background_image(html or "", url)
    if not poster:
        poster = _first_meta_content_from_soup(
            soup,
            ["og:image", "og:image:secure_url", "twitter:image", "twitter:image:src"],
        )
    if poster and url:
        poster = urljoin(url, poster)
    media["poster_image"] = poster or ""

    if media["is_reel"]:
        media["kind"] = "reel"
    elif media["is_video"]:
        media["kind"] = "video"
    elif media["is_carousel"]:
        media["kind"] = "carousel"
    elif platform in {"instagram", "facebook", "threads", "twitter"}:
        media["kind"] = "post"

    return media


def _is_still_instagram_carousel(
    platform: str, media: dict[str, Any], carousel_has_video: bool
) -> bool:
    return (
        platform == "instagram"
        and media.get("is_carousel")
        and not media.get("is_reel")
        and not carousel_has_video
    )


def _instagram_carousel_has_video(items) -> bool:
    if not isinstance(items, list):
        return False
    return any(_instagram_media_is_video(item) for item in items)


def _instagram_sidecar_has_video(edges) -> bool:
    if not isinstance(edges, list):
        return False
    for edge in edges:
        node = edge.get("node") if isinstance(edge, dict) else None
        if _instagram_media_is_video(node):
            return True
    return False


def _instagram_media_is_video(media) -> bool:
    if not isinstance(media, dict):
        return False

    if media.get("is_video") is True or media.get("isVideo") is True:
        return True

    media_type = media.get("media_type") or media.get("__typename")
    if media_type in {2, "2", "GraphVideo", "XDTGraphVideo"}:
        return True

    product_type = str(media.get("product_type") or "").lower()
    if product_type in {"clips", "igtv", "video"}:
        return True

    return any(
        bool(media.get(key))
        for key in ("video_versions", "video_url", "playable_url", "dash_manifest")
    )


def _first_meta_content_from_soup(soup: BeautifulSoup, keys: list[str]) -> str:
    for key in keys:
        tag = soup.find("meta", attrs={"property": key})
        if tag and tag.get("content"):
            val = tag["content"].strip()
            if val:
                return val
        tag = soup.find("meta", attrs={"name": key})
        if tag and tag.get("content"):
            val = tag["content"].strip()
            if val:
                return val
    return ""


def _first_instagram_post_image(html: str, url: str) -> str:
    post = _find_instagram_post_object(html, url)
    if not isinstance(post, dict):
        return ""

    carousel = post.get("carousel_media")
    if isinstance(carousel, list) and carousel:
        img = _image_from_instagram_media(carousel[0])
        if img:
            return urljoin(url, img)

    img = _image_from_instagram_media(post)
    return urljoin(url, img) if img else ""


def _find_instagram_post_object(html: str, url: str):
    shortcode = _instagram_shortcode_from_url(url)
    if not shortcode:
        return None

    soup = BeautifulSoup(html or "", "html.parser")
    for script in soup.find_all("script"):
        text = (script.string or script.get_text() or "").strip()
        if not text or shortcode not in text:
            continue
        if not (text.startswith("{") or text.startswith("[")):
            continue

        try:
            data = json.loads(text)
        except Exception:
            continue

        found = _find_instagram_post_object_in_json(data, shortcode)
        if found:
            return found

    return None


def _find_instagram_post_object_in_json(data, shortcode: str):
    if isinstance(data, dict):
        if data.get("code") == shortcode:
            return data
        for value in data.values():
            found = _find_instagram_post_object_in_json(value, shortcode)
            if found:
                return found

    if isinstance(data, list):
        for item in data:
            found = _find_instagram_post_object_in_json(item, shortcode)
            if found:
                return found

    return None


def _instagram_shortcode_from_url(url: str) -> str:
    try:
        parts = [part for part in urlparse(url or "").path.split("/") if part]
    except Exception:
        return ""

    for marker in ("p", "reel", "reels", "tv"):
        if marker in parts:
            idx = parts.index(marker)
            if idx + 1 < len(parts):
                return parts[idx + 1]

    return ""


def _facebook_formatted_background_image(html: str, url: str) -> str:
    """
    Facebook colored-background text posts can expose post-scoped text metadata
    while their OG image points at the group/page cover. Prefer the story's own
    formatted-background asset when that exact post-rendering shape is present.
    """
    if not html or (
        "CometFeedStoryFormattedBackgroundMessageRenderingStrategy" not in html
        and "TextFormatImageBackground" not in html
    ):
        return ""

    metadata = _extract_json_object_after_key(html, "text_format_metadata")
    if not isinstance(metadata, dict):
        return ""

    candidates = [
        _nested_uri(metadata, ("background_image",)),
        _nested_uri(metadata, ("background", "image")),
        _nested_uri(metadata, ("portrait_background_image",)),
        _nested_uri(metadata, ("background", "portrait_image")),
    ]
    for candidate in candidates:
        if _looks_like_image_url(candidate):
            return urljoin(url, candidate)

    return ""


def _nested_uri(data, path: tuple[str, ...]) -> str:
    current = data
    for key in path:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)

    if isinstance(current, dict):
        val = current.get("uri") or current.get("url") or current.get("src")
        return val if isinstance(val, str) else ""

    return current if isinstance(current, str) else ""


def _first_instagram_carousel_image(soup: BeautifulSoup, url: str) -> str:
    for script in soup.find_all("script"):
        text = script.string or script.get_text() or ""

        media = _extract_json_array_after_key(text, "carousel_media")
        if media:
            img = _image_from_instagram_media(media[0])
            if img:
                return urljoin(url, img)

        sidecar = _extract_json_object_after_key(text, "edge_sidecar_to_children")
        if sidecar:
            img = _image_from_instagram_sidecar(sidecar)
            if img:
                return urljoin(url, img)

    return ""


def _extract_json_array_after_key(text: str, key: str):
    key_pos = text.find(f'"{key}"')
    if key_pos == -1:
        key_pos = text.find(key)
    if key_pos == -1:
        return None

    return _extract_json_after_marker(text, key_pos, "[", "]")


def _extract_json_object_after_key(text: str, key: str):
    key_pos = text.find(f'"{key}"')
    if key_pos == -1:
        key_pos = text.find(key)
    if key_pos == -1:
        return None

    return _extract_json_after_marker(text, key_pos, "{", "}")


def _extract_json_after_marker(text: str, key_pos: int, opener: str, closer: str):
    start = text.find(opener, key_pos)
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False

    for i in range(start, len(text)):
        char = text[i]

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except Exception:
                    return None

    return None


def _image_from_instagram_sidecar(sidecar) -> str:
    if not isinstance(sidecar, dict):
        return ""

    edges = sidecar.get("edges")
    if not isinstance(edges, list) or not edges:
        return ""

    node = edges[0].get("node") if isinstance(edges[0], dict) else None
    if not isinstance(node, dict):
        return ""

    return _image_from_instagram_media(node)


def _image_from_instagram_media(media) -> str:
    if not isinstance(media, dict):
        return ""

    image_versions = media.get("image_versions2")
    if isinstance(image_versions, dict):
        img = _first_candidate_url(image_versions.get("candidates"))
        if img:
            return img

    for key in ("display_resources", "thumbnail_resources"):
        img = _first_candidate_url(media.get(key))
        if img:
            return img

    for key in ("thumbnail_src", "display_url", "image_url", "url"):
        val = media.get(key)
        if _looks_like_image_url(val):
            return val

    return ""


def _first_candidate_url(candidates) -> str:
    if not isinstance(candidates, list):
        return ""

    for candidate in candidates:
        if isinstance(candidate, dict):
            val = candidate.get("url") or candidate.get("src")
        else:
            val = candidate

        if _looks_like_image_url(val):
            return val

    return ""


def _looks_like_image_url(val) -> bool:
    if not isinstance(val, str) or not val.strip():
        return False

    lower = val.lower()
    if lower.startswith("data:"):
        return False
    return not any(ext in lower for ext in (".mp4", ".mov", ".m3u8"))


def _looks_like_threads_chrome(text: str) -> bool:
    lower = (text or "").lower()
    if not lower:
        return False

    nav_hits = sum(
        phrase in lower
        for phrase in (
            "home search",
            "create notifications profile",
            "back thread",
            "like comment repost share",
            "log in or sign up for threads",
            "see what people are talking about",
            "instagram log in with username",
            "© 2026 threads",
            "threads terms",
        )
    )
    return nav_hits >= 2


# ---- PARAGRAPH-LIKE BLOCK (FALLBACK TEXT FOR SUMMARIZATION) ----
def extract_paragraph_like_block(html: str) -> str:
    """
    Fallback HTML block extractor for pages without good metadata.
    Prioritize character count for summarization (not word count).
    """
    soup = BeautifulSoup(html or "", "html.parser")

    # First: <main> or <article> if decently long
    for tag in ["main", "article"]:
        node = soup.find(tag)
        if node:
            text = node.get_text(separator=" ", strip=True)
            if len(text) >= 280:  # characters, not words
                return text

    # Second: divs with decent content
    candidates = []
    for div in soup.find_all("div"):
        txt = div.get_text(separator=" ", strip=True)
        if (
            280 <= len(txt) <= 3000
            and "block user" not in (txt.lower())
            and not _looks_like_threads_chrome(txt)
        ):
            candidates.append(txt)
    if candidates:
        return max(candidates, key=len)

    # Last: first 5 paragraphs
    paragraphs = soup.find_all("p")
    blob = " ".join(p.get_text(strip=True) for p in paragraphs[:5])
    return blob
