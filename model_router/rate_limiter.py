import threading
import time
from collections import deque


class RateLimiter:
    """Sliding-window request cap - refuses calls once `max_requests` have
    happened in the last `per_seconds`, so a stuck loop or crash-restart
    can't run up an unbounded API bill."""

    def __init__(self, max_requests: int, per_seconds: float):
        self.max_requests = max_requests
        self.per_seconds = per_seconds
        self._timestamps = deque()
        self._lock = threading.Lock()

    def allow(self) -> bool:
        now = time.monotonic()
        with self._lock:
            while self._timestamps and now - self._timestamps[0] > self.per_seconds:
                self._timestamps.popleft()
            if len(self._timestamps) >= self.max_requests:
                return False
            self._timestamps.append(now)
            return True
