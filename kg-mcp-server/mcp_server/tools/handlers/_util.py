"""Shared utilities for handler modules."""

import asyncio


async def _run_sync(func, *args, **kwargs):
    """Run a blocking function in a thread to avoid blocking the event loop."""
    return await asyncio.to_thread(func, *args, **kwargs)
