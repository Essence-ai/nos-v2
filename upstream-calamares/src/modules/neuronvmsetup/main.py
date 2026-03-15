"""
NeuronOS VM Setup Module

Asks the user if they need Windows application support and
queues the VM template download for first boot.
"""

import os
import libcalamares


def run():
    """Calamares job entry point."""
    root_mount = libcalamares.globalstorage.value("rootMountPoint")
    capability = libcalamares.globalstorage.value("neuron_hw_capability")
    needs_vm = libcalamares.globalstorage.value("neuron_needs_vm", False)

    libcalamares.utils.debug(f"NeuronOS VM Setup: capability={capability}, needs_vm={needs_vm}")

    if capability == "no_passthrough":
        libcalamares.utils.debug("NeuronOS VM Setup: No passthrough capability, skipping VM setup")
        return None

    if not needs_vm:
        libcalamares.utils.debug("NeuronOS VM Setup: User doesn't need Windows apps, skipping")
        return None

    # Create the first-boot VM download flag
    neuron_dir = os.path.join(root_mount, "etc/neuronos")
    os.makedirs(neuron_dir, exist_ok=True)

    flag_file = os.path.join(neuron_dir, "download-vm-template")
    with open(flag_file, "w") as f:
        f.write("1")

    libcalamares.utils.debug("NeuronOS VM Setup: VM template download queued for first boot")

    # Enable the first-boot setup service
    try:
        import subprocess
        subprocess.run(
            ["arch-chroot", root_mount, "systemctl", "enable", "neuronos-firstboot.service"],
            check=True,
            capture_output=True
        )
    except Exception as e:
        libcalamares.utils.warning(f"NeuronOS VM Setup: Could not enable first-boot service: {e}")

    return None


# For viewmodule, we also need QML/UI component
# This would be loaded by Calamares to show the "Do you need Windows apps?" dialog
