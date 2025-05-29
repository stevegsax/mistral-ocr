"""Comprehensive tests for the retry manager and error recovery system."""

import time
from unittest.mock import AsyncMock, patch

import pytest

from mistral_ocr.exceptions import NonRetryableError, RetryableError
from mistral_ocr.utils.retry_manager import (
    RetryManager,
    create_retry_manager,
    with_retry,
    with_retry_async,
)


class TestRetryManager:
    """Test the RetryManager class."""

    def test_retry_manager_default_initialization(self):
        """Test RetryManager with default parameters."""
        manager = RetryManager()
        assert manager.max_retries == 3
        assert manager.base_delay == 1.0
        assert manager.max_delay == 60.0
        assert manager.exponential_base == 2.0
        assert manager.jitter is True

    def test_retry_manager_custom_initialization(self):
        """Test RetryManager with custom parameters."""
        manager = RetryManager(
            max_retries=5, base_delay=2.0, max_delay=120.0, exponential_base=1.5, jitter=False
        )
        assert manager.max_retries == 5
        assert manager.base_delay == 2.0
        assert manager.max_delay == 120.0
        assert manager.exponential_base == 1.5
        assert manager.jitter is False

    def test_retry_manager_custom_exceptions(self):
        """Test RetryManager with custom exception sets."""
        custom_retryable = {ValueError, TypeError}
        custom_non_retryable = {KeyError, AttributeError}

        manager = RetryManager(
            retryable_exceptions=custom_retryable, non_retryable_exceptions=custom_non_retryable
        )

        assert manager.retryable_exceptions == custom_retryable
        assert manager.non_retryable_exceptions == custom_non_retryable

    def test_calculate_delay_basic(self):
        """Test basic delay calculation."""
        manager = RetryManager(base_delay=2.0, exponential_base=2.0, jitter=False)

        # First retry (attempt 0)
        delay = manager.calculate_delay(0)
        assert delay == 2.0

        # Second retry (attempt 1)
        delay = manager.calculate_delay(1)
        assert delay == 4.0

        # Third retry (attempt 2)
        delay = manager.calculate_delay(2)
        assert delay == 8.0

    def test_calculate_delay_with_max(self):
        """Test delay calculation with maximum limit."""
        manager = RetryManager(base_delay=10.0, max_delay=15.0, jitter=False)

        # Should be capped at max_delay
        delay = manager.calculate_delay(5)  # Would be 320.0 without cap
        assert delay == 15.0

    def test_calculate_delay_with_retry_after(self):
        """Test delay calculation with retry-after header."""
        manager = RetryManager(base_delay=2.0, jitter=False)

        # Should use retry_after value instead of calculated delay
        delay = manager.calculate_delay(0, retry_after=5.0)
        assert delay == 5.0

    def test_calculate_delay_with_jitter(self):
        """Test delay calculation with jitter enabled."""
        manager = RetryManager(base_delay=10.0, jitter=True)

        # Run multiple times to verify jitter creates variation
        delays = [manager.calculate_delay(0) for _ in range(10)]

        # All delays should be close to base_delay but not identical
        assert all(8.0 <= delay <= 12.0 for delay in delays)  # ±20% jitter range
        assert len(set(delays)) > 1  # Should have variation

    def test_is_retryable_default_exceptions(self):
        """Test exception classification with default settings."""
        manager = RetryManager()

        # Retryable exceptions
        assert manager.is_retryable(ConnectionError("Network error"))
        assert manager.is_retryable(TimeoutError("Request timeout"))
        assert manager.is_retryable(RetryableError("Custom retryable"))

        # Non-retryable exceptions
        assert not manager.is_retryable(ValueError("Invalid input"))
        assert not manager.is_retryable(TypeError("Type error"))
        assert not manager.is_retryable(NonRetryableError("Custom non-retryable"))

    def test_is_retryable_custom_exceptions(self):
        """Test exception classification with custom settings."""
        manager = RetryManager(
            retryable_exceptions={ValueError}, non_retryable_exceptions={ConnectionError}
        )

        # Custom retryable
        assert manager.is_retryable(ValueError("Now retryable"))

        # Custom non-retryable
        assert not manager.is_retryable(ConnectionError("Now non-retryable"))

    def test_extract_retry_after_none(self):
        """Test retry-after extraction when not available."""
        manager = RetryManager()

        # Standard exceptions without retry-after
        assert manager.extract_retry_after(ValueError("Error")) is None
        assert manager.extract_retry_after(ConnectionError("Error")) is None

    def test_extract_retry_after_http_exception(self):
        """Test retry-after extraction from HTTP-like exceptions."""
        manager = RetryManager()

        # Mock HTTP exception with response
        class MockHTTPError(Exception):
            def __init__(self, response):
                self.response = response

        class MockResponse:
            def __init__(self, headers):
                self.headers = headers

        # With retry-after header
        response = MockResponse({"retry-after": "30"})
        exception = MockHTTPError(response)
        assert manager.extract_retry_after(exception) == 30.0

        # Without retry-after header
        response = MockResponse({})
        exception = MockHTTPError(response)
        assert manager.extract_retry_after(exception) is None

    def test_execute_with_retry_success_immediately(self):
        """Test successful execution without retries."""
        manager = RetryManager()

        def successful_function():
            return "success"

        result = manager.execute_with_retry(successful_function)
        assert result == "success"

    def test_execute_with_retry_success_after_retries(self):
        """Test successful execution after some failures."""
        manager = RetryManager(base_delay=0.01)  # Fast retries for testing

        call_count = 0

        def function_with_transient_failures():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Transient error")
            return "success"

        with patch("time.sleep"):  # Mock sleep to speed up test
            result = manager.execute_with_retry(function_with_transient_failures)

        assert result == "success"
        assert call_count == 3

    def test_execute_with_retry_exhausted(self):
        """Test retry exhaustion with persistent failures."""
        manager = RetryManager(max_retries=2, base_delay=0.01)

        call_count = 0

        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Persistent error")

        with patch("time.sleep"):  # Mock sleep to speed up test
            with pytest.raises(ConnectionError):
                manager.execute_with_retry(always_failing_function)

        assert call_count == 3  # Initial + 2 retries

    def test_execute_with_retry_non_retryable(self):
        """Test immediate failure for non-retryable exceptions."""
        manager = RetryManager()

        call_count = 0

        def function_with_non_retryable_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-retryable error")

        with pytest.raises(ValueError):
            manager.execute_with_retry(function_with_non_retryable_error)

        assert call_count == 1  # Should not retry

    def test_execute_with_retry_with_args_kwargs(self):
        """Test retry execution with function arguments."""
        manager = RetryManager()

        def function_with_args(arg1, arg2, kwarg1=None):
            return f"{arg1}-{arg2}-{kwarg1}"

        result = manager.execute_with_retry(function_with_args, "test", "value", kwarg1="keyword")
        assert result == "test-value-keyword"

    @pytest.mark.asyncio
    async def test_execute_with_retry_async_success(self):
        """Test async retry execution with immediate success."""
        manager = RetryManager()

        async def async_successful_function():
            return "async_success"

        result = await manager.execute_with_retry_async(async_successful_function)
        assert result == "async_success"

    @pytest.mark.asyncio
    async def test_execute_with_retry_async_with_retries(self):
        """Test async retry execution with eventual success."""
        manager = RetryManager(base_delay=0.01)

        call_count = 0

        async def async_function_with_failures():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Async transient error")
            return "async_success"

        with patch("asyncio.sleep", new_callable=AsyncMock):  # Mock async sleep
            result = await manager.execute_with_retry_async(async_function_with_failures)

        assert result == "async_success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_execute_with_retry_async_exhausted(self):
        """Test async retry exhaustion."""
        manager = RetryManager(max_retries=1, base_delay=0.01)

        call_count = 0

        async def always_failing_async_function():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Persistent async error")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(ConnectionError):
                await manager.execute_with_retry_async(always_failing_async_function)

        assert call_count == 2  # Initial + 1 retry


