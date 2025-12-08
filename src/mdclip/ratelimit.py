"""Domain-based rate limiting for mdclip."""

import time
from collections import deque
from urllib.parse import urlparse


class DomainRateLimiter:
    """Rate limiter that tracks per-domain access times.

    Supports deferred queue for efficient processing of mixed-domain URL lists.
    """

    def __init__(self, delay_seconds: float = 3.0):
        """Initialize rate limiter.

        Args:
            delay_seconds: Minimum seconds between requests to same domain.
        """
        self.delay_seconds = delay_seconds
        self._domain_timestamps: dict[str, float] = {}
        self._deferred: deque[str] = deque()

    @staticmethod
    def get_domain(url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc.lower()

    def time_until_allowed(self, url: str) -> float:
        """Return seconds to wait before this URL can be processed.

        Returns 0 if the URL can be processed immediately.
        """
        domain = self.get_domain(url)
        last_access = self._domain_timestamps.get(domain)
        if last_access is None:
            return 0.0
        elapsed = time.time() - last_access
        remaining = self.delay_seconds - elapsed
        return max(0.0, remaining)

    def is_allowed(self, url: str) -> bool:
        """Check if URL can be processed now without waiting."""
        return self.time_until_allowed(url) <= 0

    def record_access(self, url: str) -> None:
        """Record that a URL's domain was just accessed."""
        domain = self.get_domain(url)
        self._domain_timestamps[domain] = time.time()

    def wait_if_needed(self, url: str) -> float:
        """Wait until URL is allowed, return seconds waited."""
        wait_time = self.time_until_allowed(url)
        if wait_time > 0:
            time.sleep(wait_time)
        return wait_time

    # --- Deferred queue methods ---

    def defer(self, url: str) -> None:
        """Add URL to deferred queue for later processing."""
        self._deferred.append(url)

    def get_ready_deferred(self) -> list[str]:
        """Get and remove all deferred URLs that are now ready."""
        ready = []
        still_deferred: deque[str] = deque()
        while self._deferred:
            url = self._deferred.popleft()
            if self.is_allowed(url):
                ready.append(url)
            else:
                still_deferred.append(url)
        self._deferred = still_deferred
        return ready

    def has_deferred(self) -> bool:
        """Check if there are deferred URLs waiting."""
        return len(self._deferred) > 0

    def pop_deferred_with_wait(self) -> str | None:
        """Pop next deferred URL, waiting if necessary.

        Returns None if the deferred queue is empty.
        """
        if not self._deferred:
            return None
        url = self._deferred.popleft()
        self.wait_if_needed(url)
        return url

    def deferred_count(self) -> int:
        """Return number of URLs in deferred queue."""
        return len(self._deferred)
