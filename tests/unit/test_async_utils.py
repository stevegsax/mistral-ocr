"""Unit tests for async utilities."""

import asyncio
import functools
import time
from unittest.mock import MagicMock, patch

import pytest

from mistral_ocr.async_utils import (
    AsyncAPIManager,
    ConcurrentJobProcessor,
    run_async_in_sync_context,
    async_method_wrapper
)


class TestAsyncAPIManager:
    """Test AsyncAPIManager functionality."""

    @pytest.fixture
    def manager(self):
        """Create AsyncAPIManager instance for testing."""
        return AsyncAPIManager(max_concurrent_requests=3)

    def test_init_creates_semaphore_and_executor(self, manager):
        """Test AsyncAPIManager initialization."""
        assert manager.max_concurrent_requests == 3
        assert manager.semaphore._value == 3  # Initial semaphore count
        assert manager.executor is not None

    @pytest.mark.asyncio
    async def test_run_sync_in_executor_executes_function(self, manager):
        """Test running sync function in executor."""
        def sync_function(x, y):
            return x + y
        
        result = await manager.run_sync_in_executor(sync_function, 5, 3)
        
        assert result == 8

    @pytest.mark.asyncio
    async def test_run_sync_in_executor_with_kwargs(self, manager):
        """Test running sync function in executor with kwargs."""
        def sync_function(x, y=10):
            return x * y
        
        result = await manager.run_sync_in_executor(sync_function, 5, y=3)
        
        assert result == 15

    @pytest.mark.asyncio
    async def test_run_concurrent_operations_executes_all(self, manager):
        """Test concurrent operations execution."""
        def operation(value):
            return value * 2
        
        operations = [functools.partial(operation, i) for i in range(5)]
        results = await manager.run_concurrent_operations(operations)
        
        assert len(results) == 5
        assert results == [0, 2, 4, 6, 8]

    @pytest.mark.asyncio
    async def test_run_concurrent_operations_respects_rate_limit(self, manager):
        """Test concurrent operations respect rate limiting."""
        call_times = []
        
        def slow_operation(value):
            call_times.append(time.time())
            time.sleep(0.1)  # Small delay to test concurrency
            return value
        
        operations = [functools.partial(slow_operation, i) for i in range(5)]
        start_time = time.time()
        results = await manager.run_concurrent_operations(operations)
        end_time = time.time()
        
        assert len(results) == 5
        assert results == [0, 1, 2, 3, 4]
        
        # Should take less time than sequential execution due to concurrency
        # but respect the rate limit (max 3 concurrent)
        total_time = end_time - start_time
        assert total_time < 0.5  # Less than sequential (5 * 0.1 = 0.5s)

    @pytest.mark.asyncio
    async def test_run_concurrent_operations_handles_exceptions(self, manager):
        """Test concurrent operations handle exceptions properly."""
        def operation(value):
            if value == 2:
                raise ValueError(f"Error for value {value}")
            return value * 2
        
        operations = [functools.partial(operation, i) for i in range(5)]
        results = await manager.run_concurrent_operations(operations, return_exceptions=True)
        
        assert len(results) == 5
        assert results[0] == 0
        assert results[1] == 2
        assert isinstance(results[2], ValueError)
        assert results[3] == 6
        assert results[4] == 8

    @pytest.mark.asyncio
    async def test_run_concurrent_operations_without_exception_handling(self, manager):
        """Test concurrent operations without exception handling."""
        def operation(value):
            if value == 2:
                raise ValueError(f"Error for value {value}")
            return value * 2
        
        operations = [functools.partial(operation, i) for i in range(5)]
        
        with pytest.raises(ValueError, match="Error for value 2"):
            await manager.run_concurrent_operations(operations, return_exceptions=False)

    @pytest.mark.asyncio
    async def test_run_concurrent_with_progress_tracks_progress(self, manager):
        """Test concurrent operations with progress tracking."""
        progress_updates = []
        
        def progress_callback(completed, total):
            progress_updates.append((completed, total))
        
        def operation(value):
            time.sleep(0.05)  # Small delay
            return value * 2
        
        operations = [functools.partial(operation, i) for i in range(3)]
        results = await manager.run_concurrent_with_progress(operations, progress_callback)
        
        assert len(results) == 3
        assert results == [0, 2, 4]
        
        # Should have progress updates
        assert len(progress_updates) == 3
        assert (1, 3) in progress_updates
        assert (2, 3) in progress_updates
        assert (3, 3) in progress_updates

    @pytest.mark.asyncio
    async def test_run_concurrent_with_progress_handles_exceptions(self, manager):
        """Test concurrent operations with progress handling exceptions."""
        progress_updates = []
        
        def progress_callback(completed, total):
            progress_updates.append((completed, total))
        
        def operation(value):
            if value == 1:
                raise ValueError(f"Error for value {value}")
            return value * 2
        
        operations = [functools.partial(operation, i) for i in range(3)]
        results = await manager.run_concurrent_with_progress(operations, progress_callback)
        
        assert len(results) == 3
        assert results[0] == 0
        assert isinstance(results[1], ValueError)
        assert results[2] == 4
        
        # Should still track progress even with exceptions
        assert len(progress_updates) == 3
        assert (3, 3) in progress_updates

    def test_close_shuts_down_executor(self, manager):
        """Test close method shuts down executor."""
        manager.close()
        
        # Executor should be shut down
        assert manager.executor._shutdown


