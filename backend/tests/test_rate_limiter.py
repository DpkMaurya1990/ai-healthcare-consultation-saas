import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rate_limiter import RateLimiter


class DummyTime:
    def __init__(self) -> None:
        self._now = 1000.0

    def time(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


class RateLimiterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dummy_time = DummyTime()
        self.limiter = RateLimiter(time_func=self.dummy_time.time, user_limit=2, ip_limit=3, daily_user_limit=5)

    def test_rate_limit_user_window(self) -> None:
        self.assertTrue(self.limiter.allow("user1", "1.1.1.1")[0])
        self.assertTrue(self.limiter.allow("user1", "1.1.1.1")[0])
        allowed, message = self.limiter.allow("user1", "1.1.1.1")
        self.assertFalse(allowed)
        self.assertIn("Too many requests", message)

    def test_rate_limit_ip_window(self) -> None:
        self.assertTrue(self.limiter.allow("user1", "1.1.1.1")[0])
        self.assertTrue(self.limiter.allow("user2", "1.1.1.1")[0])
        self.assertTrue(self.limiter.allow("user3", "1.1.1.1")[0])
        allowed, message = self.limiter.allow("user4", "1.1.1.1")
        self.assertFalse(allowed)
        self.assertIn("IP address", message)

    def test_daily_user_limit(self) -> None:
        limiter = RateLimiter(time_func=self.dummy_time.time, user_limit=100, ip_limit=100, daily_user_limit=5)
        for _ in range(5):
            self.assertTrue(limiter.allow("user1", f"1.1.1.{_}")[0])
        allowed, message = limiter.allow("user1", "1.1.1.9")
        self.assertFalse(allowed)
        self.assertIn("Daily request limit reached", message)
