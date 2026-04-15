"""Playwright-based Kleinanzeigen posting logic."""

import asyncio
import random
import logging
from pathlib import Path

from playwright.async_api import Page

from config import config
from ka_selectors import SELECTORS

logger = logging.getLogger(__name__)


async def post_listing(page: Page, listing_data: dict) -> dict:
    """
    Post a single listing to Kleinanzeigen using Playwright.

    Args:
        page: Playwright page object
        listing_data: Dict with title, description, price, zip_code, images, etc.

    Returns:
        Dict with status, url, screenshot_path
    """
    listing_id = listing_data["listing_id"]
    screenshots_dir = Path(config.SCREENSHOTS_DIR) / listing_id
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Navigate to new listing page
        logger.info(f"Navigating to new listing form...")
        await page.goto(SELECTORS["new_listing_url"], timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=15000)
        await _random_delay(1, 3)

        # Take screenshot of initial form
        await page.screenshot(path=str(screenshots_dir / "01_form_loaded.png"))

        # 2. Fill title
        logger.info(f"Filling title: {listing_data['title'][:50]}...")
        title_input = page.locator(SELECTORS["title_input"])
        await title_input.click()
        await _random_delay(0.3, 0.8)
        await title_input.fill("")
        await page.type(SELECTORS["title_input"], listing_data["title"], delay=50)
        await _random_delay(0.5, 1)

        # 3. Fill description
        logger.info("Filling description...")
        desc_input = page.locator(SELECTORS["description_input"])
        await desc_input.click()
        await _random_delay(0.3, 0.8)
        await page.type(SELECTORS["description_input"], listing_data["description"], delay=30)
        await _random_delay(0.5, 1)

        # 4. Fill price
        logger.info(f"Setting price: €{listing_data['price']}")
        price_input = page.locator(SELECTORS["price_input"])
        await price_input.click()
        await _random_delay(0.3, 0.5)
        await price_input.fill(str(int(listing_data["price"])))
        await _random_delay(0.3, 0.8)

        # Select price type (fixed)
        try:
            await page.click(SELECTORS["price_type_fixed"])
        except Exception:
            logger.warning("Could not click fixed price type, may be default")

        # 5. Upload images
        logger.info(f"Uploading {len(listing_data['images'])} images...")
        for i, img in enumerate(listing_data["images"]):
            img_path = img["path"]
            if not Path(img_path).exists():
                logger.warning(f"Image not found: {img_path}")
                continue

            try:
                file_input = page.locator(SELECTORS["file_input"]).first
                await file_input.set_input_files(img_path)
                await _random_delay(2, 4)  # Wait for upload
                logger.info(f"  Uploaded image {i+1}/{len(listing_data['images'])}")
            except Exception as e:
                logger.warning(f"Failed to upload image {i}: {e}")

        await page.screenshot(path=str(screenshots_dir / "02_form_filled.png"))

        # 6. Fill ZIP code
        logger.info(f"Setting ZIP: {listing_data['zip_code']}")
        zip_input = page.locator(SELECTORS["zip_input"])
        await zip_input.click()
        await _random_delay(0.3, 0.5)
        await zip_input.fill(listing_data["zip_code"])
        await _random_delay(1, 2)

        # 7. Screenshot before submit
        await page.screenshot(path=str(screenshots_dir / "03_pre_submit.png"))

        # 8. Submit (or dry-run stop)
        if config.DRY_RUN:
            logger.info("DRY RUN — skipping submit")
            return {
                "status": "posted",
                "url": "dry-run://no-url",
                "screenshot_path": str(screenshots_dir / "03_pre_submit.png"),
            }

        logger.info("Submitting listing...")
        await page.click(SELECTORS["submit_button"])
        await page.wait_for_load_state("networkidle", timeout=30000)
        await _random_delay(2, 4)

        # 9. Screenshot after submit
        await page.screenshot(path=str(screenshots_dir / "04_post_submit.png"))

        # 10. Check for success
        result_url = page.url
        logger.info(f"Listing posted. URL: {result_url}")

        return {
            "status": "posted",
            "url": result_url,
            "screenshot_path": str(screenshots_dir / "04_post_submit.png"),
        }

    except Exception as e:
        error_screenshot = str(screenshots_dir / "error.png")
        try:
            await page.screenshot(path=error_screenshot)
        except Exception:
            pass

        logger.error(f"Posting failed for {listing_id}: {e}")
        return {
            "status": "failed",
            "url": None,
            "screenshot_path": error_screenshot,
            "error": str(e),
        }


async def _random_delay(min_sec: float, max_sec: float):
    """Sleep for a random duration to mimic human behavior."""
    await asyncio.sleep(random.uniform(min_sec, max_sec))