class TestConcurrentJobProcessor:
    """Test ConcurrentJobProcessor functionality."""

    @pytest.fixture
    def processor(self):
        """Create ConcurrentJobProcessor instance for testing."""
        return ConcurrentJobProcessor(max_concurrent=2)

    def test_init_creates_async_manager(self, processor):
        """Test ConcurrentJobProcessor initialization."""
        assert processor.async_manager is not None
        assert processor.async_manager.max_concurrent_requests == 2

    @pytest.mark.asyncio
    async def test_refresh_job_statuses_async_filters_correctly(self, processor):
        """Test async job status refresh filters jobs correctly."""
        # Mock job manager
        mock_job_manager = MagicMock()
        mock_job_manager.check_job_status.side_effect = lambda job_id: {
            "job1": "completed",
            "job2": "failed", 
            "job3": "running"
        }.get(job_id, "unknown")
        
        from mistral_ocr.types import JobInfo
        jobs = [
            JobInfo(id="job1", status="running", submitted="2024-01-01T10:00:00Z"),
            JobInfo(id="job2", status="pending", submitted="2024-01-01T10:00:00Z"),
            JobInfo(id="job3", status="processing", submitted="2024-01-01T10:00:00Z")
        ]
        
        skip_statuses = {"SUCCESS", "COMPLETED", "FAILED"}
        
        result = await processor.refresh_job_statuses_async(
            mock_job_manager, jobs, skip_statuses
        )
        
        assert len(result) == 3
        
        # Verify statuses were updated
        job_statuses = {job["id"]: job["status"] for job in result}
        assert job_statuses["job1"] == "completed"
        assert job_statuses["job2"] == "failed"
        assert job_statuses["job3"] == "running"

    @pytest.mark.asyncio
    async def test_refresh_job_statuses_async_skips_final_statuses(self, processor):
        """Test async job status refresh skips final statuses."""
        # Mock job manager
        mock_job_manager = MagicMock()
        call_count = 0
        
        def mock_check_status(job_id):
            nonlocal call_count
            call_count += 1
            return "completed"
        
        mock_job_manager.check_job_status.side_effect = mock_check_status
        
        from mistral_ocr.types import JobInfo
        jobs = [
            JobInfo(id="job1", status="SUCCESS", submitted="2024-01-01T10:00:00Z"),  # Should be skipped
            JobInfo(id="job2", status="running", submitted="2024-01-01T10:00:00Z"),   # Should be refreshed
            JobInfo(id="job3", status="FAILED", submitted="2024-01-01T10:00:00Z")     # Should be skipped
        ]
        
        skip_statuses = {"SUCCESS", "FAILED", "COMPLETED"}
        
        result = await processor.refresh_job_statuses_async(
            mock_job_manager, jobs, skip_statuses
        )
        
        assert len(result) == 3
        # Only job2 should have been checked (call_count = 1)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_refresh_job_statuses_async_handles_exceptions(self, processor):
        """Test async job status refresh handles individual job exceptions."""
        # Mock job manager with exception for one job
        mock_job_manager = MagicMock()
        
        def mock_check_status(job_id):
            if job_id == "job2":
                raise Exception("API error")
            return "completed"
        
        mock_job_manager.check_job_status.side_effect = mock_check_status
        
        from mistral_ocr.types import JobInfo
        jobs = [
            JobInfo(id="job1", status="running", submitted="2024-01-01T10:00:00Z"),
            JobInfo(id="job2", status="processing", submitted="2024-01-01T10:00:00Z"),
            JobInfo(id="job3", status="pending", submitted="2024-01-01T10:00:00Z")
        ]
        
        skip_statuses = set()
        
        result = await processor.refresh_job_statuses_async(
            mock_job_manager, jobs, skip_statuses
        )
        
        assert len(result) == 3
        
        # job1 and job3 should be updated, job2 should keep original status
        job_statuses = {job["id"]: job["status"] for job in result}
        assert job_statuses["job1"] == "completed"
        assert job_statuses["job2"] == "processing"  # Unchanged due to exception
        assert job_statuses["job3"] == "completed"

    @pytest.mark.asyncio
    async def test_download_multiple_results_async_processes_all_jobs(self, processor):
        """Test async result download processes all jobs."""
        # Mock result manager
        mock_result_manager = MagicMock()
        
        def mock_download(job_id, destination=None):
            return f"Downloaded {job_id}"
        
        mock_result_manager.download_results.side_effect = mock_download
        
        job_ids = ["job1", "job2", "job3"]
        destination = "/tmp/results"
        
        results = await processor.download_multiple_results_async(
            mock_result_manager, job_ids, destination
        )
        
        assert len(results) == 3
        assert results == ["Downloaded job1", "Downloaded job2", "Downloaded job3"]

    @pytest.mark.asyncio
    async def test_download_multiple_results_async_handles_exceptions(self, processor):
        """Test async result download handles individual job exceptions."""
        # Mock result manager with exception for one job
        mock_result_manager = MagicMock()
        
        def mock_download(job_id, destination=None):
            if job_id == "job2":
                raise Exception(f"Download failed for {job_id}")
            return f"Downloaded {job_id}"
        
        mock_result_manager.download_results.side_effect = mock_download
        
        job_ids = ["job1", "job2", "job3"]
        
        results = await processor.download_multiple_results_async(
            mock_result_manager, job_ids
        )
        
        assert len(results) == 3
        assert results[0] == "Downloaded job1"
        assert isinstance(results[1], Exception)
        assert "Download failed for job2" in str(results[1])
        assert results[2] == "Downloaded job3"

    def test_close_cleans_up_resources(self, processor):
        """Test close method cleans up resources."""
        processor.close()
        
        # Should close the async manager
        assert processor.async_manager.executor._shutdown


