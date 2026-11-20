"""Serialize configuration edits/imports and their live readers (one service worker)."""
from asyncio import Lock
from functools import wraps

config_lock = Lock()


def locked(function):
    @wraps(function)
    async def wrapped(*args, **kwargs):
        async with config_lock:
            return await function(*args, **kwargs)
    return wrapped
