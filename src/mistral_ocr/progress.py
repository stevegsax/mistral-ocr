"""
Progress monitoring and real-time updates for Mistral OCR operations.

This module provides comprehensive progress tracking capabilities including:
- Progress bars for batch submissions and downloads
- Real-time job status monitoring
- Concurrent operation displays
- Status change notifications
"""

import time
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table

from .constants import FINAL_JOB_STATUSES


class ProgressManager:
    """
    Central manager for all progress tracking in mistral-ocr.

    Provides progress bars, real-time monitoring, and status displays
    for long-running operations like file processing and API calls.
    """

    def __init__(self, console: Optional[Console] = None, enabled: bool = False) -> None:
        """
        Initialize the progress manager.

        Args:
            console: Rich console instance, creates new one if None
            enabled: Whether progress displays are enabled (default False for file-only logging)
        """
        self.console = console or Console(file=None) if enabled else None
        self.enabled = enabled
        self._active_progress: Optional[Progress] = None
        self._active_live: Optional[Live] = None

    @contextmanager
    def create_progress(
        self,
        show_speed: bool = False,
        show_download: bool = False,
        show_time: bool = True,
    ) -> Iterator[Progress]:
        """
        Create a progress context for tracking operations.

        Args:
            show_speed: Whether to show transfer speed column
            show_download: Whether to show download-specific columns
            show_time: Whether to show time elapsed/remaining

        Yields:
            Progress instance for tracking tasks
        """
        if not self.enabled:
            # Create a dummy progress that does nothing
            yield DummyProgress()
            return

        columns = [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ]

        if show_download:
            columns.append(DownloadColumn())

        if show_speed:
            columns.append(TransferSpeedColumn())

        if show_time:
            columns.extend([TimeElapsedColumn(), TimeRemainingColumn()])

        progress = Progress(*columns, console=self.console)
        self._active_progress = progress

        try:
            with progress:
                yield progress
        finally:
            self._active_progress = None

    def create_submission_progress(self) -> "SubmissionProgressTracker":
        """Create a progress tracker for batch submission operations."""
        return SubmissionProgressTracker(self)

    def create_download_progress(self) -> "DownloadProgressTracker":
        """Create a progress tracker for download operations."""
        return DownloadProgressTracker(self)

    def create_job_monitor(self) -> "LiveJobMonitor":
        """Create a live job status monitor."""
        return LiveJobMonitor(self)


class DummyProgress:
    """Dummy progress for when progress is disabled."""

    def add_task(self, *args: Any, **kwargs: Any) -> TaskID:
        return TaskID(0)

    def update(self, *args: Any, **kwargs: Any) -> None:
        pass

    def advance(self, *args: Any, **kwargs: Any) -> None:
        pass

    def remove_task(self, *args: Any, **kwargs: Any) -> None:
        pass


class SubmissionProgressTracker:
    """Tracks progress for batch submission operations."""

    def __init__(self, manager: ProgressManager) -> None:
        self.manager = manager
        self._file_collection_task: Optional[TaskID] = None
        self._encoding_task: Optional[TaskID] = None
        self._upload_tasks: Dict[str, TaskID] = {}
        self._job_creation_task: Optional[TaskID] = None

    @contextmanager
    def track_submission(self, total_files: int, batch_count: int) -> Iterator[Any]:
        """
        Track complete submission process with multiple phases.

        Args:
            total_files: Total number of files to process
            batch_count: Number of batches to create
        """
        with self.manager.create_progress(show_time=True) as progress:
            yield SubmissionProgressContext(progress, total_files, batch_count)

    def track_file_collection(self, progress: Progress, total_expected: int) -> TaskID:
        """Track file collection progress."""
        return progress.add_task(
            "Collecting files...", total=total_expected if total_expected > 0 else None
        )

    def track_encoding(self, progress: Progress, total_files: int) -> TaskID:
        """Track file encoding progress."""
        return progress.add_task("Encoding files...", total=total_files)

    def track_upload(self, progress: Progress, filename: str, file_size: int) -> TaskID:
        """Track individual file upload progress."""
        return progress.add_task(f"Uploading {filename}...", total=file_size)

    def track_job_creation(self, progress: Progress, batch_count: int) -> TaskID:
        """Track batch job creation progress."""
        return progress.add_task("Creating jobs...", total=batch_count)


