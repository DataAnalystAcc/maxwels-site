"""Playwright-based Kleinanzeigen posting logic."""

import asyncio
import random
import logging
from pathlib import Path

from playwright.async_api import Page

from config import config

logger = logging.getLogger(__name__)

# Maps keywords (checked against item_category + item_name + title) → category click path
CATEGORY_PATHS = {
    "LEGO":          ["Familie, Kind & Baby", "Spielzeug", "LEGO & Duplo"],
    "Duplo":         ["Familie, Kind & Baby", "Spielzeug", "LEGO & Duplo"],
    "Playmobil":     ["Familie, Kind & Baby", "Spielzeug", "Playmobil"],
    "Barbie":        ["Familie, Kind & Baby", "Spielzeug", "Barbie & Co"],
    "Brettspiel":    ["Familie, Kind & Baby", "Spielzeug", "Gesellschaftsspiele"],
    "Spielzeug":     ["Familie, Kind & Baby", "Spielzeug", "Weiteres Spielzeug"],
    "Elektronik":    ["Elektronik"],
    "Laptop":        ["Elektronik"],
    "Handy":         ["Elektronik"],
    "Smartphone":    ["Elektronik"],
    "Tablet":        ["Elektronik"],
    "Kamera":        ["Elektronik"],
    "Mode":          ["Mode & Beauty"],
    "Kleidung":      ["Mode & Beauty"],
    "Schuhe":        ["Mode & Beauty"],
    "Bücher":        ["Musik, Filme & Bücher"],
    "Musik":         ["Musik, Filme & Bücher"],
    "DVD":           ["Musik, Filme & Bücher"],
    "Möbel":         ["Haus & Garten"],
    "Haushalt":      ["Haus & Garten"],
    "Sport":         ["Freizeit, Hobby & Nachbarschaft"],
    "Fahrrad":       ["Auto, Rad & Boot"],
    "Auto":          ["Auto, Rad & Boot"],
}