class TestRunAsyncInSyncContext:
    """Test run_async_in_sync_context functionality."""

    def test_run_async_function_in_sync_context(self):
        """Test running async function in sync context."""
        async def async_function(x, y):
            await asyncio.sleep(0.01)  # Small async operation
            return x + y
        
        result = run_async_in_sync_context(async_function, 5, 3)
        
        assert result == 8

    def test_run_async_function_with_kwargs(self):
        """Test running async function with kwargs in sync context."""
        async def async_function(x, y=10):
            await asyncio.sleep(0.01)
            return x * y
        
        result = run_async_in_sync_context(async_function, 5, y=3)
        
        assert result == 15

    def test_run_async_function_handles_exceptions(self):
        """Test running async function handles exceptions properly."""
        async def async_function():
            await asyncio.sleep(0.01)
            raise ValueError("Async error")
        
        with pytest.raises(ValueError, match="Async error"):
            run_async_in_sync_context(async_function)

    @pytest.mark.asyncio
    async def test_run_async_in_existing_event_loop(self):
        """Test behavior when called from within existing event loop."""
        async def async_function(x):
            await asyncio.sleep(0.01)
            return x * 2
        
        # This should work even when called from within an async context
        # by using a thread pool
        result = run_async_in_sync_context(async_function, 5)
        
        assert result == 10


