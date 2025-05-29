"""Async utilities for improved API performance."""

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Awaitable, Callable, List, Optional, TypeVar, Union

import structlog

F = TypeVar("F", bound=Callable[..., Any])


class AsyncAPIManager:
    """Manager for async API operations with thread pool fallback."""

    def __init__(self, max_concurrent_requests: int = 10) -> None:
        """Initialize async manager.

        Args:
            max_concurrent_requests: Maximum concurrent API requests
        """
        self.max_concurrent_requests = max_concurrent_requests
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_requests)
        self.logger = structlog.get_logger(__name__)

    async def run_sync_in_executor(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Run a synchronous function in a thread pool executor.

        Args:
            func: Synchronous function to run
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function call
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, functools.partial(func, *args, **kwargs))

    async def run_concurrent_operations(
        self, operations: List[Callable[[], Any]], return_exceptions: bool = True
    ) -> List[Any]:
        """Run multiple operations concurrently with rate limiting.

        Args:
            operations: List of callable operations to run
            return_exceptions: Whether to return exceptions or raise them

        Returns:
            List of results from operations
        """

        async def limited_operation(operation: Callable[[], Any]) -> Any:
            async with self.semaphore:
                return await self.run_sync_in_executor(operation)

        tasks = [limited_operation(op) for op in operations]
        results = await asyncio.gather(*tasks, return_exceptions=return_exceptions)

        if return_exceptions:
            # Log any exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.warning(f"Operation {i} failed: {result}")

        return results

    async def run_concurrent_with_progress(
        self,
        operations: List[Callable[[], Any]],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[Any]:
        """Run operations concurrently with progress tracking.

        Args:
            operations: List of operations to run
            progress_callback: Optional callback for progress updates (completed, total)

        Returns:
            List of results
        """
        completed_count = 0
        total_count = len(operations)
        results = [None] * total_count

        async def tracked_operation(index: int, operation: Callable[[], Any]) -> None:
            nonlocal completed_count
            async with self.semaphore:
                try:
                    result = await self.run_sync_in_executor(operation)
                    results[index] = result
                except Exception as e:
                    results[index] = e
                    self.logger.warning(f"Operation {index} failed: {e}")
                finally:
                    completed_count += 1
                    if progress_callback:
                        progress_callback(completed_count, total_count)

        tasks = [tracked_operation(i, op) for i, op in enumerate(operations)]
        await asyncio.gather(*tasks, return_exceptions=True)

        return results

    def close(self) -> None:
        """Clean up the thread pool executor."""
        self.executor.shutdown(wait=True)


def async_method_wrapper(max_concurrent: int = 10):
    """Decorator to add async capabilities to synchronous methods.

    Creates an async version of a method that can handle multiple concurrent calls.
    The original method is preserved, and a new async method is added.

    Args:
        max_concurrent: Maximum number of concurrent operations

    Usage:
        @async_method_wrapper(max_concurrent=5)
        def check_job_status(self, job_id: str) -> str:
            # Original sync implementation
            return self.api_client.get_job_status(job_id)

        # This creates:
        # - Original: check_job_status(job_id) -> str
        # - New: check_job_statuses_async(job_ids) -> List[str]
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Original sync method
            return func(self, *args, **kwargs)

        # Create async batch version
        async def async_batch_method(
            self, items: List[Any], progress_callback: Optional[Callable[[int, int], None]] = None
        ) -> List[Any]:
            if not hasattr(self, "_async_manager"):
                self._async_manager = AsyncAPIManager(max_concurrent)

            # Create operations for each item
            operations = [functools.partial(func, self, item) for item in items]

            if progress_callback:
                return await self._async_manager.run_concurrent_with_progress(
                    operations, progress_callback
                )
            else:
                return await self._async_manager.run_concurrent_operations(operations)

        # Add async method to the wrapper
        method_name = func.__name__
        if method_name.endswith("_status"):
            async_name = method_name.replace("_status", "_statuses_async")
        elif method_name.startswith("get_"):
            async_name = method_name.replace("get_", "get_multiple_") + "_async"
        elif method_name.startswith("check_"):
            async_name = method_name.replace("check_", "check_multiple_") + "_async"
        else:
            async_name = f"{method_name}_batch_async"

        setattr(wrapper, async_name, async_batch_method)
        wrapper._has_async_batch = True
        wrapper._async_method_name = async_name

        return wrapper

    return decorator


def run_async_in_sync_context(async_func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
    """Run an async function in a synchronous context.

    Args:
        async_func: Async function to run
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Result of the async function
    """
    try:
        # Try to get existing event loop
        asyncio.get_running_loop()
        # If we're in an async context, we need to use a new thread
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, async_func(*args, **kwargs))
            return future.result()
    except RuntimeError:
        # No event loop running, safe to create one
        return asyncio.run(async_func(*args, **kwargs))


class ConcurrentJobProcessor:
    """Specialized processor for concurrent job operations."""

    def __init__(self, max_concurrent: int = 10) -> None:
        """Initialize processor.

        Args:
            max_concurrent: Maximum concurrent operations
        """
        self.async_manager = AsyncAPIManager(max_concurrent)
        self.logger = structlog.get_logger(__name__)

    async def refresh_job_statuses_async(
        self, job_manager, jobs: List[dict], skip_statuses: set
    ) -> List[dict]:
        """Refresh job statuses concurrently.

        Args:
            job_manager: Job manager instance with check_job_status method
            jobs: List of job dictionaries with 'id' and 'status' keys
            skip_statuses: Set of statuses to skip refreshing

        Returns:
            Updated jobs list with refreshed statuses
        """
        # Filter jobs that need refreshing
        jobs_to_refresh = [job for job in jobs if job.status not in skip_statuses]
        jobs_to_skip = [job for job in jobs if job.status in skip_statuses]

        if not jobs_to_refresh:
            self.logger.debug("No jobs require status refresh")
            return jobs

        self.logger.info(f"Refreshing status for {len(jobs_to_refresh)} jobs concurrently")

        # Create operations for status checks
        operations = [
            lambda job_id=job.id: job_manager.check_job_status(job_id) for job in jobs_to_refresh
        ]

        # Run concurrent status checks
        results = await self.async_manager.run_concurrent_operations(operations)

        # Update job statuses
        updated_count = 0
        for job, result in zip(jobs_to_refresh, results):
            if not isinstance(result, Exception) and result != job.status:
                old_status = job.status
                job.status = result
                updated_count += 1
                self.logger.debug(f"Job {job.id}: {old_status} -> {result}")

        if updated_count > 0:
            self.logger.info(f"Updated status for {updated_count} jobs")

        # Return all jobs (refreshed + skipped)
        return jobs_to_refresh + jobs_to_skip

    async def download_multiple_results_async(
        self, result_manager, job_ids: List[str], destination: Optional[Any] = None
    ) -> List[Union[str, Exception]]:
        """Download results for multiple jobs concurrently.

        Args:
            result_manager: Result manager instance
            job_ids: List of job IDs to download
            destination: Optional destination directory

        Returns:
            List of results or exceptions
        """
        self.logger.info(f"Downloading results for {len(job_ids)} jobs concurrently")

        operations = [
            lambda jid=job_id: result_manager.download_results(jid, destination)
            for job_id in job_ids
        ]

        return await self.async_manager.run_concurrent_operations(operations)

    def close(self) -> None:
        """Clean up resources."""
        self.async_manager.close()
