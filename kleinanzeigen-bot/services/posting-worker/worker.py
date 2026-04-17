"""Posting Worker — polls Redis queue and posts listings via Playwright."""

import json
import asyncio
import random
import logging

import httpx
import redis.asyncio as aioredis
from playwright.async_api import async_playwright

from config import config
from session_manager import create_browser_context, check_session_valid, save_session
from poster import post_listing

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def report_result(listing_id: str, result: dict, attempt: int):
    """Report posting result back to the Core API."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.patch(
            f"{config.API_BASE_URL}/api/posting/{listing_id}/posting-result",
            json={
                "status": result["status"],
                "url": result.get("url"),
                "screenshot_path": result.get("screenshot_path"),
                "error_message": result.get("error"),
                "attempt": attempt,
            },
        )


async def get_posting_payload(listing_id: str) -> dict:
    """Fetch listing data from Core API."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{config.API_BASE_URL}/api/posting/{listing_id}/posting-payload"
        )
        response.raise_for_status()
        return response.json()


async def run():
    """Main worker loop — poll Redis, post sequentially."""
    logger.info("Posting worker starting...")
    logger.info(f"DRY_RUN: {config.DRY_RUN}")
    logger.info(f"Delay range: {config.POSTING_DELAY_MIN_SEC}–{config.POSTING_DELAY_MAX_SEC}s")

    r = aioredis.from_url(config.REDIS_URL, decode_responses=True)

    async with async_playwright() as playwright:
        context = await create_browser_context(playwright)
        items_posted = 0

        while True:
            try:
                # Block-pop from Redis queue (wait up to 30s)
                job_raw = await r.brpop(config.QUEUE_KEY, timeout=30)
                if not job_raw:
                    continue

                _, job_json = job_raw
                job = json.loads(job_json)
                listing_id = job["listing_id"]
                attempt = job.get("attempt", 1)

                logger.info(f"=== Posting job: listing={listing_id}, attempt={attempt} ===")

                # Check session before posting
                if items_posted == 0 or items_posted % 5 == 0:
                    session_valid = await check_session_valid(context)
                    if not session_valid:
                        logger.error("Session expired! Pausing worker. Please re-login.")
                        # TODO: send Telegram notification
                        await asyncio.sleep(300)  # Wait 5 min and retry
                        continue

                # Fetch listing data
                try:
                    listing_data = await get_posting_payload(listing_id)
                except Exception as e:
                    logger.error(f"Failed to fetch listing data: {e}")
                    await report_result(listing_id, {
                        "status": "failed",
                        "error": f"Failed to fetch listing data: {e}",
                    }, attempt)
                    continue

                # Post the listing
                page = await context.new_page()
                try:
                    result = await post_listing(page, listing_data)
                    await report_result(listing_id, result, attempt)

                    if result["status"] == "posted":
                        items_posted += 1
                        logger.info(f"✅ Successfully posted listing {listing_id} "
                                    f"({items_posted} total this session)")
                        # Save session after each successful post
                        await save_session(context)
                    else:
                        logger.warning(f"❌ Failed to post listing {listing_id}: "
                                       f"{result.get('error', 'unknown')}")

                except Exception as e:
                    logger.error(f"Unexpected error posting {listing_id}: {e}")
                    await report_result(listing_id, {
                        "status": "failed",
                        "error": str(e),
                    }, attempt)
                finally:
                    await page.close()

                # Check max per session
                if items_posted >= config.POSTING_MAX_PER_SESSION:
                    logger.info(f"Reached max posts per session ({config.POSTING_MAX_PER_SESSION}). "
                                "Pausing for 1 hour.")
                    await asyncio.sleep(3600)
                    items_posted = 0

                # Random delay between posts
                delay = random.uniform(
                    config.POSTING_DELAY_MIN_SEC,
                    config.POSTING_DELAY_MAX_SEC,
                )
                logger.info(f"Waiting {delay:.0f}s before next post...")
                await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(run())
