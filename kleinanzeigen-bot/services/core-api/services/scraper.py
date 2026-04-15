"""Kleinanzeigen search result scraper for pricing comparables."""

import re
import logging
import asyncio
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

KLEINANZEIGEN_SEARCH_URL = "https://www.kleinanzeigen.de/s-{query}/k0"

# Respectful delay between search requests
SCRAPE_DELAY_SECONDS = 5

# Common headers to appear as a normal browser
SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


@dataclass
class SearchResult:
    """One search result from Kleinanzeigen."""
    title: str
    price: Optional[float] = None
    price_type: str = "fixed"  # fixed, vb, free
    url: str = ""
    location: str = ""
    posted_date: Optional[str] = None


def _parse_price(price_text: str) -> tuple[Optional[float], str]:
    """Parse price text into (amount, type)."""
    text = price_text.strip().lower()

    if "zu verschenken" in text:
        return 0.0, "free"

    # Extract numeric price
    # Handle formats like "25 €", "25€", "1.250 €", "25 € VB"
    price_match = re.search(r"([\d.,]+)\s*€", text)
    if not price_match:
        return None, "unknown"

    price_str = price_match.group(1)
    # German number format: 1.250,50 → 1250.50
    price_str = price_str.replace(".", "").replace(",", ".")
    try:
        price = float(price_str)
    except ValueError:
        return None, "unknown"

    price_type = "vb" if "vb" in text else "fixed"
    return price, price_type


async def scrape_search_results(
    query: str,
    max_results: int = 20,
) -> list[SearchResult]:
    """
    Scrape Kleinanzeigen search results for a given query.

    Returns up to max_results SearchResult objects.
    """
    encoded_query = quote_plus(query)
    url = KLEINANZEIGEN_SEARCH_URL.format(query=encoded_query)

    logger.info(f"Scraping Kleinanzeigen search: {url}")

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=SCRAPE_HEADERS)
            response.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(f"Search request failed for '{query}': {e}")
        return []

    soup = BeautifulSoup(response.text, "lxml")
    results = []

    # Kleinanzeigen uses article elements or ad-listitem for search results
    # Try multiple selector strategies for resilience
    ad_items = soup.select("article.aditem") or soup.select("[class*='aditem']")

    if not ad_items:
        # Fallback: look for list items with ad-like structure
        ad_items = soup.select("li[data-adid]")

    for item in ad_items[:max_results]:
        try:
            # Title
            title_el = (
                item.select_one(".aditem-main--middle--title")
                or item.select_one("a[class*='title']")
                or item.select_one("h2 a")
                or item.select_one("a")
            )
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title:
                continue

            # URL
            link = title_el.get("href", "")
            if link and not link.startswith("http"):
                link = f"https://www.kleinanzeigen.de{link}"

            # Price
            price_el = (
                item.select_one(".aditem-main--middle--price-shipping--price")
                or item.select_one("[class*='price']")
            )
            price = None
            price_type = "unknown"
            if price_el:
                price, price_type = _parse_price(price_el.get_text())

            # Location
            location_el = item.select_one(".aditem-main--top--left") or item.select_one("[class*='location']")
            location = location_el.get_text(strip=True) if location_el else ""

            results.append(SearchResult(
                title=title,
                price=price,
                price_type=price_type,
                url=link,
                location=location,
            ))

        except Exception as e:
            logger.warning(f"Failed to parse search result: {e}")
            continue

    logger.info(f"Scraped {len(results)} results for '{query}'")
    return results


async def scrape_multiple_queries(
    queries: list[str],
    max_results_total: int = 20,
) -> list[SearchResult]:
    """
    Scrape multiple search queries and deduplicate results.
    Adds a delay between queries to be respectful.
    """
    all_results = []
    seen_urls = set()

    for i, query in enumerate(queries):
        if len(all_results) >= max_results_total:
            break

        if i > 0:
            await asyncio.sleep(SCRAPE_DELAY_SECONDS)

        remaining = max_results_total - len(all_results)
        results = await scrape_search_results(query, max_results=remaining + 5)

        for r in results:
            if r.url not in seen_urls and len(all_results) < max_results_total:
                seen_urls.add(r.url)
                all_results.append(r)

    return all_results