class TestRetryDecorators:
    """Test the retry decorator functions."""

    def test_with_retry_decorator_default(self):
        """Test @with_retry decorator with default settings."""
        call_count = 0

        @with_retry()
        def decorated_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Retryable error")
            return "decorated_success"

        with patch("time.sleep"):  # Mock sleep
            result = decorated_function()

        assert result == "decorated_success"
        assert call_count == 3

    def test_with_retry_decorator_custom_params(self):
        """Test @with_retry decorator with custom parameters."""
        call_count = 0

        @with_retry(max_retries=1, base_delay=0.01)
        def decorated_function():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Always fails")

        with patch("time.sleep"):
            with pytest.raises(ConnectionError):
                decorated_function()

        assert call_count == 2  # Initial + 1 retry

    def test_with_retry_decorator_preserves_metadata(self):
        """Test that decorator preserves function metadata."""

        @with_retry()
        def original_function():
            """Original docstring."""
            return "result"

        assert original_function.__name__ == "original_function"
        assert original_function.__doc__ == "Original docstring."

    def test_with_retry_decorator_with_args(self):
        """Test decorator with function arguments."""

        @with_retry()
        def function_with_args(x, y, multiplier=1):
            return (x + y) * multiplier

        result = function_with_args(2, 3, multiplier=4)
        assert result == 20

    @pytest.mark.asyncio
    async def test_with_retry_async_decorator(self):
        """Test @with_retry_async decorator."""
        call_count = 0

        @with_retry_async(base_delay=0.01)
        async def async_decorated_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Async retryable error")
            return "async_decorated_success"

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await async_decorated_function()

        assert result == "async_decorated_success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_with_retry_async_decorator_preserves_metadata(self):
        """Test that async decorator preserves function metadata."""

        @with_retry_async()
        async def async_original_function():
            """Async original docstring."""
            return "async_result"

        assert async_original_function.__name__ == "async_original_function"
        assert async_original_function.__doc__ == "Async original docstring."


