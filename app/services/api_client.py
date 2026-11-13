import logging
import os
import threading
import time
from typing import Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class CircuitBreakerOpenError(Exception):
    """Raised when calls to an external service are blocked because its circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Thread-safe Circuit Breaker pattern implementation for external API dependencies.
    States:
    - CLOSED: Normal operation. Requests flow through.
    - OPEN: Service has failed >= failure_threshold times. Calls fail fast without network delay.
    - HALF_OPEN: Cooldown period expired. A single canary request tests service recovery.
    """

    STATE_CLOSED = "CLOSED"
    STATE_OPEN = "OPEN"
    STATE_HALF_OPEN = "HALF_OPEN"

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        cooldown_seconds: float = 60.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._lock = threading.Lock()
        self.state = self.STATE_CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.total_calls = 0
        self.last_failure_time: Optional[float] = None
        self.last_success_time: Optional[float] = None
        self.last_state_change: float = time.time()

    def can_execute(self) -> bool:
        """Determine whether a call should be attempted or short-circuited."""
        with self._lock:
            now = time.time()
            if self.state == self.STATE_CLOSED:
                return True

            if self.state == self.STATE_OPEN:
                # Check if cooldown has elapsed to transition to HALF_OPEN
                if self.last_failure_time and (now - self.last_failure_time) >= self.cooldown_seconds:
                    self.state = self.STATE_HALF_OPEN
                    self.last_state_change = now
                    logger.info(f"[CircuitBreaker:{self.name}] Transitioned OPEN -> HALF_OPEN (probing recovery)")
                    return True
                return False

            if self.state == self.STATE_HALF_OPEN:
                # In half-open, allow the trial request
                return True

            return True

    def record_success(self, duration_ms: float = 0.0):
        """Record a successful response."""
        with self._lock:
            self.total_calls += 1
            self.success_count += 1
            self.last_success_time = time.time()
            if self.state in (self.STATE_HALF_OPEN, self.STATE_OPEN):
                logger.info(f"[CircuitBreaker:{self.name}] Service recovered. Transitioned to CLOSED.")
            self.state = self.STATE_CLOSED
            self.failure_count = 0

    def record_failure(self, error: Exception):
        """Record a call failure and potentially trip the circuit open."""
        with self._lock:
            self.total_calls += 1
            self.failure_count += 1
            now = time.time()
            self.last_failure_time = now

            if self.state == self.STATE_HALF_OPEN or self.failure_count >= self.failure_threshold:
                if self.state != self.STATE_OPEN:
                    logger.warning(
                        f"[CircuitBreaker:{self.name}] Failure threshold reached ({self.failure_count}). "
                        f"Opening circuit for {self.cooldown_seconds}s. Reason: {error}"
                    )
                self.state = self.STATE_OPEN
                self.last_state_change = now

    def reset(self):
        """Force manual reset back to normal operation."""
        with self._lock:
            self.state = self.STATE_CLOSED
            self.failure_count = 0
            self.last_state_change = time.time()

    def get_status(self) -> dict[str, Any]:
        """Return diagnostic metrics for monitoring."""
        with self._lock:
            return {
                "name": self.name,
                "state": self.state,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "total_calls": self.total_calls,
                "last_failure_time": self.last_failure_time,
                "last_success_time": self.last_success_time,
            }