async def _click_category_label(page: Page, label: str):
    """
    Click a category label inside the Kleinanzeigen category wizard.
    Scoped to main content area to avoid hitting sidebar navigation links.
    """
    # Try multiple container selectors — Kleinanzeigen uses different layouts
    selectors = [
        f"#postad-category-path li:has-text('{label}')",
        f".CategoryBox li:has-text('{label}')",
        f"main li:has-text('{label}')",
        f"[class*='categorybox'] li:has-text('{label}')",
        f"[class*='CategoryList'] li:has-text('{label}')",
        f"[class*='category-list'] li:has-text('{label}')",
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible():
                await loc.click(timeout=5000)
                logger.info(f"  Clicked '{label}' via: {sel}")
                return
        except Exception:
            continue

    # Last resort: find all <li> elements containing the label text,
    # skip any that are inside a <nav> or <aside> element
    items = await page.locator(f"li:has-text('{label}')").all()
    for item in items:
        try:
            # Skip sidebar/nav elements
            tag = await page.evaluate("el => el.closest('nav, aside, header') ? 'skip' : 'ok'", item)
            if tag == "skip":
                continue
            if await item.is_visible():
                await item.click(timeout=5000)
                logger.info(f"  Clicked '{label}' via fallback li scan")
                return
        except Exception:
            continue

    logger.warning(f"  Could not find clickable element for '{label}'")


async def _select_category(page: Page, listing_data: dict):
    """Click 'Wähle deine Kategorie' then navigate the wizard without leaving the form."""
    # Click the inline category link
    try:
        await page.locator("a:has-text('Wähle deine Kategorie'), span:has-text('Wähle deine Kategorie')").first.click(timeout=5000)
        logger.info("Clicked 'Wähle deine Kategorie'")
        await _random_delay(0.5, 1)
    except Exception:
        return

    # Wait for wizard
    try:
        await page.wait_for_selector("text=Kategorie auswählen", timeout=5000)
    except Exception:
        return

    # Determine path
    search_text = " ".join(filter(None, [
        listing_data.get("item_category", ""),
        listing_data.get("item_name", ""),
        listing_data.get("title", ""),
    ])).lower()

    path = None
    for keyword, cat_path in CATEGORY_PATHS.items():
        if keyword.lower() in search_text:
            path = cat_path
            break

    if not path:
        logger.warning(f"No category path for: '{search_text[:60]}' — using Freizeit default")
        path = ["Freizeit, Hobby & Nachbarschaft"]

    logger.info(f"Category path: {' → '.join(path)}")

    for i, label in enumerate(path):
        await _click_category_label(page, label)
        await _random_delay(0.8, 1.5)
        # Wait briefly for next column to load
        try:
            await page.wait_for_load_state("load", timeout=5000)
        except Exception:
            pass

    await _random_delay(0.5, 1)

    # Click "Weiter" to confirm category selection and return to the form
    try:
        weiter = page.locator("button:has-text('Weiter'), a:has-text('Weiter')").first
        if await weiter.count() > 0 and await weiter.is_visible():
            await weiter.click(timeout=5000)
            logger.info("Clicked 'Weiter' to confirm category")
            await page.wait_for_load_state("load", timeout=15000)
        else:
            logger.warning("'Weiter' button not found after category selection")
    except Exception as e:
        logger.warning(f"Could not click Weiter: {e}")

    await _random_delay(0.5, 1)


async def post_listing(page: Page, listing_data: dict) -> dict:
    """Post a listing to Kleinanzeigen. Returns dict with status, url, screenshot_path."""
    listing_id = listing_data.get("listing_id")
    if not listing_id:
        raise ValueError(f"Missing listing_id in payload")

    screenshots_dir = Path(config.SCREENSHOTS_DIR) / listing_id
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    try:
        # ── Step 1: Homepage → Inserieren → form ─────────────────────────────
        logger.info("Navigating to homepage...")
        await page.goto("https://www.kleinanzeigen.de/", timeout=30000)
        await page.wait_for_load_state("load", timeout=15000)

        # Cookie banner
        try:
            await page.locator("button:has-text('Alle akzeptieren')").first.click(timeout=5000)
            logger.info("Accepted cookie banner")
            await _random_delay(0.5, 1)
        except Exception:
            pass

        logger.info("Clicking Inserieren...")
        await page.locator("a:has-text('Inserieren'), button:has-text('Inserieren')").first.click(timeout=10000)
        await page.wait_for_load_state("load", timeout=15000)
        await _random_delay(0.5, 1)

        # Wait for form
        await page.wait_for_selector("text=Anzeigendetails", timeout=15000)
        await _random_delay(0.5, 1)
        await page.screenshot(path=str(screenshots_dir / "01_form.png"))
        logger.info(f"Form loaded. URL: {page.url}")

        # ── Step 2: Fill Titel ────────────────────────────────────────────────
        logger.info(f"Filling title: {listing_data['title'][:60]}...")
        await page.get_by_label("Titel").fill(listing_data["title"])
        await _random_delay(0.5, 1)

        # ── Step 3: Select category ───────────────────────────────────────────
        await _select_category(page, listing_data)

        # After category wizard, wait for form fields to be ready again
        await page.wait_for_selector("text=Preis", timeout=15000)
        await _random_delay(0.5, 1)
        await page.screenshot(path=str(screenshots_dir / "02_after_category.png"))

        # ── Step 4: Fill Preis ────────────────────────────────────────────────
        price = str(int(listing_data.get("price") or 0))
        logger.info(f"Setting price: €{price}")
        try:
            await page.get_by_label("Preis").first.fill(price, timeout=5000)
        except Exception:
            await page.locator("#pstad-price, input[name='price']").first.fill(price)
        await _random_delay(0.3, 0.6)

        # ── Step 5: Fill Beschreibung ─────────────────────────────────────────
        logger.info("Filling description...")
        try:
            await page.get_by_label("Beschreibung").first.fill(listing_data["description"], timeout=5000)
        except Exception:
            await page.locator("#pstad-descrptn, textarea[name='description']").first.fill(listing_data["description"])
        await _random_delay(0.5, 1)

        # ── Step 6: Upload images ─────────────────────────────────────────────
        images = listing_data.get("images", [])
        logger.info(f"Uploading {len(images)} images...")
        uploaded = 0
        for i, img in enumerate(images):
            img_path = img.get("path", "")
            if not Path(img_path).exists():
                logger.warning(f"  Image {i+1} not found: {img_path}")
                continue
            try:
                await page.locator("input[type='file']").first.set_input_files(img_path)
                await _random_delay(2, 3)
                uploaded += 1
                logger.info(f"  Uploaded {i+1}/{len(images)}: {Path(img_path).name}")
            except Exception as e:
                logger.warning(f"  Failed to upload image {i+1}: {e}")

        logger.info(f"Uploaded {uploaded}/{len(images)} images")
        await page.screenshot(path=str(screenshots_dir / "03_form_filled.png"))

        # ── Step 7: Submit ────────────────────────────────────────────────────
        if config.DRY_RUN:
            logger.info("DRY RUN — skipping submit")
            return {
                "status": "posted",
                "url": "dry-run://no-url",
                "screenshot_path": str(screenshots_dir / "03_form_filled.png"),
            }

        logger.info("Clicking 'Anzeige aufgeben'...")
        await page.get_by_role("button", name="Anzeige aufgeben").click(timeout=15000)
        await page.wait_for_load_state("load", timeout=30000)
        await _random_delay(2, 3)

        await page.screenshot(path=str(screenshots_dir / "04_submitted.png"))
        result_url = page.url
        logger.info(f"Submitted. URL: {result_url}")

        return {
            "status": "posted",
            "url": result_url,
            "screenshot_path": str(screenshots_dir / "04_submitted.png"),
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
    await asyncio.sleep(random.uniform(min_sec, max_sec))
