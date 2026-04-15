"""OpenRouter LLM client for item identification and draft generation."""

import json
import base64
import logging
from pathlib import Path
from typing import Optional

import httpx

from config import settings
from schemas import IdentificationResult

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """You identify household items for resale on Kleinanzeigen.de.
Respond with valid JSON only. No markdown fences. No explanation.
Write the title and description in German.
The title should be concise (max 100 chars) and include brand, model, color, and key dimensions if visible.
The description should be 2-4 sentences, mention condition, and highlight key selling points.
Generate search_terms in German that a buyer would use to find this item on Kleinanzeigen."""


def _encode_image(path: str) -> str:
    """Read image file and return base64-encoded string."""
    data = Path(path).read_bytes()
    return base64.b64encode(data).decode("utf-8")


def _select_images(image_paths: list[str], max_images: int = 4) -> list[str]:
    """Pick a representative subset of images (diverse angles)."""
    n = len(image_paths)
    if n <= max_images:
        return image_paths

    # Pick first, last, and evenly spaced middle images
    indices = [0]
    if n > 2:
        step = (n - 1) / (max_images - 1)
        for i in range(1, max_images - 1):
            indices.append(round(i * step))
    indices.append(n - 1)

    # Deduplicate and sort
    indices = sorted(set(indices))[:max_images]
    return [image_paths[i] for i in indices]


async def identify_and_draft(
    image_paths: list[str],
    user_note: Optional[str] = None,
    model: Optional[str] = None,
) -> tuple[IdentificationResult, str, dict]:
    """
    Send images + optional note to LLM, get structured identification + draft.

    Returns: (parsed_result, model_used, raw_response_json)
    """
    selected_images = _select_images(image_paths)

    # Build content array with images
    content = []
    for img_path in selected_images:
        b64 = _encode_image(img_path)
        ext = Path(img_path).suffix.lower().lstrip(".")
        mime = f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}"
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64}"},
        })

    # Add text prompt
    note_text = f'\nSeller note: "{user_note}"' if user_note else ""
    content.append({
        "type": "text",
        "text": f"""{note_text}

Identify this item and generate a Kleinanzeigen listing. Respond with JSON:
{{
  "item_name": "",
  "item_category": "",
  "item_condition": "new|like_new|good|fair|poor",
  "search_terms": [],
  "title": "",
  "description": "",
  "identification_confidence": "high|medium|low"
}}""",
    })

    # Try primary model, then fallback
    models_to_try = [
        model or settings.openrouter_model,
        settings.openrouter_fallback_model,
    ]

    last_error = None
    for model_name in models_to_try:
        try:
            result, raw = await _call_openrouter(model_name, content)
            return result, model_name, raw
        except Exception as e:
            logger.warning(f"LLM call failed with {model_name}: {e}")
            last_error = e

    raise RuntimeError(f"All LLM models failed. Last error: {last_error}")


async def _call_openrouter(model: str, content: list) -> tuple[IdentificationResult, dict]:
    """Make a single OpenRouter API call and parse the response."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        "max_tokens": 500,
        "temperature": 0.3,
    }

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://kleinanzeigen-bot.local",
        "X-Title": "Kleinanzeigen Bot",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(OPENROUTER_API_URL, json=payload, headers=headers)
        if response.status_code != 200:
            logger.error(f"OpenRouter error {response.status_code}: {response.text}")
            response.raise_for_status()
        data = response.json()

    raw_text = data["choices"][0]["message"]["content"]

    # Parse JSON, handling potential markdown fences
    json_str = raw_text.strip()
    if json_str.startswith("```"):
        # Remove markdown fences
        lines = json_str.split("\n")
        json_str = "\n".join(lines[1:-1])

    parsed = json.loads(json_str)
    result = IdentificationResult(**parsed)

    return result, data