class TestCreateRetryManager:
    """Test the create_retry_manager factory function."""

    def test_create_retry_manager_no_settings(self):
        """Test creating retry manager without settings."""
        manager = create_retry_manager()

        # Should use defaults
        assert manager.max_retries == 3
        assert manager.base_delay == 1.0
        assert manager.max_delay == 60.0
        assert manager.exponential_base == 2.0
        assert manager.jitter is True

    def test_create_retry_manager_with_settings(self):
        """Test creating retry manager with custom settings."""
        settings = {
            "max_retries": 5,
            "base_delay": 2.0,
            "max_delay": 120.0,
            "exponential_base": 1.5,
            "jitter": False,
        }

        manager = create_retry_manager(settings)

        assert manager.max_retries == 5
        assert manager.base_delay == 2.0
        assert manager.max_delay == 120.0
        assert manager.exponential_base == 1.5
        assert manager.jitter is False

    def test_create_retry_manager_partial_settings(self):
        """Test creating retry manager with partial settings."""
        settings = {
            "max_retries": 10,
            "base_delay": 3.0,
            # Other settings should use defaults
        }

        manager = create_retry_manager(settings)

        assert manager.max_retries == 10
        assert manager.base_delay == 3.0
        assert manager.max_delay == 60.0  # Default
        assert manager.exponential_base == 2.0  # Default
        assert manager.jitter is True  # Default