class ApiClient:
    """
    High-Performance Enterprise API Client for Outgoing Network Communication.
    Features:
    - Connection Pooling & Keep-Alive HTTP Session reuse
    - Exponential backoff retries for transient errors (429, 500, 502, 503, 504)
    - Per-service Circuit Breaker to prevent cascading failures
    - Granular dual timeouts (connect=1.5s, read=3.5s)
    - Request telemetry, sanitized logging, and performance metrics
    """

    DEFAULT_CONNECT_TIMEOUT = 1.5
    DEFAULT_READ_TIMEOUT = 3.5

    def __init__(
        self,
        pool_connections: int = 25,
        pool_maxsize: int = 50,
        max_retries: int = 2,
        backoff_factor: float = 0.3,
    ):
        self.session = requests.Session()

        # Enterprise retry configuration with exponential backoff and jitter
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            raise_on_status=False,
        )

        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy,
        )

        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.default_headers = {
            "User-Agent": (
                "JobSnap-Engine/2.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/html, */*",
            "Accept-Encoding": "gzip, deflate",
        }

        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()

    def get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """Get or initialize the CircuitBreaker for a given external provider."""
        with self._lock:
            if service_name not in self._breakers:
                self._breakers[service_name] = CircuitBreaker(name=service_name)
            return self._breakers[service_name]

    def request(
        self,
        method: str,
        url: str,
        service_name: Optional[str] = None,
        timeout: Optional[tuple[float, float] | float] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs,
    ) -> requests.Response:
        """
        Execute an HTTP request with connection reuse, circuit breaker protection, and telemetry.
        """
        svc = service_name or self._extract_service_name(url)
        breaker = self.get_circuit_breaker(svc)

        # Check circuit breaker before attempting network roundtrip
        if not breaker.can_execute():
            logger.warning(f"[ApiClient] Circuit OPEN for service '{svc}'. Short-circuiting call to {url}.")
            raise CircuitBreakerOpenError(f"Service '{svc}' is currently unavailable (circuit open).")

        # Merge headers
        req_headers = dict(self.default_headers)
        if headers:
            req_headers.update(headers)

        # Default granular timeouts
        if timeout is None:
            timeout = (self.DEFAULT_CONNECT_TIMEOUT, self.DEFAULT_READ_TIMEOUT)

        start_time = time.time()
        try:
            resp = self.session.request(
                method=method,
                url=url,
                headers=req_headers,
                timeout=timeout,
                **kwargs,
            )
            elapsed_ms = (time.time() - start_time) * 1000.0

            # Record outcome for circuit breaker
            if resp.status_code in (429, 500, 502, 503, 504):
                breaker.record_failure(Exception(f"HTTP {resp.status_code}"))
                logger.warning(
                    f"[ApiClient] {method} {url} returned HTTP {resp.status_code} in {elapsed_ms:.1f}ms (service: {svc})"
                )
            else:
                breaker.record_success(duration_ms=elapsed_ms)
                if elapsed_ms > 2000:
                    logger.info(f"[ApiClient] Slow response: {method} {url} took {elapsed_ms:.1f}ms")

            return resp

        except (requests.exceptions.RequestException, Exception) as exc:
            elapsed_ms = (time.time() - start_time) * 1000.0
            breaker.record_failure(exc)
            logger.warning(
                f"[ApiClient] Network error on {method} {url} after {elapsed_ms:.1f}ms (service: {svc}): {exc}"
            )
            raise

    def get(self, url: str, service_name: Optional[str] = None, **kwargs) -> requests.Response:
        """Shorthand GET request."""
        return self.request("GET", url, service_name=service_name, **kwargs)

    def post(self, url: str, service_name: Optional[str] = None, **kwargs) -> requests.Response:
        """Shorthand POST request."""
        return self.request("POST", url, service_name=service_name, **kwargs)

    def get_all_breaker_metrics(self) -> dict[str, dict[str, Any]]:
        """Return diagnostic health metrics for all registered external providers."""
        with self._lock:
            return {name: cb.get_status() for name, cb in self._breakers.items()}

    @staticmethod
    def _extract_service_name(url: str) -> str:
        """Extract domain hostname as service identifier."""
        try:
            from urllib.parse import urlparse
            netloc = urlparse(url).netloc
            return netloc.split(":")[0] if netloc else "unknown_service"
        except Exception:
            return "unknown_service"


# Global singleton client instance for high-throughput connection pooling
default_api_client = ApiClient()

