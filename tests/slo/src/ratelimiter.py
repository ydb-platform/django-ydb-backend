"""A lightweight, thread-safe rate limiter shared across worker threads."""

import threading
import time


class SyncRateLimiter:
    """Enforce a minimum interval between permits across all sharing threads.

    Used as a context manager: ``with limiter: do_one_operation()``. With a
    non-positive interval it is a no-op (run as fast as possible).
    """

    def __init__(self, min_interval_s):
        self._min_interval_s = max(0.0, float(min_interval_s))
        self._lock = threading.Lock()
        self._next_allowed_ts = 0.0  # monotonic timestamp

    @classmethod
    def from_rps(cls, rps):
        return cls(0.0 if rps <= 0 else 1.0 / rps)

    def __enter__(self):
        if self._min_interval_s <= 0.0:
            return self

        while True:
            with self._lock:
                now = time.monotonic()
                if now >= self._next_allowed_ts:
                    self._next_allowed_ts = now + self._min_interval_s
                    return self
                sleep_for = self._next_allowed_ts - now

            # Sleep outside the lock so other threads can observe the schedule.
            if sleep_for > 0:
                time.sleep(sleep_for)

    def __exit__(self, exc_type, exc, tb):
        return False
