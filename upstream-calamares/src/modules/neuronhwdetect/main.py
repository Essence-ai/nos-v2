"""
Calamares module that runs hardware detection and writes VFIO configs
to the target installation.
"""

import libcalamares
from neuron_hw.detect import build_hardware_profile
from neuron_hw.vfio_config import write_configs


def run():
    """Calamares job entry point."""
    root_mount = libcalamares.globalstorage.value("rootMountPoint")

    libcalamares.utils.debug("NeuronOS: Starting hardware detection...")

    try:
        profile = build_hardware_profile()
    except Exception as e:
        libcalamares.utils.warning(f"NeuronOS: Hardware detection failed: {e}")
        # Continue installation without VFIO config
        libcalamares.globalstorage.insert("neuron_hw_capability", "no_passthrough")
        libcalamares.globalstorage.insert("neuron_hw_warnings", [str(e)])
        return None

    libcalamares.utils.debug(
        f"NeuronOS: Detected {len(profile.gpus)} GPU(s), "
        f"capability: {profile.capability.value}"
    )

    for warning in profile.warnings:
        libcalamares.utils.warning(f"NeuronOS: {warning}")

    # Write configs to the target filesystem
    try:
        write_configs(profile, target_root=root_mount)
        libcalamares.utils.debug("NeuronOS: VFIO configuration written.")
    except Exception as e:
        libcalamares.utils.warning(f"NeuronOS: Failed to write configs: {e}")

    # Store results in Calamares global storage for other modules to use
    libcalamares.globalstorage.insert(
        "neuron_hw_capability", profile.capability.value
    )
    libcalamares.globalstorage.insert(
        "neuron_hw_warnings", profile.warnings
    )

    # Store GPU info for display in summary
    if profile.passthrough_gpu:
        libcalamares.globalstorage.insert(
            "neuron_passthrough_gpu", profile.passthrough_gpu.name
        )
    if profile.host_gpu:
        libcalamares.globalstorage.insert(
            "neuron_host_gpu", profile.host_gpu.name
        )

    return None  # Success
