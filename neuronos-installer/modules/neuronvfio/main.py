"""
NeuronOS VFIO Configuration Module

Writes VFIO configuration files based on detected hardware.
Must run after neuronhwdetect module.
"""

import os
import subprocess
import libcalamares


def run():
    """Calamares job entry point."""
    root_mount = libcalamares.globalstorage.value("rootMountPoint")
    capability = libcalamares.globalstorage.value("neuron_hw_capability")

    libcalamares.utils.debug(f"NeuronOS VFIO: Configuring for {capability}")

    if capability == "no_passthrough":
        libcalamares.utils.debug("NeuronOS VFIO: No passthrough capability, skipping")
        return None

    # Rebuild initramfs with VFIO modules
    try:
        libcalamares.utils.debug("NeuronOS VFIO: Rebuilding initramfs...")
        subprocess.run(
            ["arch-chroot", root_mount, "mkinitcpio", "-P"],
            check=True,
            capture_output=True
        )
    except subprocess.CalledProcessError as e:
        libcalamares.utils.warning(f"NeuronOS VFIO: Failed to rebuild initramfs: {e}")

    # Update GRUB configuration
    try:
        libcalamares.utils.debug("NeuronOS VFIO: Updating GRUB...")
        subprocess.run(
            ["arch-chroot", root_mount, "grub-mkconfig", "-o", "/boot/grub/grub.cfg"],
            check=True,
            capture_output=True
        )
    except subprocess.CalledProcessError as e:
        libcalamares.utils.warning(f"NeuronOS VFIO: Failed to update GRUB: {e}")

    libcalamares.utils.debug("NeuronOS VFIO: Configuration complete")
    return None
