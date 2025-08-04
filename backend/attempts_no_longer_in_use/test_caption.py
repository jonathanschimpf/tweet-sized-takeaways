# ✅ TEST FILE USING LLaVA FROM seelikeahuman.py
from seelikeahuman import caption_image
import os

if __name__ == "__main__":
    # ✅ POINT TO A PLAYWRIGHT-GENERATED SCREENSHOT
    img_path = "../public/images/playwright/huggingface-web-reading-test.png"

    if not os.path.exists(img_path):
        raise FileNotFoundError(f"❌ Image not found at: {img_path}")

    print(f"\n🧠 LLaVA is generating caption for:\n{img_path}")

    try:
        caption = caption_image(img_path)
        print("\n🧠 GENERATED CAPTION:\n")
        print(caption)
    except Exception as e:
        print("\n❌ LLaVA Captioning Failed:\n")
        print(e)
