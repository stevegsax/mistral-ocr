"""Comprehensive tests for the progress monitoring and Rich UI system."""

import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from mistral_ocr.progress import (
    DummyProgress,
    DownloadProgressTracker,
    LiveJobMonitor,
    ProgressManager,
    SubmissionProgressTracker,
)


class TestProgressManager:
    """Test the ProgressManager class."""

    def test_progress_manager_enabled(self):
        """Test ProgressManager when progress is enabled."""
        with patch("mistral_ocr.progress.Console") as mock_console:
            manager = ProgressManager(enabled=True)
            assert manager.enabled is True
            assert manager.console is not None
            mock_console.assert_called_once()

    def test_progress_manager_disabled(self):
        """Test ProgressManager when progress is disabled."""
        with patch("mistral_ocr.progress.Console") as mock_console:
            manager = ProgressManager(enabled=False)
            assert manager.enabled is False
            assert manager.console is not None
            mock_console.assert_called_once()

    def test_progress_manager_with_custom_console(self):
        """Test ProgressManager with custom console."""
        custom_console = MagicMock()
        manager = ProgressManager(console=custom_console, enabled=True)
        assert manager.console is custom_console
        assert manager.enabled is True

    def test_create_submission_progress_enabled(self):
        """Test creating submission progress tracker when enabled."""
        with patch("mistral_ocr.progress.Console"):
            manager = ProgressManager(enabled=True)
            tracker = manager.create_submission_progress()
            assert isinstance(tracker, SubmissionProgressTracker)
            assert tracker.manager is manager

    def test_create_submission_progress_disabled(self):
        """Test creating submission progress tracker when disabled."""
        with patch("mistral_ocr.progress.Console"):
            manager = ProgressManager(enabled=False)
            tracker = manager.create_submission_progress()
            # When disabled, still returns SubmissionProgressTracker but manager has enabled=False
            assert isinstance(tracker, SubmissionProgressTracker)
            assert tracker.manager.enabled is False

    def test_create_download_progress_enabled(self):
        """Test creating download progress tracker when enabled."""
        with patch("mistral_ocr.progress.Console"):
            manager = ProgressManager(enabled=True)
            tracker = manager.create_download_progress()
            assert isinstance(tracker, DownloadProgressTracker)
            assert tracker.enabled is True

    def test_create_download_progress_disabled(self):
        """Test creating download progress tracker when disabled."""
        with patch("mistral_ocr.progress.Console"):
            manager = ProgressManager(enabled=False)
            tracker = manager.create_download_progress()
            assert isinstance(tracker, DummyProgress)

    def test_create_job_monitor_enabled(self):
        """Test creating job monitor when enabled."""
        with patch("mistral_ocr.progress.Console"):
            manager = ProgressManager(enabled=True)
            monitor = manager.create_job_monitor()
            assert isinstance(monitor, LiveJobMonitor)
            assert monitor.enabled is True

    def test_create_job_monitor_disabled(self):
        """Test creating job monitor when disabled."""
        with patch("mistral_ocr.progress.Console"):
            manager = ProgressManager(enabled=False)
            monitor = manager.create_job_monitor()
            assert isinstance(monitor, DummyProgress)


class TestDummyProgress:
    """Test the DummyProgress fallback class."""

    def test_dummy_progress_initialization(self):
        """Test DummyProgress initialization."""
        dummy = DummyProgress()
        assert dummy is not None

    def test_dummy_progress_context_manager(self):
        """Test DummyProgress as context manager."""
        dummy = DummyProgress()
        with dummy.track_submission(100, 5) as context:
            assert context is not None
            # Should not raise any exceptions
            context.complete_collection(100)
            context.update_encoding(50)
            context.start_upload("file.txt", 1024)
            context.complete_upload("file.txt")
            context.update_job_creation(3)
            context.complete_job_creation()

    def test_dummy_progress_all_methods(self):
        """Test that DummyProgress handles all method calls gracefully."""
        dummy = DummyProgress()
        
        # Should not raise exceptions for any method calls
        dummy.start_download("file.txt", 1024)
        dummy.update_download("file.txt", 512)
        dummy.complete_download("file.txt")
        dummy.start_monitoring(["job1", "job2"])
        dummy.update_job_status("job1", "running")
        dummy.complete_monitoring()