class TestRetryManagerWithRealWorld:
    """Test RetryManager with realistic scenarios."""

    def test_http_timeout_scenario(self):
        """Test retry behavior for HTTP timeout scenarios."""
        manager = RetryManager(max_retries=3, base_delay=0.01)

        call_count = 0

        def simulate_http_request():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise TimeoutError("HTTP request timeout")
            return {"status": "success", "data": "response"}

        with patch("time.sleep"):
            result = simulate_http_request()
            # First call would succeed without retry manager
            assert result == {"status": "success", "data": "response"}

        # Reset and test with retry manager
        call_count = 0
        with patch("time.sleep"):
            result = manager.execute_with_retry(simulate_http_request)

        assert result == {"status": "success", "data": "response"}
        assert call_count == 3  # Succeeded on third attempt

    def test_api_rate_limiting_scenario(self):
        """Test retry behavior for API rate limiting."""
        manager = RetryManager(max_retries=2, base_delay=0.01)

        class RateLimitError(Exception):
            def __init__(self, retry_after):
                self.response = type(
                    "obj", (object,), {"headers": {"retry-after": str(retry_after)}}
                )
                super().__init__("Rate limited")

        call_count = 0

        def rate_limited_api_call():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitError(5)  # Rate limited, retry after 5 seconds
            return {"data": "api_response"}

        # Add RateLimitError to retryable exceptions
        manager.retryable_exceptions.add(RateLimitError)

        with patch("time.sleep") as mock_sleep:
            result = manager.execute_with_retry(rate_limited_api_call)

        assert result == {"data": "api_response"}
        assert call_count == 2
        # Should have used retry-after delay
        mock_sleep.assert_called_with(5.0)

    def test_network_connection_recovery(self):
        """Test retry behavior for network connection issues."""
        manager = RetryManager(max_retries=4, base_delay=0.01)

        network_errors = [
            ConnectionError("Connection refused"),
            OSError("Network unreachable"),
            TimeoutError("Connection timeout"),
            ConnectionError("Connection reset"),
        ]

        call_count = 0

        def unreliable_network_call():
            nonlocal call_count
            if call_count < len(network_errors):
                error = network_errors[call_count]
                call_count += 1
                raise error
            call_count += 1
            return "network_success"

        with patch("time.sleep"):
            result = manager.execute_with_retry(unreliable_network_call)

        assert result == "network_success"
        assert call_count == 5  # 4 failures + 1 success

    def test_mixed_error_types(self):
        """Test handling mixed retryable and non-retryable errors."""
        manager = RetryManager(max_retries=3, base_delay=0.01)

        errors = [
            ConnectionError("Retryable"),
            ValueError("Non-retryable"),  # Should stop here
        ]

        call_count = 0

        def mixed_error_function():
            nonlocal call_count
            if call_count < len(errors):
                error = errors[call_count]
                call_count += 1
                raise error
            return "should_not_reach"

        with patch("time.sleep"):
            with pytest.raises(ValueError):
                manager.execute_with_retry(mixed_error_function)

        assert call_count == 2  # Should stop at ValueError

    def test_performance_under_load(self):
        """Test retry manager performance with multiple operations."""
        manager = RetryManager(max_retries=1, base_delay=0.001)

        def fast_operation(operation_id):
            if operation_id % 10 == 0:  # 10% failure rate
                raise ConnectionError("Simulated failure")
            return f"result_{operation_id}"

        start_time = time.time()

        with patch("time.sleep"):  # Remove actual delays
            results = []
            for i in range(100):
                try:
                    result = manager.execute_with_retry(fast_operation, i)
                    results.append(result)
                except ConnectionError:
                    results.append(f"failed_{i}")

        duration = time.time() - start_time

        # Should complete quickly
        assert duration < 1.0
        assert len(results) == 100

        # Check mix of successes and failures
        successes = [r for r in results if r.startswith("result_")]
        failures = [r for r in results if r.startswith("failed_")]
        assert len(successes) > 80  # Most should succeed
        assert len(failures) > 0  # Some should fail


class TestRetryManagerEdgeCases:
    """Test edge cases and error conditions."""

    def test_zero_max_retries(self):
        """Test behavior with zero max retries."""
        manager = RetryManager(max_retries=0)

        call_count = 0

        def failing_function():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            manager.execute_with_retry(failing_function)

        assert call_count == 1  # No retries

    def test_negative_delays(self):
        """Test handling of negative delay values."""
        manager = RetryManager(base_delay=-1.0)

        # Should handle negative delays gracefully
        delay = manager.calculate_delay(0)
        assert delay >= 0  # Should not be negative

    def test_very_large_delays(self):
        """Test handling of very large delay calculations."""
        manager = RetryManager(
            base_delay=1000.0,
            exponential_base=10.0,
            max_delay=5.0,  # Much smaller max
        )

        # Should be capped at max_delay
        delay = manager.calculate_delay(10)
        assert delay == 5.0

    def test_empty_exception_sets(self):
        """Test behavior with empty exception sets."""
        manager = RetryManager(retryable_exceptions=set(), non_retryable_exceptions=set())

        # No exceptions should be retryable
        assert not manager.is_retryable(ConnectionError("Error"))
        assert not manager.is_retryable(ValueError("Error"))

    def test_function_returning_none(self):
        """Test retry with function returning None."""
        manager = RetryManager()

        def function_returning_none():
            return None

        result = manager.execute_with_retry(function_returning_none)
        assert result is None

    def test_function_with_exception_in_finally(self):
        """Test retry with function that has exception in finally block."""
        manager = RetryManager(max_retries=1, base_delay=0.01)

        call_count = 0

        def function_with_finally_exception():
            nonlocal call_count
            call_count += 1
            try:
                if call_count == 1:
                    raise ConnectionError("Retryable error")
                return "success"
            finally:
                # This finally block should not interfere with retry logic
                pass

        with patch("time.sleep"):
            result = manager.execute_with_retry(function_with_finally_exception)

        assert result == "success"
        assert call_count == 2