class SubmissionProgressContext:
    """Context for tracking submission progress with convenient methods."""

    def __init__(self, progress: Progress, total_files: int, batch_count: int) -> None:
        self.progress = progress
        self.total_files = total_files
        self.batch_count = batch_count

        # Create tasks
        self.collection_task = progress.add_task(
            "Collecting files...", total=total_files if total_files > 0 else None
        )
        self.encoding_task = progress.add_task("Encoding files...", total=total_files)
        self.job_creation_task = progress.add_task("Creating jobs...", total=batch_count)

        # Upload tasks created on demand
        self.upload_tasks: Dict[str, TaskID] = {}

    def update_collection(self, completed: int) -> None:
        """Update file collection progress."""
        self.progress.update(self.collection_task, completed=completed)

    def complete_collection(self, total_found: int) -> None:
        """Complete file collection phase."""
        self.progress.update(self.collection_task, completed=total_found, total=total_found)

    def update_encoding(self, completed: int) -> None:
        """Update file encoding progress."""
        self.progress.update(self.encoding_task, completed=completed)

    def complete_encoding(self) -> None:
        """Complete encoding phase."""
        self.progress.update(self.encoding_task, completed=self.total_files)

    def start_upload(self, filename: str, file_size: int) -> TaskID:
        """Start tracking an upload."""
        task_id = self.progress.add_task(f"Uploading {filename}...", total=file_size)
        self.upload_tasks[filename] = task_id
        return task_id

    def update_upload(self, filename: str, completed: int) -> None:
        """Update upload progress."""
        if filename in self.upload_tasks:
            self.progress.update(self.upload_tasks[filename], completed=completed)

    def complete_upload(self, filename: str) -> None:
        """Complete an upload."""
        if filename in self.upload_tasks:
            task_id = self.upload_tasks[filename]
            self.progress.remove_task(task_id)
            del self.upload_tasks[filename]

    def update_job_creation(self, completed: int) -> None:
        """Update job creation progress."""
        self.progress.update(self.job_creation_task, completed=completed)

    def complete_job_creation(self) -> None:
        """Complete job creation phase."""
        self.progress.update(self.job_creation_task, completed=self.batch_count)


class DownloadProgressTracker:
    """Tracks progress for download operations."""

    def __init__(self, manager: ProgressManager) -> None:
        self.manager = manager

    @contextmanager
    def track_downloads(self, job_count: int) -> Iterator[Any]:
        """
        Track multiple download operations.

        Args:
            job_count: Number of jobs to download
        """
        with self.manager.create_progress(show_download=True, show_speed=True) as progress:
            yield DownloadProgressContext(progress, job_count)


class DownloadProgressContext:
    """Context for tracking download progress."""

    def __init__(self, progress: Progress, job_count: int) -> None:
        self.progress = progress
        self.job_count = job_count
        self.download_tasks: Dict[str, TaskID] = {}

        # Overall progress task
        self.overall_task = progress.add_task(f"Downloading {job_count} jobs...", total=job_count)

    def start_download(self, job_id: str, file_size: Optional[int] = None) -> TaskID:
        """Start tracking a download."""
        task_id = self.progress.add_task(f"Downloading {job_id[:8]}...", total=file_size)
        self.download_tasks[job_id] = task_id
        return task_id

    def update_download(self, job_id: str, completed: int) -> None:
        """Update download progress."""
        if job_id in self.download_tasks:
            self.progress.update(self.download_tasks[job_id], completed=completed)

    def complete_download(self, job_id: str) -> None:
        """Complete a download."""
        if job_id in self.download_tasks:
            task_id = self.download_tasks[job_id]
            self.progress.remove_task(task_id)
            del self.download_tasks[job_id]

        # Update overall progress
        completed = self.job_count - len(self.download_tasks)
        self.progress.update(self.overall_task, completed=completed)


