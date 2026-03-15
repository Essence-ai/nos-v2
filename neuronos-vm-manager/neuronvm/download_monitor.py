"""
Monitors the Downloads directory for Windows executables and prompts
for installation.

Uses inotify to watch for new .exe/.msi files.
"""

import logging
import os
import threading
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Try to import inotify, fall back to polling if not available
try:
    from inotify_simple import INotify, flags
    INOTIFY_AVAILABLE = True
except ImportError:
    INOTIFY_AVAILABLE = False
    logger.warning("inotify_simple not available, falling back to polling")


class DownloadMonitor:
    """
    Monitors directories for new Windows executables.

    When a .exe or .msi file appears, notifies callbacks so the
    application can prompt the user for installation.
    """

    WATCH_EXTENSIONS = {".exe", ".msi"}
    POLL_INTERVAL = 2  # seconds (for fallback polling)

    def __init__(
        self,
        watch_dirs: Optional[list[str]] = None,
        on_new_file: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize the download monitor.

        Args:
            watch_dirs: List of directories to watch. Defaults to ~/Downloads.
            on_new_file: Callback called when a new executable is detected.
        """
        if watch_dirs is None:
            downloads = Path.home() / "Downloads"
            watch_dirs = [str(downloads)] if downloads.exists() else []

        self._watch_dirs = watch_dirs
        self._callbacks: list[Callable[[str], None]] = []
        if on_new_file:
            self._callbacks.append(on_new_file)

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._seen_files: set[str] = set()

        # Track existing files so we don't trigger on startup
        self._initialize_seen_files()

    def _initialize_seen_files(self):
        """Record all existing files so we only trigger on new ones."""
        for watch_dir in self._watch_dirs:
            if os.path.isdir(watch_dir):
                for filename in os.listdir(watch_dir):
                    filepath = os.path.join(watch_dir, filename)
                    if self._is_windows_executable(filepath):
                        self._seen_files.add(filepath)

    def _is_windows_executable(self, filepath: str) -> bool:
        """Check if a file is a Windows executable."""
        if not os.path.isfile(filepath):
            return False
        ext = os.path.splitext(filepath)[1].lower()
        return ext in self.WATCH_EXTENSIONS

    def add_callback(self, callback: Callable[[str], None]):
        """Add a callback for when new executables are detected."""
        self._callbacks.append(callback)

    def _notify_callbacks(self, filepath: str):
        """Notify all callbacks of a new file."""
        for callback in self._callbacks:
            try:
                callback(filepath)
            except Exception as e:
                logger.error(f"Callback error for {filepath}: {e}")

    def start(self):
        """Start monitoring in a background thread."""
        if self._running:
            return

        self._running = True

        if INOTIFY_AVAILABLE:
            self._thread = threading.Thread(
                target=self._inotify_loop,
                daemon=True,
                name="download-monitor-inotify"
            )
        else:
            self._thread = threading.Thread(
                target=self._poll_loop,
                daemon=True,
                name="download-monitor-poll"
            )

        self._thread.start()
        logger.info(f"Download monitor started for: {self._watch_dirs}")

    def stop(self):
        """Stop monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Download monitor stopped")

    def _inotify_loop(self):
        """Main loop using inotify for efficient file watching."""
        inotify = INotify()

        watch_flags = flags.CREATE | flags.MOVED_TO | flags.CLOSE_WRITE

        for watch_dir in self._watch_dirs:
            if os.path.isdir(watch_dir):
                try:
                    inotify.add_watch(watch_dir, watch_flags)
                except Exception as e:
                    logger.error(f"Failed to watch {watch_dir}: {e}")

        while self._running:
            try:
                events = inotify.read(timeout=1000)  # 1 second timeout
                for event in events:
                    if event.name:
                        # Find which watch directory this event is from
                        for watch_dir in self._watch_dirs:
                            filepath = os.path.join(watch_dir, event.name)
                            if (
                                os.path.exists(filepath)
                                and self._is_windows_executable(filepath)
                                and filepath not in self._seen_files
                            ):
                                self._seen_files.add(filepath)
                                logger.info(f"New executable detected: {filepath}")
                                self._notify_callbacks(filepath)
            except Exception as e:
                if self._running:
                    logger.error(f"inotify error: {e}")

    def _poll_loop(self):
        """Fallback polling loop for systems without inotify."""
        import time

        while self._running:
            for watch_dir in self._watch_dirs:
                if not os.path.isdir(watch_dir):
                    continue

                try:
                    for filename in os.listdir(watch_dir):
                        filepath = os.path.join(watch_dir, filename)
                        if (
                            self._is_windows_executable(filepath)
                            and filepath not in self._seen_files
                        ):
                            self._seen_files.add(filepath)
                            logger.info(f"New executable detected: {filepath}")
                            self._notify_callbacks(filepath)
                except Exception as e:
                    logger.error(f"Poll error for {watch_dir}: {e}")

            time.sleep(self.POLL_INTERVAL)

    def check_file(self, filepath: str) -> bool:
        """
        Manually check a file and trigger callbacks if it's a new executable.

        Returns True if the file was processed.
        """
        if not self._is_windows_executable(filepath):
            return False

        if filepath in self._seen_files:
            return False

        self._seen_files.add(filepath)
        self._notify_callbacks(filepath)
        return True
