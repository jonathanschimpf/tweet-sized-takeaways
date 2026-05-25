# IN ALL CAPS: OCR FALLBACK MODULE FOR TEXT EXTRACTION AND SUMMARIZATION

import re
from PIL import Image
import pytesseract
from transformers import pipeline


# === OCR STEP: EXTRACT TEXT FROM AN IMAGE ===
def extract_text_from_image(image_path: str) -> str:
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image)
    return text.strip()


# === BASIC CLEANUP: REMOVE JUNK CHARACTERS AND WHITESPACE ===
def clean_extracted_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# === BART SUMMARIZATION (IF NEEDED) ===
summarizer = pipeline("summarization", model="facebook/bart-large-cnn", device=-1)


def summarize_with_bart(text: str) -> str:
    prompt = text[:1024]
    if len(prompt) < 50:
        return prompt  # TOO SHORT — SKIP SUMMARIZATION
    summary = summarizer(prompt, max_length=80, min_length=20, do_sample=False)[0][
        "summary_text"
    ]
    return summary.strip()


# === FINAL FILTER TO REMOVE UNWANTED BRANDS, REPETITIONS ===
def remove_hallucinated_brands(summary: str) -> str:
    summary = re.sub(r"\bCNN\.com.*?(\.|\n|$)", "", summary, flags=re.IGNORECASE)
    summary = re.sub(r"\b(mm A)+", "", summary, flags=re.IGNORECASE)  # REMOVE 'mm A'
    summary = re.sub(
        r"(This is an OCR test.*?)\1+", r"\1", summary
    )  # DEDUP repeated lines
    return summary.strip()
