"""
Wrapper around the Looking Glass client that provides the seamless
application-window experience.
"""

import subprocess
import threading
import logging
import shutil
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class LookingGlassWrapper:
    """
    Manages the Looking Glass client for seamless VM display.

    Provides:
    - Borderless window display of VM content
    - Automatic window sizing and positioning
    - Input capture and forwarding
    - Lifecycle management
    """

    LG_CLIENT_PATH = "/usr/bin/looking-glass-client"
    SHM_PATH = "/dev/shm/looking-glass"
    DEFAULT_SHM_SIZE = 128  # MB

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._exit_callbacks: list[Callable[[int], None]] = []
        self._current_app_name: str = "Windows Application"

    @classmethod
    def is_available(cls) -> bool:
        """Check if Looking Glass client is installed."""
        return shutil.which(cls.LG_CLIENT_PATH) is not None

    def add_exit_callback(self, callback: Callable[[int], None]):
        """Add a callback that's called when Looking Glass exits."""
        self._exit_callbacks.append(callback)

    def launch(
        self,
        app_name: str = "Windows Application",
        width: int = 1920,
        height: int = 1080,
        borderless: bool = True,
        capture_input: bool = True,
        escape_key: str = "KEY_RIGHTCTRL",
    ):
        """
        Launch Looking Glass client.

        Args:
            app_name: Window title (shows in taskbar)
            width: Window width in pixels
            height: Window height in pixels
            borderless: Use borderless window mode
            capture_input: Auto-capture mouse/keyboard
            escape_key: Key to release input capture
        """
        if self._process and self._process.poll() is None:
            logger.info("Looking Glass already running, bringing to front")
            # Could use wmctrl/xdotool to focus window
            return

        self._current_app_name = app_name

        cmd = [self.LG_CLIENT_PATH]

        if borderless:
            cmd.append("-F")  # Borderless fullscreen

        cmd.extend([
            "-m", str(self.DEFAULT_SHM_SIZE),  # Shared memory size
            "-S",  # Disable screensaver inhibit
            "-p", "0",  # Disable cursor position polling
            f"app:renderer=egl",
            f"win:size={width}x{height}",
            f"win:title={app_name}",
            "win:autoResize=yes",
            "win:keepAspect=yes",
            "spice:enable=no",  # We don't use Spice display
        ])

        if capture_input:
            cmd.extend([
                "input:autoCapture=yes",
                f"input:escapeKey={escape_key}",
            ])
        else:
            cmd.extend([
                "input:autoCapture=no",
                "input:grabKeyboard=no",
            ])

        logger.info(f"Launching Looking Glass: {' '.join(cmd)}")

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"Looking Glass client not found at {self.LG_CLIENT_PATH}. "
                f"Please install Looking Glass."
            )
        except Exception as e:
            raise RuntimeError(f"Failed to launch Looking Glass: {e}")

        # Monitor the process in a background thread
        self._monitor_thread = threading.Thread(
            target=self._monitor,
            daemon=True,
            name="looking-glass-monitor"
        )
        self._monitor_thread.start()

    def _monitor(self):
        """Watch the Looking Glass process and handle exit."""
        if self._process:
            return_code = self._process.wait()
            logger.info(f"Looking Glass exited with code {return_code}")

            # Read any error output
            if self._process.stderr:
                stderr = self._process.stderr.read().decode()
                if stderr:
                    logger.warning(f"Looking Glass stderr: {stderr}")

            # Notify callbacks
            for callback in self._exit_callbacks:
                try:
                    callback(return_code)
                except Exception as e:
                    logger.error(f"Exit callback error: {e}")

    def stop(self):
        """Stop the Looking Glass client."""
        if self._process and self._process.poll() is None:
            logger.info("Stopping Looking Glass")
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Looking Glass didn't terminate, killing")
                self._process.kill()
                self._process.wait()

    @property
    def is_running(self) -> bool:
        """Check if Looking Glass is currently running."""
        return self._process is not None and self._process.poll() is None

    @property
    def current_app_name(self) -> str:
        """Get the current application name being displayed."""
        return self._current_app_name

    def get_window_info(self) -> Optional[dict]:
        """
        Get information about the Looking Glass window.
        Requires wmctrl or xdotool.
        """
        if not self.is_running:
            return None

        try:
            # Try to get window info using wmctrl
            result = subprocess.run(
                ["wmctrl", "-l"],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if self._current_app_name in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            return {
                                "window_id": parts[0],
                                "desktop": parts[1],
                                "title": " ".join(parts[3:]),
                            }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return None

    def focus_window(self):
        """Bring the Looking Glass window to focus."""
        if not self.is_running:
            return

        try:
            # Try wmctrl first
            subprocess.run(
                ["wmctrl", "-a", self._current_app_name],
                timeout=1
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            try:
                # Fall back to xdotool
                subprocess.run(
                    ["xdotool", "search", "--name", self._current_app_name, "windowactivate"],
                    timeout=1
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.warning("Could not focus window (wmctrl/xdotool not available)")