class LiveJobMonitor:
    """Provides real-time monitoring of job statuses."""

    def __init__(self, manager: ProgressManager) -> None:
        self.manager = manager
        self.console = manager.console
        self._last_statuses: Dict[str, str] = {}

    def monitor_jobs(
        self,
        job_ids: List[str],
        refresh_interval: int = 10,
        auto_exit: bool = True,
    ) -> None:
        """
        Monitor job statuses with live updates.

        Args:
            job_ids: List of job IDs to monitor
            refresh_interval: Seconds between status refreshes
            auto_exit: Whether to exit when all jobs complete
        """
        if not self.manager.enabled:
            self.console.print("Job monitoring disabled in quiet mode")
            return

        # Import here to avoid circular dependencies
        from .client import MistralOCRClient
        from .settings import get_settings

        settings = get_settings()
        api_key = settings.get_api_key_optional()
        if not api_key:
            self.console.print("❌ No API key available for monitoring")
            return

        try:
            client = MistralOCRClient(api_key=api_key, settings=settings)
            self._run_monitor_loop(client, job_ids, refresh_interval, auto_exit)
        except Exception as e:
            self.console.print(f"❌ Failed to start monitoring: {e}")

    def _run_monitor_loop(
        self,
        client: Any,
        job_ids: List[str],
        refresh_interval: int,
        auto_exit: bool,
    ) -> None:
        """Run the main monitoring loop."""
        start_time = time.time()

        with Live(
            self._create_status_table(job_ids, {}),
            console=self.console,
            refresh_per_second=0.5,
        ) as live:
            while True:
                try:
                    # Refresh job statuses
                    current_statuses = self._refresh_job_statuses(client, job_ids)

                    # Detect and announce status changes
                    self._detect_status_changes(current_statuses)

                    # Update display
                    live.update(self._create_status_table(job_ids, current_statuses, start_time))

                    # Check exit conditions
                    if auto_exit and self._all_jobs_complete(current_statuses):
                        break

                    # Wait for next refresh
                    time.sleep(refresh_interval)

                except KeyboardInterrupt:
                    self.console.print("\n⏹️  Monitoring stopped by user")
                    break
                except Exception as e:
                    self.console.print(f"\n❌ Monitoring error: {e}")
                    time.sleep(refresh_interval)

    def _refresh_job_statuses(self, client: Any, job_ids: List[str]) -> Dict[str, str]:
        """Refresh statuses for all monitored jobs."""
        statuses = {}
        for job_id in job_ids:
            try:
                status = client.check_job_status(job_id)
                statuses[job_id] = status
            except Exception as e:
                statuses[job_id] = f"error: {e}"
        return statuses

    def _detect_status_changes(self, current_statuses: Dict[str, str]) -> None:
        """Detect and announce status changes."""
        for job_id, current_status in current_statuses.items():
            previous_status = self._last_statuses.get(job_id)
            if previous_status and previous_status != current_status:
                self._announce_status_change(job_id, previous_status, current_status)

        self._last_statuses = current_statuses.copy()

    def _announce_status_change(self, job_id: str, old_status: str, new_status: str) -> None:
        """Announce a status change."""
        status_emoji = {
            "completed": "✅",
            "failed": "❌",
            "running": "🔄",
            "pending": "⏳",
            "cancelled": "⏹️",
        }

        emoji = status_emoji.get(new_status.lower(), "📋")
        self.console.print(f"{emoji} {job_id[:8]}... changed from {old_status} to {new_status}")

    def _all_jobs_complete(self, statuses: Dict[str, str]) -> bool:
        """Check if all jobs have completed."""
        # Create uppercase version of final statuses for consistent comparison
        final_statuses_upper = {status.upper() for status in FINAL_JOB_STATUSES}
        return all(status.upper() in final_statuses_upper for status in statuses.values())

    def _create_status_table(
        self,
        job_ids: List[str],
        statuses: Dict[str, str],
        start_time: Optional[float] = None,
    ) -> Panel:
        """Create a rich table showing job statuses."""
        table = Table(title="Live Job Monitor", show_header=True, header_style="bold")

        table.add_column("Job ID", style="cyan", width=12)
        table.add_column("Status", style="green", width=12)
        table.add_column("Updated", style="yellow", width=15)

        current_time = time.time()

        for job_id in job_ids:
            status = statuses.get(job_id, "unknown")
            job_display = job_id[:8] + "..." if len(job_id) > 8 else job_id

            # Status with emoji
            status_display = self._format_status(status)

            # Time since start
            if start_time:
                elapsed = int(current_time - start_time)
                time_display = f"{elapsed}s ago"
            else:
                time_display = "just now"

            table.add_row(job_display, status_display, time_display)

        # Add summary footer
        if statuses:
            completed = sum(1 for s in statuses.values() if s.upper() in FINAL_JOB_STATUSES)
            total = len(statuses)
            footer_text = f"Progress: {completed}/{total} jobs completed"
            if start_time:
                elapsed = int(current_time - start_time)
                footer_text += f" • Monitoring for {elapsed}s"
        else:
            footer_text = "Waiting for status updates..."

        return Panel(
            table,
            subtitle=footer_text,
            border_style="blue",
        )

    def _format_status(self, status: str) -> str:
        """Format status with appropriate emoji and styling."""
        status_formats = {
            "completed": "✅ completed",
            "failed": "❌ failed",
            "running": "🔄 running",
            "pending": "⏳ pending",
            "cancelled": "⏹️ cancelled",
        }

        return status_formats.get(status.lower(), f"❓ {status}")


# Convenience functions for easy integration
def create_progress_manager(enabled: bool = True) -> ProgressManager:
    """Create a configured progress manager."""
    return ProgressManager(enabled=enabled)


def is_progress_supported() -> bool:
    """Check if progress displays are supported in current terminal."""
    try:
        console = Console()
        return console.is_terminal and not console.legacy_windows
    except Exception:
        return False
