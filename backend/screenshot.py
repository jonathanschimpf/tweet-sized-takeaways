import os
import asyncio
from backend.pathlib import Path
from backend.playwright.async_api import async_playwright

# Output directory for screenshots
SCREENSHOT_DIR = Path(__file__).parent / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)


async def take_screenshot(url: str, filename: str = "screenshot.png") -> str:
    """
    Capture a full-page screenshot of the given URL.
    Returns the file path of the saved image.
    """
    filepath = SCREENSHOT_DIR / filename

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        await page.goto(url, wait_until="networkidle")
        await page.screenshot(path=str(filepath), full_page=True)
        await browser.close()

    return str(filepath)


# Debug CLI runner
if __name__ == "__main__":
    test_url = "https://example.com"
    out_file = "testshot.png"
    print("📸 Capturing screenshot...")

    asyncio.run(take_screenshot(test_url, out_file))
    print(f"✅ Saved to: {SCREENSHOT_DIR / out_file}")
