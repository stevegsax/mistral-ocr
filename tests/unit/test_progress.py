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
            assert tracker.manager is manager

    def test_create_download_progress_disabled(self):
        """Test creating download progress tracker when disabled."""
        with patch("mistral_ocr.progress.Console"):
            manager = ProgressManager(enabled=False)
            tracker = manager.create_download_progress()
            assert isinstance(tracker, DownloadProgressTracker)
            assert tracker.manager.enabled is False

    def test_create_job_monitor_enabled(self):
        """Test creating job monitor when enabled."""
        with patch("mistral_ocr.progress.Console"):
            manager = ProgressManager(enabled=True)
            monitor = manager.create_job_monitor()
            assert isinstance(monitor, LiveJobMonitor)
            assert monitor.manager is manager

    def test_create_job_monitor_disabled(self):
        """Test creating job monitor when disabled."""
        with patch("mistral_ocr.progress.Console"):
            manager = ProgressManager(enabled=False)
            monitor = manager.create_job_monitor()
            assert isinstance(monitor, LiveJobMonitor)
            assert monitor.manager.enabled is False


class TestDummyProgress:
    """Test the DummyProgress fallback class."""

    def test_dummy_progress_initialization(self):
        """Test DummyProgress initialization."""
        dummy = DummyProgress()
        assert dummy is not None

    def test_dummy_progress_basic_methods(self):
        """Test DummyProgress basic methods."""
        dummy = DummyProgress()
        # Should not raise any exceptions
        task_id = dummy.add_task("test", total=100)
        dummy.update(task_id, completed=50)
        dummy.advance(task_id, 10)
        dummy.remove_task(task_id)

    def test_dummy_progress_task_operations(self):
        """Test that DummyProgress handles task operations gracefully."""
        dummy = DummyProgress()
        
        # Should not raise exceptions for any method calls
        task_id = dummy.add_task("Processing files", total=100)
        dummy.update(task_id, completed=25, description="Processing...")
        dummy.advance(task_id, 10)
        dummy.remove_task(task_id)


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
    def submission_tracker(self):
        """Create a SubmissionProgressTracker with mocks."""
        manager = MagicMock()
        manager.enabled = True
        return SubmissionProgressTracker(manager)

    def test_submission_tracker_initialization(self):
        """Test SubmissionProgressTracker initialization."""
        manager = MagicMock()
        tracker = SubmissionProgressTracker(manager)
        assert tracker.manager is manager

    def test_submission_tracker_disabled(self):
        """Test SubmissionProgressTracker when disabled."""
        manager = MagicMock()
        manager.enabled = False
        tracker = SubmissionProgressTracker(manager)
        assert tracker.manager.enabled is False
        # Should work with manager.create_progress context
        with tracker.track_submission(10, 2) as context:
            context.complete_collection(10)  # Should not raise

    def test_track_submission_context_manager(self, submission_tracker, mock_progress):
        """Test track_submission context manager setup."""
        file_count = 150
        batch_count = 3
        
        # Mock the manager's create_progress method
        submission_tracker.manager.create_progress.return_value.__enter__ = Mock(return_value=mock_progress)
        submission_tracker.manager.create_progress.return_value.__exit__ = Mock(return_value=None)
        
        with submission_tracker.track_submission(file_count, batch_count) as context:
            # Context should provide methods
            assert hasattr(context, 'complete_collection')
            assert hasattr(context, 'update_encoding')
            assert hasattr(context, 'start_upload')
            assert hasattr(context, 'complete_upload')
            assert hasattr(context, 'update_job_creation')
            assert hasattr(context, 'complete_job_creation')

    def test_submission_progress_phases(self, submission_tracker, mock_progress):
        """Test all phases of submission progress tracking."""
        # Mock the manager's create_progress method
        submission_tracker.manager.create_progress.return_value.__enter__ = Mock(return_value=mock_progress)
        submission_tracker.manager.create_progress.return_value.__exit__ = Mock(return_value=None)
        
        with submission_tracker.track_submission(100, 2) as context:
            # Phase 1: Collection
            context.complete_collection(100)
            # Phase 2: Encoding
            context.update_encoding(50)
            # Phase 3: Upload
            context.start_upload("batch1.jsonl", 1024*1024)
            
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
    def download_tracker(self):
        """Create a DownloadProgressTracker with mocks."""
        manager = MagicMock()
        manager.enabled = True
        return DownloadProgressTracker(manager)

    def test_download_tracker_initialization(self):
        """Test DownloadProgressTracker initialization."""
        manager = MagicMock()
        tracker = DownloadProgressTracker(manager)
        assert tracker.manager is manager

    def test_download_tracker_disabled(self):
        """Test DownloadProgressTracker when disabled."""
        manager = MagicMock()
        manager.enabled = False
        tracker = DownloadProgressTracker(manager)
        assert tracker.manager.enabled is False
        # Should work with track_downloads context
        with tracker.track_downloads(3) as context:
            context.start_download("job123", 1024)  # Should not raise

    def test_start_download(self, download_tracker, mock_progress):
        """Test starting a download with progress tracking."""
        job_id = "job_12345"
        file_size = 1024 * 1024  # 1MB
        
        # Mock the manager's create_progress method
        download_tracker.manager.create_progress.return_value.__enter__ = Mock(return_value=mock_progress)
        download_tracker.manager.create_progress.return_value.__exit__ = Mock(return_value=None)
        
        with download_tracker.track_downloads(1) as context:
            context.start_download(job_id, file_size)
            
            # Should add a task for this download
            mock_progress.add_task.assert_called()
            call_args = mock_progress.add_task.call_args
            assert job_id[:8] in call_args[0][0]  # Description should contain job ID
            assert call_args[1]['total'] == file_size

    def test_update_download(self, download_tracker, mock_progress):
        """Test updating download progress."""
        job_id = "job_12345"
        file_size = 1024 * 1024
        
        # Mock the manager's create_progress method
        download_tracker.manager.create_progress.return_value.__enter__ = Mock(return_value=mock_progress)
        download_tracker.manager.create_progress.return_value.__exit__ = Mock(return_value=None)
        
        # Setup download
        mock_progress.add_task.return_value = "task_id"
        
        with download_tracker.track_downloads(1) as context:
            context.start_download(job_id, file_size)
            
            # Update progress
            downloaded = 512 * 1024  # 512KB
            context.update_download(job_id, downloaded)
            
            # Should update the task
            mock_progress.update.assert_called()

    def test_complete_download(self, download_tracker, mock_progress):
        """Test completing a download."""
        job_id = "job_12345"
        file_size = 1024 * 1024
        
        # Mock the manager's create_progress method
        download_tracker.manager.create_progress.return_value.__enter__ = Mock(return_value=mock_progress)
        download_tracker.manager.create_progress.return_value.__exit__ = Mock(return_value=None)
        
        # Setup download
        mock_progress.add_task.return_value = "task_id"
        
        with download_tracker.track_downloads(1) as context:
            context.start_download(job_id, file_size)
            
            # Complete download
            context.complete_download(job_id)
            
            # Should remove task
            mock_progress.remove_task.assert_called()

    def test_multiple_concurrent_downloads(self, download_tracker, mock_progress):
        """Test handling multiple concurrent downloads."""
        jobs = [
            ("job_001", 1024),
            ("job_002", 2048),
            ("job_003", 512)
        ]
        
        # Mock the manager's create_progress method
        download_tracker.manager.create_progress.return_value.__enter__ = Mock(return_value=mock_progress)
        download_tracker.manager.create_progress.return_value.__exit__ = Mock(return_value=None)
        
        with download_tracker.track_downloads(3) as context:
            # Start all downloads
            for job_id, size in jobs:
                context.start_download(job_id, size)
            
            # Update progress for each
            for job_id, size in jobs:
                context.update_download(job_id, size // 2)
            
            # Complete all downloads
            for job_id, size in jobs:
                context.complete_download(job_id)
            
            # Should have created tasks for each file (plus overall task)
            assert mock_progress.add_task.call_count >= 3

    def test_unknown_job_operations(self, download_tracker, mock_progress):
        """Test operations on unknown jobs (should handle gracefully)."""
        # Mock the manager's create_progress method
        download_tracker.manager.create_progress.return_value.__enter__ = Mock(return_value=mock_progress)
        download_tracker.manager.create_progress.return_value.__exit__ = Mock(return_value=None)
        
        with download_tracker.track_downloads(1) as context:
            # Update/complete jobs that weren't started
            context.update_download("unknown_job", 1024)
            context.complete_download("unknown_job")
            
            # Should not crash - operations on unknown jobs are handled gracefully


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
    def job_monitor(self):
        """Create a LiveJobMonitor with mocks."""
        manager = MagicMock()
        manager.enabled = True
        return LiveJobMonitor(manager)

    def test_job_monitor_initialization(self):
        """Test LiveJobMonitor initialization."""
        manager = MagicMock()
        monitor = LiveJobMonitor(manager)
        assert monitor.manager is manager
        assert monitor.console is manager.console

    def test_job_monitor_disabled(self):
        """Test LiveJobMonitor when disabled."""
        manager = MagicMock()
        manager.enabled = False
        monitor = LiveJobMonitor(manager)
        assert monitor.manager.enabled is False
        # Should handle disabled state gracefully
        monitor.monitor_jobs(["job1", "job2"])  # Should not raise

    def test_basic_monitor_setup(self, job_monitor):
        """Test basic job monitor setup."""
        job_ids = ["job_001", "job_002", "job_003"]
        
        # Mock the necessary dependencies for monitor_jobs
        with patch('mistral_ocr.progress.get_settings') as mock_get_settings:
            with patch('mistral_ocr.progress.MistralOCRClient'):
                mock_settings = MagicMock()
                mock_settings.get_api_key_optional.return_value = "test-key"
                mock_get_settings.return_value = mock_settings
                
                # Should not raise when monitor is enabled
                assert job_monitor.manager.enabled

    def test_status_table_creation(self, job_monitor):
        """Test status table creation."""
        job_ids = ["job_001", "job_002"]
        statuses = {"job_001": "running", "job_002": "completed"}
        
        # Should be able to create status table
        table = job_monitor._create_status_table(job_ids, statuses)
        assert table is not None

    def test_status_change_detection(self, job_monitor):
        """Test status change detection."""
        current_statuses = {"job_001": "completed", "job_002": "running"}
        
        # Initialize last statuses
        job_monitor._last_statuses = {"job_001": "running", "job_002": "pending"}
        
        # Should detect changes
        job_monitor._detect_status_changes(current_statuses)
        
        # Last statuses should be updated
        assert job_monitor._last_statuses["job_001"] == "completed"

    def test_all_jobs_complete_check(self, job_monitor):
        """Test checking if all jobs are complete."""
        # All completed
        statuses_complete = {"job_001": "COMPLETED", "job_002": "FAILED"}
        assert job_monitor._all_jobs_complete(statuses_complete)
        
        # Some still running
        statuses_running = {"job_001": "COMPLETED", "job_002": "RUNNING"}
        assert not job_monitor._all_jobs_complete(statuses_running)

    def test_format_status(self, job_monitor):
        """Test status formatting with emojis."""
        assert "✅" in job_monitor._format_status("completed")
        assert "❌" in job_monitor._format_status("failed")
        assert "🔄" in job_monitor._format_status("running")
        assert "⏳" in job_monitor._format_status("pending")


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

    def test_disabled_manager_creates_trackers_with_disabled_managers(self):
        """Test that disabled manager creates trackers with disabled managers."""
        with patch("mistral_ocr.progress.Console"):
            manager = ProgressManager(enabled=False)
            
            # All trackers should still be the correct type but with disabled managers
            submission_tracker = manager.create_submission_progress()
            download_tracker = manager.create_download_progress()
            job_monitor = manager.create_job_monitor()
            
            assert isinstance(submission_tracker, SubmissionProgressTracker)
            assert isinstance(download_tracker, DownloadProgressTracker)
            assert isinstance(job_monitor, LiveJobMonitor)
            
            # But their managers should be disabled
            assert not submission_tracker.manager.enabled
            assert not download_tracker.manager.enabled
            assert not job_monitor.manager.enabled

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