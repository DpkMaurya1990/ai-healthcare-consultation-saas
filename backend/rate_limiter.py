"""Simple in-memory rate limiting for backend request protection."""

import time
from collections import deque
from typing import Callable, Deque, Dict, Optional, Tuple


class RateLimiter:
    """Fixed-window rate limiter for user and IP-based request protection."""

    def __init__(
        self,
        user_limit: int = 12,
        ip_limit: int = 20,
        user_window_seconds: int = 60,
        ip_window_seconds: int = 60,
        daily_user_limit: int = 500,
        time_func: Callable[[], float] = time.time,
    ) -> None:
        self.user_limit = user_limit
        self.ip_limit = ip_limit
        self.user_window_seconds = user_window_seconds
        self.ip_window_seconds = ip_window_seconds
        self.daily_user_limit = daily_user_limit
        self.time_func = time_func

        self.user_requests: Dict[str, Deque[float]] = {}
        self.ip_requests: Dict[str, Deque[float]] = {}
        self.user_daily: Dict[str, Tuple[int, float]] = {}

    def _cleanup(self, queue: Deque[float], window: int, now: float) -> None:
        while queue and now - queue[0] > window:
            queue.popleft()

    def _check_and_add(self, storage: Dict[str, Deque[float]], key: str, limit: int, window: int, now: float) -> bool:
        queue = storage.setdefault(key, deque())
        self._cleanup(queue, window, now)
        if len(queue) >= limit:
            return False
        queue.append(now)
        return True

    def _check_daily(self, user_id: str, now: float) -> bool:
        count, day_start = self.user_daily.get(user_id, (0, now))
        if now - day_start >= 86400:
            count = 0
            day_start = now
        if count >= self.daily_user_limit:
            self.user_daily[user_id] = (count, day_start)
            return False
        self.user_daily[user_id] = (count + 1, day_start)
        return True

    def allow(self, user_id: str, ip_address: str) -> Tuple[bool, Optional[str]]:
        now = self.time_func()

        if not self._check_daily(user_id, now):
            return False, "Daily request limit reached. Please try again tomorrow."

        if not self._check_and_add(self.user_requests, user_id, self.user_limit, self.user_window_seconds, now):
            return False, "Too many requests from this account. Please wait a moment and try again."

        if not self._check_and_add(self.ip_requests, ip_address, self.ip_limit, self.ip_window_seconds, now):
            return False, "Too many requests from this IP address. Please wait a moment and try again."

        return True, None