class TestAsyncMethodWrapper:
    """Test async_method_wrapper decorator functionality."""

    def test_async_method_wrapper_preserves_original_method(self):
        """Test wrapper preserves original method functionality."""
        @async_method_wrapper(max_concurrent=2)
        def test_method(self, value):
            return value * 2
        
        mock_self = MagicMock()
        result = test_method(mock_self, 5)
        
        assert result == 10

    def test_async_method_wrapper_adds_async_attribute(self):
        """Test wrapper adds async method attribute."""
        @async_method_wrapper(max_concurrent=2)
        def check_status(self, job_id):
            return f"Status for {job_id}"
        
        assert hasattr(check_status, '_has_async_batch')
        assert check_status._has_async_batch is True
        assert hasattr(check_status, '_async_method_name')

    def test_async_method_wrapper_creates_correct_async_name(self):
        """Test wrapper creates correct async method names."""
        @async_method_wrapper(max_concurrent=2)
        def check_job_status(self, job_id):
            return f"Status for {job_id}"
        
        assert check_job_status._async_method_name == "check_job_statuses_async"
        
        @async_method_wrapper(max_concurrent=2)
        def get_results(self, job_id):
            return f"Results for {job_id}"
        
        assert get_results._async_method_name == "get_multiple_results_async"
        
        @async_method_wrapper(max_concurrent=2)
        def process_item(self, item):
            return f"Processed {item}"
        
        assert process_item._async_method_name == "process_item_batch_async"

    @pytest.mark.asyncio
    async def test_async_method_wrapper_batch_functionality(self):
        """Test wrapper's async batch functionality."""
        call_log = []
        
        @async_method_wrapper(max_concurrent=2)
        def process_item(self, item):
            call_log.append(item)
            return f"Processed {item}"
        
        # Create a real object to avoid MagicMock issues with hasattr
        class MockSelf:
            pass
        mock_self = MockSelf()
        
        # Get the async batch method
        async_method = getattr(process_item, process_item._async_method_name)
        
        items = ["item1", "item2", "item3"]
        results = await async_method(mock_self, items)
        
        assert len(results) == 3
        assert results == ["Processed item1", "Processed item2", "Processed item3"]
        assert set(call_log) == set(items)

    @pytest.mark.asyncio
    async def test_async_method_wrapper_with_progress_callback(self):
        """Test wrapper's async functionality with progress callback."""
        progress_updates = []
        
        def progress_callback(completed, total):
            progress_updates.append((completed, total))
        
        @async_method_wrapper(max_concurrent=2)
        def process_item(self, item):
            time.sleep(0.01)  # Small delay
            return f"Processed {item}"
        
        # Create a real object to avoid MagicMock issues with hasattr
        class MockSelf:
            pass
        mock_self = MockSelf()
        
        # Get the async batch method
        async_method = getattr(process_item, process_item._async_method_name)
        
        items = ["item1", "item2", "item3"]
        results = await async_method(mock_self, items, progress_callback)
        
        assert len(results) == 3
        assert len(progress_updates) == 3
        assert (3, 3) in progress_updates


class TestIntegrationScenarios:
    """Integration tests for async utilities working together."""

    @pytest.mark.asyncio
    async def test_concurrent_job_processing_realistic_scenario(self):
        """Test realistic concurrent job processing scenario."""
        # Simulate a job manager with realistic delays
        class MockJobManager:
            def check_job_status(self, job_id):
                # Simulate API delay
                time.sleep(0.05)
                
                # Return different statuses based on job ID
                if "complete" in job_id:
                    return "completed"
                elif "fail" in job_id:
                    return "failed"
                else:
                    return "running"
        
        processor = ConcurrentJobProcessor(max_concurrent=3)
        job_manager = MockJobManager()
        
        from mistral_ocr.types import JobInfo
        jobs = [
            JobInfo(id="job_complete_1", status="running", submitted="2024-01-01T10:00:00Z"),
            JobInfo(id="job_fail_1", status="processing", submitted="2024-01-01T10:00:00Z"),
            JobInfo(id="job_running_1", status="pending", submitted="2024-01-01T10:00:00Z"),
            JobInfo(id="job_complete_2", status="running", submitted="2024-01-01T10:00:00Z"),
            JobInfo(id="job_running_2", status="processing", submitted="2024-01-01T10:00:00Z")
        ]
        
        skip_statuses = {"SUCCESS", "FAILED"}
        
        start_time = time.time()
        result = await processor.refresh_job_statuses_async(
            job_manager, jobs, skip_statuses
        )
        end_time = time.time()
        
        # Verify results
        assert len(result) == 5
        
        job_statuses = {job["id"]: job["status"] for job in result}
        assert job_statuses["job_complete_1"] == "completed"
        assert job_statuses["job_fail_1"] == "failed"
        assert job_statuses["job_running_1"] == "running"
        assert job_statuses["job_complete_2"] == "completed"
        assert job_statuses["job_running_2"] == "running"
        
        # Should be faster than sequential (5 * 0.05 = 0.25s)
        total_time = end_time - start_time
        assert total_time < 0.2  # Should be much faster due to concurrency
        
        processor.close()

    def test_sync_to_async_bridge_realistic_scenario(self):
        """Test sync to async bridge in realistic scenario."""
        async def async_operation(items):
            manager = AsyncAPIManager(max_concurrent_requests=2)
            
            def process_item(item):
                time.sleep(0.02)  # Simulate processing
                return f"processed_{item}"
            
            operations = [functools.partial(process_item, item) for item in items]
            results = await manager.run_concurrent_operations(operations)
            manager.close()
            return results
        
        items = ["a", "b", "c", "d", "e"]
        
        start_time = time.time()
        results = run_async_in_sync_context(async_operation, items)
        end_time = time.time()
        
        assert len(results) == 5
        assert results == ["processed_a", "processed_b", "processed_c", "processed_d", "processed_e"]
        
        # Should be faster than sequential (5 * 0.02 = 0.1s) due to concurrency
        total_time = end_time - start_time
        assert total_time < 0.09  # Slightly more lenient for CI environments