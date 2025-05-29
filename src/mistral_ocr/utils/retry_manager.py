"""
Retry management utilities for handling transient failures with exponential backoff.

This module provides a comprehensive retry system for API calls and other operations
that may fail due to temporary network issues, rate limiting, or transient errors.
"""

import asyncio
import functools
import logging
import random
import time
from typing import Any, Callable, Dict, Optional, Set, Type, TypeVar

from ..constants import DEFAULT_MAX_RETRIES, MAX_RETRIES_LIMIT
from ..exceptions import (
    APIConnectionError,
    NonRetryableError,
    RetryableError,
)

# Type variables for generic retry functionality
F = TypeVar("F", bound=Callable[..., Any])
AsyncF = TypeVar("AsyncF", bound=Callable[..., Any])

logger = logging.getLogger(__name__)


class RetryManager:
    """
    Manages retry logic with exponential backoff and jitter.

    This class provides configurable retry behavior for operations that may
    fail due to transient errors like network issues or API rate limiting.
    """

    def __init__(
        self,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[Set[Type[Exception]]] = None,
        non_retryable_exceptions: Optional[Set[Type[Exception]]] = None,
    ) -> None:
        """
        Initialize the RetryManager.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            exponential_base: Base for exponential backoff calculation
            jitter: Whether to add random jitter to delays
            retryable_exceptions: Set of exception types that should trigger retries
            non_retryable_exceptions: Set of exception types that should never retry
        """
        if max_retries < 0 or max_retries > MAX_RETRIES_LIMIT:
            raise ValueError(f"max_retries must be between 0 and {MAX_RETRIES_LIMIT}")

        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

        # Default retryable exceptions (network/connection issues)
        self.retryable_exceptions = retryable_exceptions if retryable_exceptions is not None else {
            APIConnectionError,
            ConnectionError,
            TimeoutError,
            OSError,  # Network errors often manifest as OSError
            RetryableError,
        }

        # Default non-retryable exceptions (permanent failures)
        self.non_retryable_exceptions = non_retryable_exceptions if non_retryable_exceptions is not None else {
            NonRetryableError,
            ValueError,  # Invalid input parameters
            TypeError,  # Programming errors
            KeyError,  # Missing required data
        }

    def calculate_delay(self, attempt: int, retry_after: Optional[float] = None) -> float:
        """
        Calculate the delay for the given retry attempt.

        Args:
            attempt: The current attempt number (0-based)
            retry_after: Optional delay specified by API (e.g., from Retry-After header)

        Returns:
            Delay in seconds before the next retry
        """
        if retry_after is not None:
            # Respect API-specified retry delay
            base_delay = retry_after
        else:
            # Calculate exponential backoff delay
            base_delay = self.base_delay * (self.exponential_base**attempt)

        # Apply jitter to avoid thundering herd
        if self.jitter:
            jitter_factor = 0.1  # ±10% jitter
            jitter_amount = base_delay * jitter_factor * (2 * random.random() - 1)
            base_delay += jitter_amount

        # Cap at maximum delay and ensure non-negative
        return max(0.0, min(base_delay, self.max_delay))

    def is_retryable(self, exception: Exception) -> bool:
        """
        Determine if an exception should trigger a retry.

        Args:
            exception: The exception to evaluate

        Returns:
            True if the exception is retryable, False otherwise
        """
        # Check for explicit non-retryable exceptions first
        if any(isinstance(exception, exc_type) for exc_type in self.non_retryable_exceptions):
            return False

        # Check for explicit retryable exceptions
        if any(isinstance(exception, exc_type) for exc_type in self.retryable_exceptions):
            return True

        # Check for HTTP status codes that are typically retryable
        if hasattr(exception, "status_code"):
            status = exception.status_code
            # Retry on server errors (5xx) and rate limiting (429)
            if status >= 500 or status == 429:
                return True
            # Don't retry on client errors (4xx) except 429
            if 400 <= status < 500:
                return False

        # Default to not retryable for unknown exceptions
        return False

    def extract_retry_after(self, exception: Exception) -> Optional[float]:
        """
        Extract retry delay from exception (e.g., from API response headers).

        Args:
            exception: The exception to examine

        Returns:
            Delay in seconds if found, None otherwise
        """
        if isinstance(exception, RetryableError) and exception.retry_after:
            return exception.retry_after

        # Check for HTTP response with Retry-After header (case-insensitive)
        if hasattr(exception, "response") and hasattr(exception.response, "headers"):
            headers = exception.response.headers
            # Try both common case variations of the header
            retry_after = headers.get("Retry-After") or headers.get("retry-after")
            if retry_after:
                try:
                    return float(retry_after)
                except ValueError:
                    # Retry-After might be a date instead of seconds
                    pass

        return None

    def execute_with_retry(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Execute a function with retry logic.

        Args:
            func: The function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            The result of the successful function call

        Raises:
            The last exception if all retries are exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):  # +1 for initial attempt
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"Operation succeeded after {attempt} retries")
                return result

            except Exception as e:
                last_exception = e

                # Don't retry if this is the last attempt
                if attempt >= self.max_retries:
                    break

                # Check if this exception is retryable
                if not self.is_retryable(e):
                    logger.debug(f"Exception not retryable: {type(e).__name__}: {e}")
                    break

                # Calculate delay and wait
                retry_after = self.extract_retry_after(e)
                delay = self.calculate_delay(attempt, retry_after)

                logger.warning(
                    f"Attempt {attempt + 1}/{self.max_retries + 1} failed: "
                    f"{type(e).__name__}: {e}. Retrying in {delay:.2f} seconds..."
                )

                time.sleep(delay)

        # All retries exhausted
        logger.error(
            f"All retry attempts exhausted. Last error: "
            f"{type(last_exception).__name__}: {last_exception}"
        )
        raise last_exception

    async def execute_with_retry_async(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Execute an async function with retry logic.

        Args:
            func: The async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            The result of the successful function call

        Raises:
            The last exception if all retries are exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):  # +1 for initial attempt
            try:
                result = await func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"Async operation succeeded after {attempt} retries")
                return result

            except Exception as e:
                last_exception = e

                # Don't retry if this is the last attempt
                if attempt >= self.max_retries:
                    break

                # Check if this exception is retryable
                if not self.is_retryable(e):
                    logger.debug(f"Exception not retryable: {type(e).__name__}: {e}")
                    break

                # Calculate delay and wait
                retry_after = self.extract_retry_after(e)
                delay = self.calculate_delay(attempt, retry_after)

                logger.warning(
                    f"Async attempt {attempt + 1}/{self.max_retries + 1} failed: "
                    f"{type(e).__name__}: {e}. Retrying in {delay:.2f} seconds..."
                )

                await asyncio.sleep(delay)

        # All retries exhausted
        logger.error(
            f"All async retry attempts exhausted. Last error: "
            f"{type(last_exception).__name__}: {last_exception}"
        )
        raise last_exception


