"""
NeuronOS Post-Install Module

Copies NeuronOS components (binaries, Python packages, configs, services)
from the live ISO to the installed target system.
"""

import os
import subprocess
import libcalamares


def run():
    """Calamares job entry point."""
    root_mount = libcalamares.globalstorage.value("rootMountPoint")

    libcalamares.utils.debug("NeuronOS Post-Install: Copying components to target...")

    install_script = "/usr/lib/neuronos/install-to-target.sh"

    if not os.path.exists(install_script):
        libcalamares.utils.warning(
            f"NeuronOS Post-Install: Install script not found at {install_script}"
        )
        return None

    try:
        result = subprocess.run(
            [install_script, root_mount],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        libcalamares.utils.debug(f"NeuronOS Post-Install: {result.stdout}")
    except subprocess.CalledProcessError as e:
        libcalamares.utils.warning(
            f"NeuronOS Post-Install: Script failed: {e.stderr}"
        )
    except subprocess.TimeoutExpired:
        libcalamares.utils.warning(
            "NeuronOS Post-Install: Script timed out after 5 minutes"
        )

    libcalamares.utils.debug("NeuronOS Post-Install: Complete")
    return None
