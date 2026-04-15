"""Kleinanzeigen Listing Bot — Telegram bot entry point."""

import logging
import traceback
import redis.asyncio as aioredis
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
)

from config import config
import handlers
from media_grouper import MediaGrouper

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Global error handler — catches any unhandled exception in handlers."""
    logger.error(f"Unhandled exception: {context.error}\n{traceback.format_exc()}")

    # Try to notify the user
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                f"⚠️ Unerwarteter Fehler:\n`{type(context.error).__name__}: {context.error}`",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")


def main():
    """Start the Telegram bot."""
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set!")
        return

    # ── Startup diagnostics ──────────────────────────────
    logger.info("=" * 60)
    logger.info("Starting Kleinanzeigen Listing Bot...")
    logger.info(f"  TELEGRAM_BOT_TOKEN: ...{config.TELEGRAM_BOT_TOKEN[-8:]}")
    logger.info(f"  ALLOWED_CHAT_ID:    {config.ALLOWED_TELEGRAM_CHAT_ID}")
    logger.info(f"  REDIS_URL:          {config.REDIS_URL}")
    logger.info(f"  DATABASE_URL:       {config.DATABASE_URL[:30]}...")
    logger.info(f"  N8N_WEBHOOK:        {config.N8N_WEBHOOK_ITEM_INTAKE}")
    logger.info(f"  IMAGES_DIR:         {config.IMAGES_DIR}")
    logger.info("=" * 60)

    # Test database connection at startup
    try:
        import psycopg2
        conn = psycopg2.connect(config.DATABASE_URL)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        logger.info("✅ Database connection OK")
    except Exception as e:
        logger.error(f"❌ Database connection FAILED: {e}")
        logger.error("Bot will start anyway, but DB operations will fail.")

    # Test Redis connection at startup
    try:
        import redis as sync_redis
        r = sync_redis.from_url(config.REDIS_URL)
        r.ping()
        r.close()
        logger.info("✅ Redis connection OK")
    except Exception as e:
        logger.error(f"❌ Redis connection FAILED: {e}")
        logger.error("Bot will start anyway, but media grouping may fail.")

    # Initialize async Redis
    redis_client = aioredis.from_url(config.REDIS_URL, decode_responses=False)
    handlers.redis_client = redis_client

    # Initialize media grouper
    media_grouper = MediaGrouper(
        redis_client=redis_client,
        on_group_ready=handlers.on_group_ready,
    )
    handlers.media_grouper = media_grouper

    # Build application
    app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Store a reference to the context for the media grouper callback
    async def post_init(application):
        handlers._bot_context = type("Ctx", (), {"bot": application.bot})()
        logger.info("✅ Bot context initialized for media grouper")

    app.post_init = post_init

    # Register error handler
    app.add_error_handler(error_handler)

    # Register handlers
    app.add_handler(CommandHandler("start", handlers.handle_start))
    app.add_handler(CommandHandler("help", handlers.handle_start))
    app.add_handler(CommandHandler("status", handlers.handle_status))
    app.add_handler(MessageHandler(filters.PHOTO, handlers.handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_text))

    logger.info("Bot handlers registered. Starting polling...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