def with_retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[Set[Type[Exception]]] = None,
    non_retryable_exceptions: Optional[Set[Type[Exception]]] = None,
) -> Callable[[F], F]:
    """
    Decorator that adds retry logic to a function.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add random jitter to delays
        retryable_exceptions: Set of exception types that should trigger retries
        non_retryable_exceptions: Set of exception types that should never retry

    Returns:
        Decorated function with retry logic
    """
    retry_manager = RetryManager(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions,
        non_retryable_exceptions=non_retryable_exceptions,
    )

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return retry_manager.execute_with_retry(func, *args, **kwargs)

        return wrapper

    return decorator


def with_retry_async(
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[Set[Type[Exception]]] = None,
    non_retryable_exceptions: Optional[Set[Type[Exception]]] = None,
) -> Callable[[AsyncF], AsyncF]:
    """
    Decorator that adds retry logic to an async function.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add random jitter to delays
        retryable_exceptions: Set of exception types that should trigger retries
        non_retryable_exceptions: Set of exception types that should never retry

    Returns:
        Decorated async function with retry logic
    """
    retry_manager = RetryManager(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions,
        non_retryable_exceptions=non_retryable_exceptions,
    )

    def decorator(func: AsyncF) -> AsyncF:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await retry_manager.execute_with_retry_async(func, *args, **kwargs)

        return wrapper

    return decorator


# Convenience function to create a configured retry manager based on settings
def create_retry_manager(settings: Optional[Dict[str, Any]] = None) -> RetryManager:
    """
    Create a RetryManager instance configured with application settings.

    Args:
        settings: Optional dictionary with retry configuration

    Returns:
        Configured RetryManager instance
    """
    if settings is None:
        settings = {}

    return RetryManager(
        max_retries=settings.get("max_retries", DEFAULT_MAX_RETRIES),
        base_delay=settings.get("base_delay", 1.0),
        max_delay=settings.get("max_delay", 60.0),
        exponential_base=settings.get("exponential_base", 2.0),
        jitter=settings.get("jitter", True),
    )
