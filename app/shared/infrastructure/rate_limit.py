from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    def __init__(self):
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = monotonic()
        window_start = now - window_seconds

        with self._lock:
            events = self._events[key]

            while events and events[0] < window_start:
                events.popleft()

            if len(events) >= limit:
                return False

            events.append(now)
            return True


rate_limiter = InMemoryRateLimiter()


def rate_limit(bucket: str, *, limit: int, window_seconds: int):
    async def dependency(request: Request) -> None:
        client_host = request.client.host if request.client else "unknown"
        key = f"{bucket}:{client_host}"

        if not rate_limiter.allow(
            key=key,
            limit=limit,
            window_seconds=window_seconds,
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )

    return dependency
