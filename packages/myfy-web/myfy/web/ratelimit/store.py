"""
Rate limit storage backends.

Provides protocol and implementations for storing rate limit state.
"""

import asyncio
import contextlib
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Protocol

from .types import RateLimitResult


class RateLimitStore(Protocol):
    """
    Protocol for rate limit storage backends.

    Implementations must be thread-safe and support async operations.
    The store tracks request counts per key within sliding time windows.
    """

    async def check_and_increment(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        """
        Check if a request is allowed and increment the counter.

        This operation must be atomic to prevent race conditions.

        Args:
            key: Unique identifier for the rate limit bucket
            limit: Maximum requests allowed in the window
            window_seconds: Time window in seconds

        Returns:
            RateLimitResult with allowed status and metadata
        """
        ...

    async def get_remaining(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        """
        Get remaining requests without incrementing.

        Useful for checking limits without consuming quota.

        Args:
            key: Unique identifier for the rate limit bucket
            limit: Maximum requests allowed in the window
            window_seconds: Time window in seconds

        Returns:
            RateLimitResult with current state
        """
        ...

    async def reset(self, key: str) -> None:
        """
        Reset the rate limit for a key.

        Useful for admin operations or testing.

        Args:
            key: Unique identifier for the rate limit bucket
        """
        ...


@dataclass
class _BucketState:
    """Internal state for a rate limit bucket."""

    count: int = 0
    window_start: float = field(default_factory=time.time)


class InMemoryRateLimitStore:
    """
    In-memory rate limit store using sliding window counters.

    Suitable for single-instance deployments. For distributed systems,
    use a Redis-backed implementation.

    Thread-safe via asyncio locks per bucket.
    Automatically cleans up expired buckets.
    """

    def __init__(self, cleanup_interval: float = 60.0):
        """
        Initialize the in-memory store.

        Args:
            cleanup_interval: Seconds between cleanup runs (default: 60)
        """
        self._buckets: dict[str, _BucketState] = defaultdict(_BucketState)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._global_lock = asyncio.Lock()
        self._cleanup_interval = cleanup_interval
        self._cleanup_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start background cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None

    async def _cleanup_loop(self) -> None:
        """Periodically clean up expired buckets."""
        while True:
            await asyncio.sleep(self._cleanup_interval)
            await self._cleanup_expired()

    async def _cleanup_expired(self) -> None:
        """Remove expired bucket entries."""
        now = time.time()
        async with self._global_lock:
            expired_keys = [
                key
                for key, state in self._buckets.items()
                # Keep buckets for 2x window to handle edge cases
                if now - state.window_start > 120
            ]
            for key in expired_keys:
                del self._buckets[key]
                if key in self._locks:
                    del self._locks[key]

    async def check_and_increment(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        """Check and increment atomically."""
        async with self._locks[key]:
            now = time.time()
            state = self._buckets[key]

            # Check if window has expired
            if now - state.window_start >= window_seconds:
                # Start new window
                state.count = 0
                state.window_start = now

            # Calculate reset time
            reset_at = state.window_start + window_seconds
            remaining = limit - state.count - 1  # -1 for this request

            if state.count >= limit:
                # Rate limit exceeded
                retry_after = int(reset_at - now) + 1
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_at=reset_at,
                    retry_after=retry_after,
                    limit=limit,
                )

            # Increment counter
            state.count += 1

            return RateLimitResult(
                allowed=True,
                remaining=max(0, remaining),
                reset_at=reset_at,
                retry_after=0,
                limit=limit,
            )

    async def get_remaining(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        """Get remaining without incrementing."""
        async with self._locks[key]:
            now = time.time()
            state = self._buckets[key]

            # Check if window has expired
            if now - state.window_start >= window_seconds:
                # Window expired, would start fresh
                return RateLimitResult(
                    allowed=True,
                    remaining=limit,
                    reset_at=now + window_seconds,
                    retry_after=0,
                    limit=limit,
                )

            reset_at = state.window_start + window_seconds
            remaining = limit - state.count

            if remaining <= 0:
                retry_after = int(reset_at - now) + 1
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_at=reset_at,
                    retry_after=retry_after,
                    limit=limit,
                )

            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                reset_at=reset_at,
                retry_after=0,
                limit=limit,
            )

    async def reset(self, key: str) -> None:
        """Reset a specific bucket."""
        async with self._locks[key]:
            if key in self._buckets:
                del self._buckets[key]