class TestSubmissionProgressTracker:
    """Test the SubmissionProgressTracker class."""

    @pytest.fixture
    def mock_console(self):
        """Create a mock console for testing."""
        return MagicMock()

    @pytest.fixture
    def mock_progress(self):
        """Create a mock Progress instance."""
        progress = MagicMock()
        # Mock the context manager behavior
        progress.__enter__ = Mock(return_value=progress)
        progress.__exit__ = Mock(return_value=None)
        return progress

    @pytest.fixture
    def submission_tracker(self, mock_console, mock_progress):
        """Create a SubmissionProgressTracker with mocks."""
        with patch("mistral_ocr.progress.Progress", return_value=mock_progress):
            tracker = SubmissionProgressTracker(mock_console, enabled=True)
            tracker.progress = mock_progress
            return tracker

    def test_submission_tracker_initialization(self, mock_console):
        """Test SubmissionProgressTracker initialization."""
        with patch("mistral_ocr.progress.Progress") as mock_progress_class:
            tracker = SubmissionProgressTracker(mock_console, enabled=True)
            assert tracker.console is mock_console
            assert tracker.enabled is True
            mock_progress_class.assert_called_once()

    def test_submission_tracker_disabled(self, mock_console):
        """Test SubmissionProgressTracker when disabled."""
        tracker = SubmissionProgressTracker(mock_console, enabled=False)
        assert tracker.enabled is False
        # Should behave like DummyProgress
        with tracker.track_submission(10, 2) as context:
            context.complete_collection(10)  # Should not raise

    def test_track_submission_context_manager(self, submission_tracker, mock_progress):
        """Test track_submission context manager setup."""
        file_count = 150
        batch_count = 3
        
        with submission_tracker.track_submission(file_count, batch_count) as context:
            # Verify progress setup
            assert mock_progress.__enter__.called
            
            # Verify task creation
            assert mock_progress.add_task.call_count >= 4  # collection, encoding, upload, job_creation
            
            # Context should provide methods
            assert hasattr(context, 'complete_collection')
            assert hasattr(context, 'update_encoding')
            assert hasattr(context, 'start_upload')
            assert hasattr(context, 'complete_upload')
            assert hasattr(context, 'update_job_creation')
            assert hasattr(context, 'complete_job_creation')

    def test_submission_progress_phases(self, submission_tracker, mock_progress):
        """Test all phases of submission progress tracking."""
        with submission_tracker.track_submission(100, 2) as context:
            # Phase 1: Collection
            context.complete_collection(100)
            mock_progress.update.assert_called()
            
            # Phase 2: Encoding
            context.update_encoding(50)
            mock_progress.update.assert_called()
            
            # Phase 3: Upload
            context.start_upload("batch1.jsonl", 1024*1024)
            mock_progress.update.assert_called()
            
            context.complete_upload("batch1.jsonl")
            mock_progress.update.assert_called()
            
            # Phase 4: Job Creation
            context.update_job_creation(1)
            mock_progress.update.assert_called()
            
            context.complete_job_creation()
            mock_progress.update.assert_called()

    def test_submission_multiple_uploads(self, submission_tracker, mock_progress):
        """Test handling multiple batch uploads."""
        with submission_tracker.track_submission(200, 3) as context:
            # Multiple uploads for different batches
            for i in range(3):
                batch_name = f"batch{i+1}.jsonl"
                context.start_upload(batch_name, 1024*1024)
                context.complete_upload(batch_name)
                context.update_job_creation(i+1)
            
            context.complete_job_creation()
            
            # Should have multiple update calls
            assert mock_progress.update.call_count >= 6  # 3 starts + 3 completions


