"""Kleinanzeigen browser session manager."""

import logging
from pathlib import Path

from playwright.async_api import BrowserContext, Playwright

from config import config
from ka_selectors import SELECTORS

logger = logging.getLogger(__name__)


async def create_browser_context(playwright: Playwright) -> BrowserContext:
    """
    Create a Playwright browser context with session persistence.
    Loads existing session if available.
    """
    browser = await playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox"],
    )

    session_path = Path(config.SESSION_PATH)
    if session_path.exists():
        logger.info("Loading existing browser session...")
        context = await browser.new_context(
            storage_state=str(session_path),
            locale="de-DE",
            timezone_id="Europe/Berlin",
        )
    else:
        logger.info("No existing session found, creating new context...")
        context = await browser.new_context(
            locale="de-DE",
            timezone_id="Europe/Berlin",
        )

    return context


async def check_session_valid(context: BrowserContext) -> bool:
    """Check if the current session is still logged in."""
    page = await context.new_page()
    try:
        await page.goto(SELECTORS["account_page"], timeout=15000)
        await page.wait_for_load_state("networkidle", timeout=10000)

        # Check if we were redirected to login
        login_el = await page.query_selector(SELECTORS["login_indicator"])
        if login_el:
            logger.warning("Session expired — login required.")
            return False

        logger.info("Session is valid.")
        return True
    except Exception as e:
        logger.error(f"Session check failed: {e}")
        return False
    finally:
        await page.close()


async def save_session(context: BrowserContext):
    """Save the current browser session state."""
    session_path = Path(config.SESSION_PATH)
    session_path.parent.mkdir(parents=True, exist_ok=True)
    await context.storage_state(path=str(session_path))
    logger.info("Browser session saved.")
