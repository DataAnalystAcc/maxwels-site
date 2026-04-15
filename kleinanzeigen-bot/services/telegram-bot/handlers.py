"""Telegram message handlers — photo intake, notes, and commands."""

import json
import uuid
import logging
import traceback
from datetime import datetime, timezone

import httpx
import psycopg2
import redis.asyncio as aioredis
from telegram import Update
from telegram.ext import ContextTypes

from config import config
from media_grouper import MediaGrouper
from file_downloader import download_photo

logger = logging.getLogger(__name__)

# Module-level state (initialized in bot.py)
redis_client: aioredis.Redis = None
media_grouper: MediaGrouper = None

# Will be set by bot.py after initialization
_bot_context = None


def get_db_conn():
    """Get a synchronous psycopg2 connection (used for simple inserts)."""
    return psycopg2.connect(config.DATABASE_URL)


def _is_authorized(chat_id: int) -> bool:
    """Check if the chat is authorized."""
    if config.ALLOWED_TELEGRAM_CHAT_ID == 0:
        return True  # No restriction configured
    return chat_id == config.ALLOWED_TELEGRAM_CHAT_ID


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming photo messages (single or part of media group)."""
    message = update.effective_message
    chat_id = message.chat_id

    if not _is_authorized(chat_id):
        logger.warning(f"Unauthorized message from chat {chat_id}")
        return

    try:
        # Get the largest photo size
        photo = message.photo[-1]

        # Prepare message data for buffering
        msg_data = {
            "message_id": message.message_id,
            "chat_id": chat_id,
            "file_id": photo.file_id,
            "file_unique_id": photo.file_unique_id,
            "file_size": photo.file_size,
            "width": photo.width,
            "height": photo.height,
            "caption": message.caption,
            "timestamp": message.date.isoformat() if message.date else None,
        }

        if message.media_group_id:
            # Part of a media group — buffer it
            await media_grouper.add_message(message.media_group_id, msg_data)
        else:
            # Single photo — process immediately
            await _process_item(
                group_id=None,
                messages=[msg_data],
                context=context,
            )

    except Exception as e:
        logger.error(f"handle_photo failed for chat {chat_id}: {e}\n{traceback.format_exc()}")
        try:
            await message.reply_text(
                f"⚠️ Fehler beim Verarbeiten des Fotos:\n`{type(e).__name__}: {e}`",
                parse_mode="Markdown",
            )
        except Exception as reply_err:
            logger.error(f"Failed to send error reply: {reply_err}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages — might be a note for the last item."""
    message = update.effective_message
    chat_id = message.chat_id

    if not _is_authorized(chat_id):
        return

    text = message.text.strip() if message.text else ""
    if not text:
        return

    try:
        # Check if there's a recent listing awaiting a note
        note_key = f"awaiting_note:{chat_id}"
        listing_id = await redis_client.get(note_key)

        if listing_id:
            listing_id = listing_id.decode("utf-8")
            await redis_client.delete(note_key)

            # Update listing with user note
            conn = get_db_conn()
            cur = conn.cursor()
            cur.execute(
                "UPDATE listings SET user_note = %s, updated_at = %s WHERE id = %s::uuid",
                (text, datetime.now(timezone.utc), listing_id),
            )
            conn.commit()
            cur.close()
            conn.close()

            await message.reply_text(f"📝 Note added to last item.")
            logger.info(f"Note added to listing {listing_id}: {text[:50]}...")
        else:
            await message.reply_text(
                "💡 Send photos first, then add a note within 5 seconds.\n"
                "Or send /help for commands."
            )

    except Exception as e:
        logger.error(f"handle_text failed for chat {chat_id}: {e}\n{traceback.format_exc()}")
        try:
            await message.reply_text(f"⚠️ Fehler: {e}")
        except Exception:
            pass


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        "📦 *Kleinanzeigen Listing Bot*\n\n"
        "Send me photos of items you want to sell:\n"
        "• Send 1–8 photos as an album\n"
        "• Optionally add a caption or follow-up note\n"
        "• I'll identify the item, research prices, and create a draft listing\n\n"
        "Commands:\n"
        "/status — Show queue status\n"
        "/help — Show this message",
        parse_mode="Markdown",
    )


