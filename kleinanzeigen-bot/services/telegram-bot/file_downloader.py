"""Download Telegram files and generate thumbnails."""

import logging
import traceback
from pathlib import Path
from io import BytesIO

from PIL import Image
from telegram import PhotoSize, Bot

from config import config

logger = logging.getLogger(__name__)


async def download_photo(bot: Bot, photo: PhotoSize, listing_id: str, index: int) -> dict:
    """
    Download a photo from Telegram and save original + thumbnail.

    Returns dict with file metadata.
    """
    listing_dir = Path(config.IMAGES_DIR) / listing_id
    listing_dir.mkdir(parents=True, exist_ok=True)

    # Download from Telegram
    logger.info(f"Downloading photo {index} for listing {listing_id} "
                f"(file_id={photo.file_id[:20]}...)")

    file = await bot.get_file(photo.file_id)
    file_bytes = BytesIO()
    await file.download_to_memory(out=file_bytes)
    file_bytes.seek(0)

    raw_data = file_bytes.getvalue()
    if len(raw_data) == 0:
        raise ValueError(f"Downloaded 0 bytes for photo {index} of listing {listing_id}")

    # Determine filename
    ext = "jpg"
    original_name = f"original_{index:02d}.{ext}"
    thumb_name = f"thumb_{index:02d}.{ext}"

    original_path = listing_dir / original_name
    thumb_path = listing_dir / thumb_name

    # Save original
    with open(original_path, "wb") as f:
        f.write(raw_data)

    # Generate thumbnail (max 512px on longest side)
    file_bytes.seek(0)
    try:
        img = Image.open(file_bytes)
        img.thumbnail((config.THUMB_MAX_SIZE, config.THUMB_MAX_SIZE), Image.Resampling.LANCZOS)
        img.save(thumb_path, "JPEG", quality=80)
        thumb_width, thumb_height = img.size
    except Exception as e:
        logger.warning(f"Thumbnail generation failed for photo {index}: {e}")
        # Fall back to using original as thumb
        import shutil
        shutil.copy2(original_path, thumb_path)
        thumb_width, thumb_height = photo.width, photo.height

    file_size = original_path.stat().st_size

    logger.info(f"✅ Saved photo {index} for listing {listing_id}: "
                f"{file_size} bytes, {photo.width}x{photo.height} → {original_path}")

    return {
        "file_path": str(original_path),
        "file_name": original_name,
        "file_size_bytes": file_size,
        "mime_type": f"image/{ext}",
        "width": photo.width,
        "height": photo.height,
        "thumb_path": str(thumb_path),
        "telegram_file_id": photo.file_id,
        "telegram_file_unique_id": photo.file_unique_id,
        "sort_order": index,
    }
