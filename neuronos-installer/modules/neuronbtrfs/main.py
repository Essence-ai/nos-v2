"""
NeuronOS BTRFS Configuration Module

Sets up snapper for automatic system snapshots and
integrates with GRUB for bootable snapshots.
"""

import os
import subprocess
import libcalamares


def run():
    """Calamares job entry point."""
    root_mount = libcalamares.globalstorage.value("rootMountPoint")

    libcalamares.utils.debug("NeuronOS BTRFS: Configuring snapper...")

    # Check if we're using BTRFS
    try:
        result = subprocess.run(
            ["findmnt", "-n", "-o", "FSTYPE", root_mount],
            capture_output=True,
            text=True
        )
        fstype = result.stdout.strip()
        if fstype != "btrfs":
            libcalamares.utils.debug(f"NeuronOS BTRFS: Not using BTRFS ({fstype}), skipping")
            return None
    except Exception as e:
        libcalamares.utils.warning(f"NeuronOS BTRFS: Could not detect filesystem: {e}")
        return None

    # Create snapper config for root
    snapper_config = os.path.join(root_mount, "etc/snapper/configs/root")
    snapper_template = os.path.join(root_mount, "etc/snapper/config-templates/default")

    try:
        os.makedirs(os.path.dirname(snapper_config), exist_ok=True)

        if os.path.exists(snapper_template):
            # Create snapper config
            subprocess.run(
                ["arch-chroot", root_mount, "snapper", "-c", "root", "create-config", "/"],
                check=True,
                capture_output=True
            )
            libcalamares.utils.debug("NeuronOS BTRFS: Created snapper config")

    except subprocess.CalledProcessError as e:
        libcalamares.utils.warning(f"NeuronOS BTRFS: Failed to create snapper config: {e}")
        # Continue anyway

    # Configure snapper settings
    snapper_settings = """
# NeuronOS Snapper Configuration
TIMELINE_CREATE="yes"
TIMELINE_CLEANUP="yes"
TIMELINE_MIN_AGE="1800"
TIMELINE_LIMIT_HOURLY="5"
TIMELINE_LIMIT_DAILY="7"
TIMELINE_LIMIT_WEEKLY="4"
TIMELINE_LIMIT_MONTHLY="3"
TIMELINE_LIMIT_YEARLY="0"
NUMBER_LIMIT="50"
NUMBER_MIN_AGE="1800"
NUMBER_LIMIT_IMPORTANT="10"
"""

    try:
        with open(snapper_config, "a") as f:
            f.write(snapper_settings)
    except Exception as e:
        libcalamares.utils.warning(f"NeuronOS BTRFS: Failed to write snapper settings: {e}")

    # Enable snapper timer
    try:
        subprocess.run(
            ["arch-chroot", root_mount, "systemctl", "enable", "snapper-timeline.timer"],
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["arch-chroot", root_mount, "systemctl", "enable", "snapper-cleanup.timer"],
            check=True,
            capture_output=True
        )
        libcalamares.utils.debug("NeuronOS BTRFS: Enabled snapper timers")
    except subprocess.CalledProcessError as e:
        libcalamares.utils.warning(f"NeuronOS BTRFS: Failed to enable snapper: {e}")

    # Configure grub-btrfs for bootable snapshots
    try:
        subprocess.run(
            ["arch-chroot", root_mount, "systemctl", "enable", "grub-btrfsd"],
            check=True,
            capture_output=True
        )
        libcalamares.utils.debug("NeuronOS BTRFS: Enabled grub-btrfsd")
    except subprocess.CalledProcessError as e:
        libcalamares.utils.warning(f"NeuronOS BTRFS: grub-btrfsd not available: {e}")

    libcalamares.utils.debug("NeuronOS BTRFS: Configuration complete")
    return None