class TestDownloadProgressTracker:
    """Test the DownloadProgressTracker class."""

    @pytest.fixture
    def mock_console(self):
        """Create a mock console for testing."""
        return MagicMock()

    @pytest.fixture
    def mock_progress(self):
        """Create a mock Progress instance."""
        progress = MagicMock()
        progress.__enter__ = Mock(return_value=progress)
        progress.__exit__ = Mock(return_value=None)
        return progress

    @pytest.fixture
    def download_tracker(self, mock_console, mock_progress):
        """Create a DownloadProgressTracker with mocks."""
        with patch("mistral_ocr.progress.Progress", return_value=mock_progress):
            tracker = DownloadProgressTracker(mock_console, enabled=True)
            tracker.progress = mock_progress
            return tracker

    def test_download_tracker_initialization(self, mock_console):
        """Test DownloadProgressTracker initialization."""
        with patch("mistral_ocr.progress.Progress") as mock_progress_class:
            tracker = DownloadProgressTracker(mock_console, enabled=True)
            assert tracker.console is mock_console
            assert tracker.enabled is True
            mock_progress_class.assert_called_once()

    def test_download_tracker_disabled(self, mock_console):
        """Test DownloadProgressTracker when disabled."""
        tracker = DownloadProgressTracker(mock_console, enabled=False)
        assert tracker.enabled is False
        # Should behave like DummyProgress
        tracker.start_download("file.txt", 1024)  # Should not raise

    def test_start_download(self, download_tracker, mock_progress):
        """Test starting a download with progress tracking."""
        filename = "result_file.txt"
        file_size = 1024 * 1024  # 1MB
        
        download_tracker.start_download(filename, file_size)
        
        # Should add a task for this download
        mock_progress.add_task.assert_called()
        call_args = mock_progress.add_task.call_args
        assert filename in call_args[0][0]  # Description should contain filename
        assert call_args[1]['total'] == file_size

    def test_update_download(self, download_tracker, mock_progress):
        """Test updating download progress."""
        filename = "result_file.txt"
        file_size = 1024 * 1024
        
        # Setup download
        mock_progress.add_task.return_value = "task_id"
        download_tracker.start_download(filename, file_size)
        
        # Update progress
        downloaded = 512 * 1024  # 512KB
        download_tracker.update_download(filename, downloaded)
        
        # Should update the task
        mock_progress.update.assert_called()

    def test_complete_download(self, download_tracker, mock_progress):
        """Test completing a download."""
        filename = "result_file.txt"
        file_size = 1024 * 1024
        
        # Setup download
        mock_progress.add_task.return_value = "task_id"
        download_tracker.start_download(filename, file_size)
        
        # Complete download
        download_tracker.complete_download(filename)
        
        # Should update task to completion
        mock_progress.update.assert_called()

    def test_multiple_concurrent_downloads(self, download_tracker, mock_progress):
        """Test handling multiple concurrent downloads."""
        files = [
            ("file1.txt", 1024),
            ("file2.pdf", 2048),
            ("file3.json", 512)
        ]
        
        # Start all downloads
        for filename, size in files:
            download_tracker.start_download(filename, size)
        
        # Update progress for each
        for filename, size in files:
            download_tracker.update_download(filename, size // 2)
        
        # Complete all downloads
        for filename, size in files:
            download_tracker.complete_download(filename)
        
        # Should have created and updated tasks for each file
        assert mock_progress.add_task.call_count == 3
        assert mock_progress.update.call_count >= 6  # 3 updates + 3 completions

    def test_unknown_file_operations(self, download_tracker, mock_progress):
        """Test operations on unknown files (should handle gracefully)."""
        # Update/complete files that weren't started
        download_tracker.update_download("unknown_file.txt", 1024)
        download_tracker.complete_download("unknown_file.txt")
        
        # Should not crash or add tasks
        mock_progress.add_task.assert_not_called()


class TestLiveJobMonitor:
    """Test the LiveJobMonitor class."""

    @pytest.fixture
    def mock_console(self):
        """Create a mock console for testing."""
        return MagicMock()

    @pytest.fixture
    def mock_live(self):
        """Create a mock Live instance."""
        live = MagicMock()
        live.__enter__ = Mock(return_value=live)
        live.__exit__ = Mock(return_value=None)
        return live

    @pytest.fixture
    def job_monitor(self, mock_console, mock_live):
        """Create a LiveJobMonitor with mocks."""
        with patch("mistral_ocr.progress.Live", return_value=mock_live):
            monitor = LiveJobMonitor(mock_console, enabled=True)
            monitor.live = mock_live
            return monitor

    def test_job_monitor_initialization(self, mock_console):
        """Test LiveJobMonitor initialization."""
        with patch("mistral_ocr.progress.Live") as mock_live_class:
            monitor = LiveJobMonitor(mock_console, enabled=True)
            assert monitor.console is mock_console
            assert monitor.enabled is True
            mock_live_class.assert_called_once()

    def test_job_monitor_disabled(self, mock_console):
        """Test LiveJobMonitor when disabled."""
        monitor = LiveJobMonitor(mock_console, enabled=False)
        assert monitor.enabled is False
        # Should behave like DummyProgress
        monitor.start_monitoring(["job1", "job2"])  # Should not raise

    def test_start_monitoring(self, job_monitor, mock_live):
        """Test starting job monitoring."""
        job_ids = ["job_001", "job_002", "job_003"]
        
        job_monitor.start_monitoring(job_ids)
        
        # Should initialize job status tracking
        assert len(job_monitor.job_statuses) == 3
        for job_id in job_ids:
            assert job_id in job_monitor.job_statuses
            assert job_monitor.job_statuses[job_id] == "pending"

    def test_update_job_status(self, job_monitor, mock_live):
        """Test updating individual job status."""
        job_ids = ["job_001", "job_002"]
        job_monitor.start_monitoring(job_ids)
        
        # Update status
        job_monitor.update_job_status("job_001", "running")
        assert job_monitor.job_statuses["job_001"] == "running"
        
        # Update to completion
        job_monitor.update_job_status("job_001", "completed")
        assert job_monitor.job_statuses["job_001"] == "completed"
        
        # Live display should be updated
        mock_live.update.assert_called()

    def test_update_unknown_job(self, job_monitor, mock_live):
        """Test updating status for unknown job."""
        job_monitor.start_monitoring(["job_001"])
        
        # Should handle unknown job gracefully
        job_monitor.update_job_status("unknown_job", "running")
        
        # Should not crash, unknown job should be ignored
        assert "unknown_job" not in job_monitor.job_statuses

    def test_complete_monitoring(self, job_monitor, mock_live):
        """Test completing job monitoring."""
        job_ids = ["job_001", "job_002"]
        job_monitor.start_monitoring(job_ids)
        
        # Update some statuses
        job_monitor.update_job_status("job_001", "completed")
        job_monitor.update_job_status("job_002", "running")
        
        # Complete monitoring
        job_monitor.complete_monitoring()
        
        # Should still maintain job statuses for final state
        assert job_monitor.job_statuses["job_001"] == "completed"
        assert job_monitor.job_statuses["job_002"] == "running"

    def test_job_monitor_context_manager(self, job_monitor, mock_live):
        """Test job monitor as context manager."""
        with job_monitor:
            # Should enter live context
            mock_live.__enter__.assert_called_once()
            
            # Operations should work
            job_monitor.start_monitoring(["job_001"])
            job_monitor.update_job_status("job_001", "running")
        
        # Should exit live context
        mock_live.__exit__.assert_called_once()

    def test_status_display_formatting(self, job_monitor, mock_live):
        """Test that status display is properly formatted."""
        job_ids = ["job_001", "job_002", "job_003"]
        job_monitor.start_monitoring(job_ids)
        
        # Update various statuses
        job_monitor.update_job_status("job_001", "completed")
        job_monitor.update_job_status("job_002", "running")
        job_monitor.update_job_status("job_003", "failed")
        
        # The display should be updated with formatted status
        mock_live.update.assert_called()
        
        # Verify the display includes all job statuses
        update_calls = mock_live.update.call_args_list
        assert len(update_calls) >= 3  # At least one call per status update


class TestProgressIntegration:
    """Integration tests for progress monitoring components."""

    def test_progress_manager_full_workflow(self):
        """Test complete workflow with ProgressManager."""
        with patch("mistral_ocr.progress.Console") as mock_console:
            with patch("mistral_ocr.progress.Progress") as mock_progress:
                with patch("mistral_ocr.progress.Live") as mock_live:
                    # Create manager
                    manager = ProgressManager(enabled=True)
                    
                    # Create all tracker types
                    submission_tracker = manager.create_submission_progress()
                    download_tracker = manager.create_download_progress()
                    job_monitor = manager.create_job_monitor()
                    
                    # Verify correct types
                    assert isinstance(submission_tracker, SubmissionProgressTracker)
                    assert isinstance(download_tracker, DownloadProgressTracker)
                    assert isinstance(job_monitor, LiveJobMonitor)

    def test_disabled_manager_creates_dummy_progress(self):
        """Test that disabled manager creates dummy progress instances."""
        with patch("mistral_ocr.progress.Console"):
            manager = ProgressManager(enabled=False)
            
            # All trackers should be DummyProgress
            submission_tracker = manager.create_submission_progress()
            download_tracker = manager.create_download_progress()
            job_monitor = manager.create_job_monitor()
            
            assert isinstance(submission_tracker, DummyProgress)
            assert isinstance(download_tracker, DummyProgress)
            assert isinstance(job_monitor, DummyProgress)

    def test_progress_tracking_performance(self):
        """Test that progress tracking doesn't significantly impact performance."""
        start_time = time.time()
        
        # Create multiple progress trackers and simulate work
        with patch("mistral_ocr.progress.Console"):
            manager = ProgressManager(enabled=True)
            
            # Create trackers
            for _ in range(10):
                tracker = manager.create_submission_progress()
                with tracker.track_submission(100, 5) as context:
                    context.complete_collection(100)
                    context.update_encoding(50)
                    context.complete_job_creation()
        
        duration = time.time() - start_time
        
        # Should complete quickly (< 1 second even with overhead)
        assert duration < 1.0

    def test_concurrent_progress_tracking(self):
        """Test that multiple progress trackers can work concurrently."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def track_progress(tracker_id):
            with patch("mistral_ocr.progress.Console"):
                manager = ProgressManager(enabled=True)
                tracker = manager.create_submission_progress()
                
                try:
                    with tracker.track_submission(50, 2) as context:
                        context.complete_collection(50)
                        context.update_encoding(25)
                        context.complete_job_creation()
                    results.put((tracker_id, "success"))
                except Exception as e:
                    results.put((tracker_id, f"error: {e}"))
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=track_progress, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify all succeeded
        thread_results = []
        while not results.empty():
            thread_results.append(results.get())
        
        assert len(thread_results) == 3
        for tracker_id, result in thread_results:
            assert result == "success"

    def test_progress_with_rich_components(self):
        """Test integration with actual Rich components (mocked)."""
        from rich.console import Console
        from rich.progress import Progress
        from rich.live import Live
        
        # Test with real Rich classes but minimal functionality
        with patch.object(Console, 'print') as mock_print:
            with patch.object(Progress, '__enter__', return_value=MagicMock()):
                with patch.object(Progress, '__exit__', return_value=None):
                    with patch.object(Progress, 'add_task', return_value="task_id"):
                        with patch.object(Progress, 'update'):
                            # Create real ProgressManager with Rich components
                            manager = ProgressManager(enabled=True)
                            tracker = manager.create_submission_progress()
                            
                            # Should work with actual Rich integration
                            with tracker.track_submission(10, 1) as context:
                                context.complete_collection(10)
                                context.complete_job_creation()