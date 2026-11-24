"""How often one connection may ask (server.py): actions are already paced by game time (one in flight per agent),
so these only stop floods."""

import collections
import time

LIMITS = {"act": (900, 60.0), "observe": (900, 60.0), "say": (20, 60.0), "shout": (3, 60.0)}


class RateLimiter:
    def __init__(self):
        self.hits = collections.defaultdict(collections.deque)

    def allow(self, key: str) -> bool:
        n, window = LIMITS[key]
        q, now = self.hits[key], time.monotonic()
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= n:
            return False
        q.append(now)
        return True
