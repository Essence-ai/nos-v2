"""
Generate all system configuration files needed for VFIO passthrough.
"""

import json
import os
import re
from typing import Optional

from neuron_hw.models import HardwareProfile, PassthroughCapability


def generate_grub_params(profile: HardwareProfile) -> str:
    """Generate the GRUB_CMDLINE_LINUX_DEFAULT additions."""
    params = []

    if profile.cpu_vendor == "intel":
        params.append("intel_iommu=on")
    elif profile.cpu_vendor == "amd":
        params.append("amd_iommu=on")

    params.append("iommu=pt")  # Passthrough mode for better performance

    if profile.capability == PassthroughCapability.DUAL_GPU:
        # In dual-GPU mode, bind the passthrough GPU to vfio-pci at boot
        gpu = profile.passthrough_gpu
        if gpu:
            ids = gpu.primary_device.vfio_id
            if gpu.audio_device:
                ids += f",{gpu.audio_device.vfio_id}"
            params.append(f"vfio-pci.ids={ids}")

    # Single-GPU mode does NOT bind at boot — binding happens dynamically
    return " ".join(params)


def generate_modprobe_conf(profile: HardwareProfile) -> str:
    """Generate /etc/modprobe.d/vfio.conf content."""
    lines = []

    if profile.capability == PassthroughCapability.DUAL_GPU:
        gpu = profile.passthrough_gpu
        if gpu:
            ids = gpu.primary_device.vfio_id
            if gpu.audio_device:
                ids += f",{gpu.audio_device.vfio_id}"
            lines.append(f"options vfio-pci ids={ids}")

            # Softdep ensures vfio-pci loads before the GPU driver
            if gpu.vendor.value == "nvidia":
                lines.append("softdep nvidia pre: vfio-pci")
                lines.append("softdep nouveau pre: vfio-pci")
            elif gpu.vendor.value == "amd":
                lines.append("softdep amdgpu pre: vfio-pci")
                lines.append("softdep radeon pre: vfio-pci")
            elif gpu.vendor.value == "intel":
                lines.append("softdep i915 pre: vfio-pci")

    return "\n".join(lines)


def generate_mkinitcpio_conf(profile: HardwareProfile) -> str:
    """Generate /etc/mkinitcpio.conf.d/vfio.conf content."""
    if profile.capability == PassthroughCapability.DUAL_GPU:
        return "MODULES=(vfio_pci vfio vfio_iommu_type1)"
    return ""


def generate_dracut_conf(profile: HardwareProfile) -> str:
    """Generate /etc/dracut.conf.d/vfio.conf content (alternative to mkinitcpio)."""
    if profile.capability == PassthroughCapability.DUAL_GPU:
        return 'add_drivers+=" vfio vfio_iommu_type1 vfio_pci "'
    return ""


def write_configs(profile: HardwareProfile, target_root: str = "/"):
    """
    Write all config files to the target filesystem.
    target_root is "/" for live system or "/mnt" during installation.
    """
    # GRUB
    grub_params = generate_grub_params(profile)
    grub_default = os.path.join(target_root, "etc/default/grub")
    if os.path.exists(grub_default):
        with open(grub_default) as f:
            content = f.read()
        # Append our params to GRUB_CMDLINE_LINUX_DEFAULT
        content = re.sub(
            r'(GRUB_CMDLINE_LINUX_DEFAULT="[^"]*)',
            rf'\1 {grub_params}',
            content
        )
        with open(grub_default, "w") as f:
            f.write(content)

    # modprobe
    modprobe_conf = generate_modprobe_conf(profile)
    if modprobe_conf:
        modprobe_dir = os.path.join(target_root, "etc/modprobe.d")
        os.makedirs(modprobe_dir, exist_ok=True)
        with open(os.path.join(modprobe_dir, "vfio.conf"), "w") as f:
            f.write(modprobe_conf + "\n")

    # mkinitcpio
    initramfs_conf = generate_mkinitcpio_conf(profile)
    if initramfs_conf:
        mkinit_dir = os.path.join(target_root, "etc/mkinitcpio.conf.d")
        os.makedirs(mkinit_dir, exist_ok=True)
        with open(os.path.join(mkinit_dir, "vfio.conf"), "w") as f:
            f.write(initramfs_conf + "\n")

    # dracut (alternative to mkinitcpio)
    dracut_conf = generate_dracut_conf(profile)
    if dracut_conf:
        dracut_dir = os.path.join(target_root, "etc/dracut.conf.d")
        os.makedirs(dracut_dir, exist_ok=True)
        with open(os.path.join(dracut_dir, "vfio.conf"), "w") as f:
            f.write(dracut_conf + "\n")

    # Save the profile for other NeuronOS components to read
    neuron_dir = os.path.join(target_root, "etc/neuronos")
    os.makedirs(neuron_dir, exist_ok=True)
    with open(os.path.join(neuron_dir, "hardware-profile.json"), "w") as f:
        json.dump(profile.to_dict(), f, indent=2)


def read_profile(target_root: str = "/") -> Optional[HardwareProfile]:
    """
    Read a previously saved hardware profile from disk.
    """
    profile_path = os.path.join(target_root, "etc/neuronos/hardware-profile.json")
    if not os.path.exists(profile_path):
        return None

    with open(profile_path) as f:
        data = json.load(f)

    profile = HardwareProfile()
    profile.cpu_vendor = data.get("cpu_vendor", "")
    profile.iommu_enabled = data.get("iommu_enabled", False)
    profile.capability = PassthroughCapability(data.get("capability", "no_passthrough"))
    profile.warnings = data.get("warnings", [])

    # Note: Full GPU objects are not restored, only metadata
    return profile
