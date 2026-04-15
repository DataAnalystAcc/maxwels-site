"""Pricing engine — computes recommended price from comparables."""

import math
import statistics
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Condition adjustment multipliers (relative to median)
CONDITION_MULTIPLIERS = {
    "new": 1.10,
    "like_new": 1.00,
    "good": 0.90,
    "fair": 0.75,
    "poor": 0.50,
}


@dataclass
class PriceRecommendation:
    """Result of the pricing engine."""
    price: Optional[float]
    confidence: str  # high, medium, low, none
    reasoning: str
    comp_count: int
    median: Optional[float] = None
    range_low: Optional[float] = None
    range_high: Optional[float] = None


def _percentile(data: list[float], p: int) -> float:
    """Compute the p-th percentile of a sorted list."""
    if not data:
        return 0.0
    k = (len(data) - 1) * (p / 100)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return data[int(k)]
    return data[f] * (c - k) + data[c] * (k - f)


def round_to_nice(price: float) -> float:
    """Round to psychologically appealing price points."""
    if price <= 0:
        return 0
    elif price <= 5:
        return round(price)
    elif price <= 20:
        return round(price / 5) * 5
    elif price <= 100:
        return round(price / 5) * 5
    elif price <= 500:
        return round(price / 10) * 10
    else:
        return round(price / 25) * 25


def compute_similarity(our_item_name: str, candidate_title: str) -> float:
    """
    Compute Jaccard similarity between item name and candidate title.
    Returns 0.0–1.0.
    """
    our_words = set(our_item_name.lower().split())
    their_words = set(candidate_title.lower().split())

    if not our_words or not their_words:
        return 0.0

    intersection = len(our_words & their_words)
    union = len(our_words | their_words)

    return intersection / union if union > 0 else 0.0


def filter_and_score_candidates(
    candidates: list[dict],
    item_name: str,
    min_similarity: float = 0.2,
) -> list[dict]:
    """
    Score candidates by similarity and filter out weak matches and outliers.

    Each candidate dict should have: title, price, price_type
    Returns candidates with added: similarity_score, is_comparable
    """
    # Step 1: score all candidates
    for c in candidates:
        c["similarity_score"] = compute_similarity(item_name, c.get("title", ""))

    # Step 2: filter by minimum similarity
    viable = [c for c in candidates if c["similarity_score"] >= min_similarity]

    # Step 3: filter out free items unless majority are free
    priced = [c for c in viable if c.get("price") and c["price"] > 0]
    free = [c for c in viable if c.get("price_type") == "free"]

    if len(free) > len(priced):
        # Most items are free — keep all
        scored = viable
    else:
        scored = priced

    # Step 4: remove outliers (>3x median or <median/5)
    prices = sorted([c["price"] for c in scored if c.get("price") and c["price"] > 0])
    if len(prices) >= 3:
        median = statistics.median(prices)
        scored = [
            c for c in scored
            if not c.get("price") or (c["price"] <= median * 3 and c["price"] >= median / 5)
        ]

    # Mark comparables
    for c in candidates:
        c["is_comparable"] = c in scored

    return candidates


def compute_price(
    prices: list[float],
    strategy: str = "competitive",
    condition: str = "good",
) -> PriceRecommendation:
    """
    Compute recommended price from a list of comparable prices.

    Args:
        prices: list of comparable prices (already filtered)
        strategy: 'fast_sale', 'competitive', or 'fair'
        condition: item condition for adjustment
    """
    valid_prices = sorted([p for p in prices if p > 0])

    if not valid_prices:
        return PriceRecommendation(
            price=None,
            confidence="none",
            reasoning="No comparables found. Manual pricing required.",
            comp_count=0,
        )

    # Confidence based on sample size
    n = len(valid_prices)
    if n < 3:
        confidence = "low"
    elif n < 6:
        confidence = "medium"
    else:
        confidence = "high"

    median = statistics.median(valid_prices)
    p25 = _percentile(valid_prices, 25)
    p75 = _percentile(valid_prices, 75)

    # Apply condition adjustment
    condition_mult = CONDITION_MULTIPLIERS.get(condition, 0.9)
    adjusted_median = median * condition_mult

    # Apply strategy
    if strategy == "fast_sale":
        raw_price = adjusted_median * 0.80  # 20% below adjusted median
        reasoning = (
            f"Fast sale: 20% below adjusted median. "
            f"Median={median:.0f}€, Condition adj={condition_mult}x, "
            f"P25={p25:.0f}€–P75={p75:.0f}€ ({n} comps)"
        )
    elif strategy == "competitive":
        raw_price = adjusted_median * 0.90  # 10% below adjusted median
        reasoning = (
            f"Competitive: 10% below adjusted median. "
            f"Median={median:.0f}€, Condition adj={condition_mult}x, "
            f"P25={p25:.0f}€–P75={p75:.0f}€ ({n} comps)"
        )
    elif strategy == "fair":
        raw_price = adjusted_median  # at adjusted median
        reasoning = (
            f"Fair market: at adjusted median. "
            f"Median={median:.0f}€, Condition adj={condition_mult}x, "
            f"P25={p25:.0f}€–P75={p75:.0f}€ ({n} comps)"
        )
    else:
        raw_price = adjusted_median * 0.90
        reasoning = "Default competitive pricing"

    recommended = round_to_nice(raw_price)

    # Ensure minimum price of €1
    if recommended < 1 and valid_prices:
        recommended = 1.0

    return PriceRecommendation(
        price=recommended,
        confidence=confidence,
        reasoning=reasoning,
        comp_count=n,
        median=round(median, 2),
        range_low=round(p25, 2),
        range_high=round(p75, 2),
    )
