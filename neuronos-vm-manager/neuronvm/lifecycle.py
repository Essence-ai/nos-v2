"""
Manages the Windows VM lifecycle through libvirt.
Handles start, stop, suspend, and dynamic resource allocation.
"""

import json
import os
import time
import threading
import logging
from pathlib import Path
from typing import Optional, Callable

try:
    import libvirt
except ImportError:
    libvirt = None  # Allow running on systems without libvirt

logger = logging.getLogger(__name__)


class VMLifecycleManager:
    """
    Manages the NeuronOS Windows VM lifecycle.

    Handles:
    - Starting/stopping the VM
    - Resource allocation based on system resources
    - Grace period shutdown when no apps are running
    - Application registration for lifecycle management
    """

    DOMAIN_NAME = "win11-neuron"
    GRACE_PERIOD_SECONDS = 300  # Keep VM alive 5 min after last app closes
    PROFILE_PATH = Path("/etc/neuronos/hardware-profile.json")

    def __init__(self):
        self._conn: Optional["libvirt.virConnect"] = None
        self._domain: Optional["libvirt.virDomain"] = None
        self._active_apps: set[str] = set()
        self._shutdown_timer: Optional[threading.Timer] = None
        self._hw_profile = self._load_hw_profile()
        self._state_callbacks: list[Callable[[str], None]] = []

    def _load_hw_profile(self) -> dict:
        """Load hardware profile from disk."""
        if self.PROFILE_PATH.exists():
            try:
                return json.loads(self.PROFILE_PATH.read_text())
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load hardware profile: {e}")
        return {}

    def _connect(self):
        """Establish connection to libvirt."""
        if libvirt is None:
            raise RuntimeError("libvirt is not available")

        if self._conn is None or not self._conn.isAlive():
            self._conn = libvirt.open("qemu:///system")

        try:
            self._domain = self._conn.lookupByName(self.DOMAIN_NAME)
        except libvirt.libvirtError:
            self._domain = None

    def add_state_callback(self, callback: Callable[[str], None]):
        """Add a callback that's called when VM state changes."""
        self._state_callbacks.append(callback)

    def _notify_state_change(self, state: str):
        """Notify all callbacks of a state change."""
        for callback in self._state_callbacks:
            try:
                callback(state)
            except Exception as e:
                logger.error(f"State callback error: {e}")

    @property
    def capability(self) -> str:
        """Get the system's passthrough capability."""
        return self._hw_profile.get("capability", "no_passthrough")

    @property
    def is_single_gpu(self) -> bool:
        """Check if system requires single-GPU switching."""
        return self.capability == "single_gpu"

    def is_running(self) -> bool:
        """Check if the VM is currently running."""
        self._connect()
        if self._domain is None:
            return False
        try:
            state, _ = self._domain.state()
            return state == libvirt.VIR_DOMAIN_RUNNING
        except libvirt.libvirtError:
            return False

    def is_paused(self) -> bool:
        """Check if the VM is paused."""
        self._connect()
        if self._domain is None:
            return False
        try:
            state, _ = self._domain.state()
            return state == libvirt.VIR_DOMAIN_PAUSED
        except libvirt.libvirtError:
            return False

    def start_vm(self) -> bool:
        """
        Start the VM.

        Returns True if VM is now running.
        """
        if self.is_running():
            return True

        self._connect()
        if self._domain is None:
            raise RuntimeError(
                f"VM domain '{self.DOMAIN_NAME}' not found. "
                f"Run the VM setup wizard first."
            )

        # Cancel any pending shutdown
        if self._shutdown_timer:
            self._shutdown_timer.cancel()
            self._shutdown_timer = None

        self._notify_state_change("starting")

        try:
            self._domain.create()  # libvirt "create" = start

            # Wait for VM to be fully booted
            for _ in range(60):  # 60 second timeout
                if self.is_running():
                    self._notify_state_change("running")
                    return True
                time.sleep(1)

            self._notify_state_change("failed")
            return False

        except libvirt.libvirtError as e:
            self._notify_state_change("failed")
            raise RuntimeError(f"Failed to start VM: {e}")

    def stop_vm(self, force: bool = False):
        """
        Gracefully shut down the VM (or force-kill if needed).
        """
        if not self.is_running():
            return

        self._notify_state_change("stopping")

        try:
            if force:
                self._domain.destroy()  # Immediate power off
            else:
                self._domain.shutdown()  # Graceful ACPI shutdown
                # Wait up to 30 seconds for shutdown
                for _ in range(30):
                    if not self.is_running():
                        break
                    time.sleep(1)
                else:
                    # Force kill if graceful failed
                    self._domain.destroy()

            self._notify_state_change("stopped")

        except libvirt.libvirtError as e:
            self._notify_state_change("failed")
            raise RuntimeError(f"Failed to stop VM: {e}")

    def pause_vm(self):
        """Pause (suspend) the VM."""
        if not self.is_running():
            return

        try:
            self._domain.suspend()
            self._notify_state_change("paused")
        except libvirt.libvirtError as e:
            raise RuntimeError(f"Failed to pause VM: {e}")

    def resume_vm(self):
        """Resume a paused VM."""
        if not self.is_paused():
            return

        try:
            self._domain.resume()
            self._notify_state_change("running")
        except libvirt.libvirtError as e:
            raise RuntimeError(f"Failed to resume VM: {e}")

    def register_app(self, app_name: str):
        """
        Called when a VM app is launched.
        Starts VM if needed.
        """
        self._active_apps.add(app_name)
        logger.info(f"Registered app: {app_name} (total: {len(self._active_apps)})")

        if self._shutdown_timer:
            self._shutdown_timer.cancel()
            self._shutdown_timer = None

        if not self.is_running():
            self.start_vm()

    def unregister_app(self, app_name: str):
        """
        Called when a VM app closes.
        Schedules shutdown if no apps left.
        """
        self._active_apps.discard(app_name)
        logger.info(f"Unregistered app: {app_name} (remaining: {len(self._active_apps)})")

        if not self._active_apps:
            logger.info(f"No active apps, scheduling shutdown in {self.GRACE_PERIOD_SECONDS}s")
            self._shutdown_timer = threading.Timer(
                self.GRACE_PERIOD_SECONDS,
                self._grace_period_expired
            )
            self._shutdown_timer.start()

    def _grace_period_expired(self):
        """No apps have been launched during the grace period. Shut down."""
        if not self._active_apps:
            logger.info("Grace period expired, shutting down VM")
            try:
                self.stop_vm()
            except Exception as e:
                logger.error(f"Failed to shut down VM: {e}")

    def get_active_apps(self) -> set[str]:
        """Get the set of currently active VM applications."""
        return self._active_apps.copy()

    def get_resource_allocation(self) -> dict:
        """
        Calculate optimal VM resource allocation based on system resources.
        """
        total_ram_mb = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') // (1024 * 1024)
        total_cores = os.cpu_count() or 4

        # Reserve minimum resources for the Linux host
        host_ram_mb = max(4096, total_ram_mb // 4)  # At least 4GB or 25%
        host_cores = max(2, total_cores // 4)        # At least 2 cores or 25%

        vm_ram_mb = total_ram_mb - host_ram_mb
        vm_cores = total_cores - host_cores

        # Cap VM resources at reasonable maximums
        vm_ram_mb = min(vm_ram_mb, 65536)  # 64GB max
        vm_cores = min(vm_cores, 16)        # 16 cores max

        return {
            "ram_mb": vm_ram_mb,
            "cores": vm_cores,
            "host_ram_mb": host_ram_mb,
            "host_cores": host_cores,
            "total_ram_mb": total_ram_mb,
            "total_cores": total_cores,
        }

    def get_vm_info(self) -> Optional[dict]:
        """Get information about the VM."""
        self._connect()
        if self._domain is None:
            return None

        try:
            info = self._domain.info()
            return {
                "state": info[0],
                "max_memory_kb": info[1],
                "memory_kb": info[2],
                "vcpus": info[3],
                "cpu_time_ns": info[4],
            }
        except libvirt.libvirtError:
            return None
