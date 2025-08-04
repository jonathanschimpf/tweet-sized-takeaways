# (HF RETRY LOOP) --> [INITIAL ➞ HF ➞ INITIAL ➞ HF ➞ ...] w/ SMART INSTAGRAM RETRIES

import asyncio
from .shared_hf import get_best_summary, is_hallucinated_summary

MAX_RETRIES = 4
MIN_VALID_LENGTH = 10  # ALLOW short, real summaries

# STRINGS TO TREAT AS SHELL CONTENT (TRIGGERS RETRY)
KNOWN_HALLUCINATED_CAPTIONS = {"Instagram", "Facebook", "Threads", ""}

async def reliable_hf_summary(text: str) -> str:
    attempt = 0
    while attempt < MAX_RETRIES:
        summary = await get_best_summary(text)
        cleaned = summary.strip()

        if (
            cleaned not in KNOWN_HALLUCINATED_CAPTIONS
            and not is_hallucinated_summary(cleaned)
            and len(cleaned) > MIN_VALID_LENGTH
        ):
            return cleaned

        print(f"⏳ Retry #{attempt + 1} — Unusable summary: '{cleaned}'. Trying again...")
        await asyncio.sleep(1.5)  # Backoff delay
        attempt += 1

    return "🧨 Hugging Face couldn't find enough readable text after several tries."
