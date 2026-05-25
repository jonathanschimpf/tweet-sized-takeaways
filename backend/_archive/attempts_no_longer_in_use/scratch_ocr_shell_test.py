# IN ALL CAPS: DEBUGGING OCR PIPELINE LOCALLY

from backend.ocr_fallback import (
    extract_text_from_image,
    clean_extracted_text,
    summarize_with_bart,
    remove_hallucinated_brands,
)

# ✅ SET PATH TO EXISTING TEST IMAGE (CORRECTED)
IMAGE_PATH = "public/images/playwright/pytesseract-ocr-test.png"

# STEP 1: EXTRACT RAW OCR TEXT
raw_text = extract_text_from_image(IMAGE_PATH)
print("\n🧾 RAW OCR TEXT:\n", raw_text)

# STEP 2: CLEAN THE TEXT
cleaned = clean_extracted_text(raw_text)
print("\n🧹 CLEANED TEXT:\n", cleaned)

# STEP 3: SUMMARIZE
summary = summarize_with_bart(cleaned)
print("\n🪄 BART SUMMARY:\n", summary)

# STEP 4: REMOVE HALLUCINATIONS
final_output = remove_hallucinated_brands(summary)
print("\n❌ FINAL OUTPUT (NO CNN):\n", final_output)