async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command — show listing counts by status."""
    if not _is_authorized(update.effective_chat.id):
        return

    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT status, COUNT(*) as cnt
            FROM listings
            GROUP BY status
            ORDER BY cnt DESC
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            await update.message.reply_text("📭 No listings yet. Send some photos!")
            return

        status_emoji = {
            "intake_received": "📥",
            "draft_generating": "⏳",
            "pricing_pending": "💰",
            "draft_ready": "📝",
            "draft_failed": "❌",
            "approved": "✅",
            "posting_queued": "📤",
            "posting_in_progress": "🚀",
            "posted": "🎉",
            "posting_failed": "⚠️",
            "failed_permanent": "💀",
            "rejected": "🗑️",
        }

        lines = ["📊 *Listing Status*\n"]
        total = 0
        for status, count in rows:
            emoji = status_emoji.get(status, "•")
            lines.append(f"{emoji} {status}: *{count}*")
            total += count
        lines.append(f"\nTotal: *{total}*")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        await update.message.reply_text("⚠️ Failed to check status.")


async def _process_item(
    group_id: str | None,
    messages: list[dict],
    context,
):
    """Process a complete item (single photo or flushed media group)."""
    if not messages:
        return

    chat_id = messages[0]["chat_id"]
    listing_id = str(uuid.uuid4())

    # Extract caption from first message (if any)
    user_note = None
    for msg in messages:
        if msg.get("caption"):
            user_note = msg["caption"]
            break

    logger.info(f"Processing item: listing_id={listing_id}, photos={len(messages)}, "
                f"note={'yes' if user_note else 'no'}")

    # Download all photos and generate thumbnails
    image_records = []
    bot = context.bot
    for i, msg in enumerate(messages):
        try:
            from telegram import PhotoSize as PS
            # Create a minimal PhotoSize object for download
            photo = PS(
                file_id=msg["file_id"],
                file_unique_id=msg["file_unique_id"],
                width=msg["width"],
                height=msg["height"],
                file_size=msg.get("file_size"),
            )
            file_meta = await download_photo(bot, photo, listing_id, i)
            image_records.append(file_meta)
        except Exception as e:
            logger.error(f"Failed to download photo {i} for listing {listing_id}: {e}\n{traceback.format_exc()}")

    if not image_records:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text="⚠️ Konnte keine Fotos herunterladen. Bitte nochmal versuchen.",
            )
        except Exception as send_err:
            logger.error(f"Failed to send download-error message: {send_err}")
        return

    # Save to database
    try:
        conn = get_db_conn()
        cur = conn.cursor()

        # Insert listing
        msg_ids = [m["message_id"] for m in messages]
        cur.execute("""
            INSERT INTO listings (id, status, user_note, telegram_chat_id,
                                  telegram_msg_ids, media_group_id, created_at, updated_at)
            VALUES (%s::uuid, 'intake_received', %s, %s, %s, %s, %s, %s)
        """, (
            listing_id, user_note, chat_id, msg_ids, group_id,
            datetime.now(timezone.utc), datetime.now(timezone.utc),
        ))

        # Insert images
        for img in image_records:
            cur.execute("""
                INSERT INTO listing_images
                    (listing_id, file_path, file_name, file_size_bytes, mime_type,
                     width, height, sort_order, telegram_file_id,
                     telegram_file_unique_id, thumb_path)
                VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (telegram_file_unique_id) DO UPDATE SET
                    listing_id = EXCLUDED.listing_id,
                    file_path = EXCLUDED.file_path,
                    file_name = EXCLUDED.file_name,
                    file_size_bytes = EXCLUDED.file_size_bytes,
                    thumb_path = EXCLUDED.thumb_path,
                    sort_order = EXCLUDED.sort_order
            """, (
                listing_id, img["file_path"], img["file_name"],
                img["file_size_bytes"], img["mime_type"],
                img["width"], img["height"], img["sort_order"],
                img["telegram_file_id"], img["telegram_file_unique_id"],
                img["thumb_path"],
            ))

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        logger.error(f"Database insert failed for listing {listing_id}: {e}\n{traceback.format_exc()}")
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ DB-Fehler beim Speichern:\n`{type(e).__name__}: {e}`",
                parse_mode="Markdown",
            )
        except Exception:
            pass
        return

    # Set "awaiting note" key if no caption was provided
    if not user_note:
        try:
            await redis_client.setex(
                f"awaiting_note:{chat_id}",
                int(config.NOTE_WAIT_TIMEOUT_SEC),
                listing_id,
            )
        except Exception as e:
            logger.warning(f"Redis setex for awaiting_note failed: {e}")

    # Get item count for this chat
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM listings WHERE telegram_chat_id = %s",
            (chat_id,),
        )
        item_count = cur.fetchone()[0]
        cur.close()
        conn.close()
    except Exception:
        item_count = "?"

    # Reply to user
    note_hint = "" if user_note else "\n💡 Send a text note within 5s to add details."
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=f"📦 Item #{item_count} received ({len(image_records)} photos). Processing...{note_hint}",
        )
    except Exception as e:
        logger.error(f"Failed to send confirmation to chat {chat_id}: {e}")

    # Fire webhook to n8n to trigger draft generation
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                config.N8N_WEBHOOK_ITEM_INTAKE,
                json={
                    "listing_id": listing_id,
                    "chat_id": chat_id,
                    "review_url": config.REVIEW_BASE_URL,
                    "image_count": len(image_records),
                    "has_user_note": user_note is not None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        logger.info(f"n8n webhook fired for listing {listing_id} (status={resp.status_code})")
    except Exception as e:
        logger.warning(f"n8n webhook failed for listing {listing_id}: {e} — draft can be triggered manually later")
        # Not fatal — the draft can be triggered manually later


async def on_group_ready(group_id: str, messages: list[dict]):
    """
    Callback from MediaGrouper when a media group is fully collected.
    This needs access to the bot context, which we pass through a module-level global.
    """
    global _bot_context
    if _bot_context is None:
        logger.error(f"No bot context available to process group {group_id}. "
                     f"This means post_init hasn't run yet. Dropping {len(messages)} photos.")
        return

    try:
        await _process_item(group_id, messages, _bot_context)
    except Exception as e:
        logger.error(f"on_group_ready failed for group {group_id}: {e}\n{traceback.format_exc()}")
        # Try to notify the user
        chat_id = messages[0].get("chat_id") if messages else None
        if chat_id and _bot_context:
            try:
                await _bot_context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ Fehler beim Verarbeiten des Albums:\n`{type(e).__name__}: {e}`",
                    parse_mode="Markdown",
                )
            except Exception:
                pass
