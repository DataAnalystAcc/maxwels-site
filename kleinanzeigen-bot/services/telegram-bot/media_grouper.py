"""Media group buffering logic using Redis.

Telegram sends each photo in an album as a separate message with a shared
media_group_id. This module implements the buffer-and-timeout pattern:
1. Buffer each message in Redis keyed by media_group_id
2. Refresh a short TTL on each new message
3. After timeout with no new messages, flush the group for processing
"""

import json
import asyncio
import logging
from typing import Callable, Awaitable, Optional

import redis.asyncio as aioredis

from config import config

logger = logging.getLogger(__name__)

# Redis key patterns
_GROUP_KEY = "media_group:{group_id}"
_TIMERS: dict[str, asyncio.Task] = {}


class MediaGrouper:
    """Buffers Telegram media group messages and flushes them after a timeout."""

    def __init__(self, redis_client: aioredis.Redis, on_group_ready: Callable):
        """
        Args:
            redis_client: async Redis connection
            on_group_ready: async callback(group_id, messages_json_list)
        """
        self.redis = redis_client
        self.on_group_ready = on_group_ready
        self._timers: dict[str, asyncio.Task] = {}

    async def add_message(self, group_id: str, message_data: dict):
        """
        Add a message to the media group buffer.
        Resets the flush timer each time a new message arrives.
        """
        key = _GROUP_KEY.format(group_id=group_id)

        # Store message in Redis list
        await self.redis.rpush(key, json.dumps(message_data))
        # Set/refresh TTL (safety net in case timer fails)
        await self.redis.expire(key, 30)

        # Cancel existing timer for this group
        if group_id in self._timers:
            self._timers[group_id].cancel()

        # Start new timer
        self._timers[group_id] = asyncio.create_task(
            self._flush_after_timeout(group_id)
        )

    async def _flush_after_timeout(self, group_id: str):
        """Wait for timeout, then flush the group."""
        try:
            await asyncio.sleep(config.MEDIA_GROUP_TIMEOUT_SEC)
            await self._flush_group(group_id)
        except asyncio.CancelledError:
            pass  # Timer was cancelled because a new message arrived

    async def _flush_group(self, group_id: str):
        """Retrieve all messages for a group and trigger processing."""
        key = _GROUP_KEY.format(group_id=group_id)

        # Atomically get all messages and delete the key
        messages_raw = await self.redis.lrange(key, 0, -1)
        await self.redis.delete(key)

        # Clean up timer reference
        self._timers.pop(group_id, None)

        if not messages_raw:
            return

        messages = [json.loads(m) for m in messages_raw]
        # Sort by message_id to ensure correct ordering
        messages.sort(key=lambda m: m.get("message_id", 0))

        logger.info(f"Media group {group_id} complete: {len(messages)} photos")

        try:
            await self.on_group_ready(group_id, messages)
        except Exception as e:
            logger.error(f"on_group_ready callback failed for group {group_id}: {e}", exc_info=True)
