# ✅ shared_hf.py
import os
import re
import sys
import hashlib
import aiohttp
from dotenv import load_dotenv
from .bartshallucinationblacklist import HALLUCINATION_BLURBS

load_dotenv()

HF_API_URL = "https://api-inference.huggingface.co/models/tuner007/pegasus_paraphrase"


def log_hf_prompt(prompt: str):
    print("\n📝 HF RAW PROMPT >>>")
    print(prompt)
    print("<<< END PROMPT\n")
    sys.stdout.flush()


def is_hallucinated_summary(summary: str) -> bool:
    normalized = summary.lower().strip()
    return any(phrase.lower() in normalized for phrase in HALLUCINATION_BLURBS)


def trim_to_tweet(summary: str, limit: int = 280) -> str:
    if len(summary) <= limit:
        return summary
    trimmed = summary[:277].rsplit(" ", 1)[0].strip()
    return trimmed + "..."


async def get_best_summary(text: str) -> str:
    if not text.strip():
        print("🚫 No usable text found — skipping HF.")
        return "🚫 There's honestly nothing to summarize on that link. 🚫"

    prompt = text.strip()[:1024]
    log_hf_prompt(prompt)

    input_hash = hashlib.md5(prompt.encode("utf-8")).hexdigest()
    print(f"🔍 HF INPUT HASH: {input_hash}")
    print(f"🔢 HF INPUT LENGTH: {len(prompt)}")
    sys.stdout.flush()

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
                    summary = result[0]["summary_text"]
                    if is_hallucinated_summary(summary):
                        print(
                            "🚫 BLOCKED HALLUCINATED SUMMARY — returning prompt instead."
                        )
                        return trim_to_tweet(prompt)
                    return trim_to_tweet(summary)
                return "🤖 Hugging Face response malformed."
            return f"🛑 Hugging Face error {resp.status}: {await resp.text()}"
