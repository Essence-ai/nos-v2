"""
GPU detection and classification.
Parses lspci output to identify all GPUs, their types, and PCI topology.
"""

import os
import re
import subprocess
from typing import Optional

from neuron_hw.models import (
    GPUType,
    GPUVendor,
    PCIDevice,
    GPU,
    PassthroughCapability,
    HardwareProfile,
)

# Re-export models for backward compatibility
__all__ = [
    "GPUType",
    "GPUVendor",
    "PCIDevice",
    "GPU",
    "PassthroughCapability",
    "HardwareProfile",
    "detect_gpus",
    "check_iommu",
    "get_iommu_groups",
    "build_hardware_profile",
]


def detect_gpus() -> list[GPU]:
    """Parse lspci to find all GPUs in the system."""
    # -nn gives numeric IDs, -D includes domain, -k shows kernel driver
    result = subprocess.run(
        ["lspci", "-nnk", "-D"],
        capture_output=True, text=True, check=True
    )

    gpus = []
    pci_devices = _parse_lspci(result.stdout)

    # Find all VGA controllers (class 0300) and 3D controllers (class 0302)
    vga_devices = [d for d in pci_devices if d.class_code in ("0300", "0302")]

    for vga in vga_devices:
        # Find the associated audio device (same bus:slot, function 1)
        audio = next(
            (d for d in pci_devices
             if d.bus == vga.bus and d.slot == vga.slot
             and d.function == "1" and d.class_code == "0403"),
            None
        )

        gpu = GPU(primary_device=vga, audio_device=audio)
        gpu.vendor = _classify_vendor(vga.vendor_id)
        gpu.gpu_type = _classify_type(vga, gpu.vendor)
        gpu.name = vga.description

        gpus.append(gpu)

    return gpus


def check_iommu() -> bool:
    """Check if IOMMU is enabled and active."""
    try:
        result = subprocess.run(
            ["dmesg"], capture_output=True, text=True, check=True
        )
        # Look for Intel DMAR or AMD IOMMU initialization messages
        return bool(re.search(
            r'(DMAR:.*IOMMU enabled|AMD-Vi:.*IOMMU.*enabled|IOMMU.*enabled)',
            result.stdout,
            re.IGNORECASE
        ))
    except subprocess.CalledProcessError:
        # Try alternative method: check if IOMMU groups exist
        iommu_base = "/sys/kernel/iommu_groups"
        if os.path.exists(iommu_base):
            groups = os.listdir(iommu_base)
            return len(groups) > 0
        return False


def get_iommu_groups() -> dict[int, list[PCIDevice]]:
    """Map IOMMU group numbers to their member devices."""
    groups: dict[int, list[PCIDevice]] = {}
    iommu_base = "/sys/kernel/iommu_groups"

    if not os.path.exists(iommu_base):
        return groups

    # Walk /sys/kernel/iommu_groups/*/devices/*
    for group_dir in sorted(os.listdir(iommu_base)):
        try:
            group_num = int(group_dir)
        except ValueError:
            continue

        devices_dir = os.path.join(iommu_base, group_dir, "devices")
        if not os.path.isdir(devices_dir):
            continue

        groups[group_num] = []
        for dev_link in os.listdir(devices_dir):
            # dev_link is a PCI address like "0000:01:00.0"
            pci_addr = dev_link
            # Get device info from lspci
            result = subprocess.run(
                ["lspci", "-nns", pci_addr],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                device = _parse_single_lspci_line(pci_addr, result.stdout.strip())
                if device:
                    device.iommu_group = group_num
                    groups[group_num].append(device)

    return groups


def detect_cpu_vendor() -> str:
    """Detect CPU vendor from /proc/cpuinfo."""
    try:
        with open("/proc/cpuinfo") as f:
            cpuinfo = f.read()
        if "GenuineIntel" in cpuinfo:
            return "intel"
        elif "AuthenticAMD" in cpuinfo:
            return "amd"
    except FileNotFoundError:
        pass
    return ""


def build_hardware_profile() -> HardwareProfile:
    """
    Main entry point. Detects all hardware and determines the optimal
    passthrough configuration.
    """
    profile = HardwareProfile()

    # Detect CPU vendor
    profile.cpu_vendor = detect_cpu_vendor()

    # Detect GPUs
    profile.gpus = detect_gpus()

    # Check IOMMU
    profile.iommu_enabled = check_iommu()

    if not profile.iommu_enabled:
        profile.capability = PassthroughCapability.NO_PASSTHROUGH
        profile.warnings.append(
            "IOMMU is not enabled. GPU passthrough requires IOMMU support. "
            "Check your BIOS/UEFI settings for 'VT-d' (Intel) or "
            "'AMD-Vi' / 'SVM' (AMD) and enable it."
        )
        return profile

    # Get IOMMU groups
    iommu_groups = get_iommu_groups()

    # Classify GPUs and assign IOMMU groups
    integrated = [g for g in profile.gpus if g.gpu_type == GPUType.INTEGRATED]
    discrete = [g for g in profile.gpus if g.gpu_type == GPUType.DISCRETE]

    if len(discrete) == 0:
        profile.capability = PassthroughCapability.NO_PASSTHROUGH
        profile.warnings.append("No discrete GPU found for passthrough.")
        return profile

    if len(integrated) >= 1 and len(discrete) >= 1:
        # Best case: iGPU for host, dGPU for VM
        profile.capability = PassthroughCapability.DUAL_GPU
        profile.host_gpu = integrated[0]
        profile.passthrough_gpu = discrete[0]
    elif len(discrete) >= 2:
        # Two discrete GPUs: smaller one for host, larger for VM
        # (heuristic: sort by device ID, higher = newer/bigger)
        sorted_discrete = sorted(discrete, key=lambda g: g.primary_device.device_id)
        profile.capability = PassthroughCapability.DUAL_GPU
        profile.host_gpu = sorted_discrete[0]
        profile.passthrough_gpu = sorted_discrete[-1]
    else:
        # Only one GPU total — single-GPU switching required
        profile.capability = PassthroughCapability.SINGLE_GPU
        profile.passthrough_gpu = discrete[0]
        profile.host_gpu = discrete[0]  # Same GPU, will be dynamically switched

    # Validate IOMMU group isolation for the passthrough GPU
    pt_gpu = profile.passthrough_gpu
    if pt_gpu:
        group_num = None
        for gnum, devices in iommu_groups.items():
            for dev in devices:
                if dev.address == pt_gpu.primary_device.address:
                    group_num = gnum
                    break

        if group_num is not None:
            group_devices = iommu_groups[group_num]
            # Filter: only the GPU and its audio function should be in the group
            non_gpu_devices = [
                d for d in group_devices
                if d.address != pt_gpu.primary_device.address
                and (pt_gpu.audio_device is None
                     or d.address != pt_gpu.audio_device.address)
            ]
            if non_gpu_devices:
                device_list = ", ".join(d.description for d in non_gpu_devices)
                profile.warnings.append(
                    f"The GPU's IOMMU group also contains other devices: "
                    f"{device_list}. This may require an ACS override patch "
                    f"for clean isolation."
                )

    return profile


def _classify_vendor(vendor_id: str) -> GPUVendor:
    """Classify GPU vendor from PCI vendor ID."""
    vendor_map = {
        "8086": GPUVendor.INTEL,
        "1002": GPUVendor.AMD,
        "10de": GPUVendor.NVIDIA
    }
    return vendor_map.get(vendor_id, GPUVendor.UNKNOWN)


def _classify_type(device: PCIDevice, vendor: GPUVendor) -> GPUType:
    """Classify GPU type (integrated vs discrete)."""
    # Intel GPUs are almost always integrated (except Arc)
    if vendor == GPUVendor.INTEL:
        # Intel Arc discrete GPUs have class 0300 but specific device IDs
        if device.device_id.startswith("56"):  # Arc A-series
            return GPUType.DISCRETE
        return GPUType.INTEGRATED

    # AMD APU integrated GPUs are on bus 00 or have specific device IDs
    if vendor == GPUVendor.AMD and device.bus in ("00", "05", "06"):
        # Heuristic: integrated AMD GPUs are typically on low bus numbers
        # and have "Radeon Graphics" (no model number) in their name
        if "Radeon Graphics" in device.description and "RX" not in device.description:
            return GPUType.INTEGRATED

    return GPUType.DISCRETE


def _parse_lspci(output: str) -> list[PCIDevice]:
    """Parse full lspci -nnk -D output into PCIDevice objects."""
    devices = []
    current_device = None

    for line in output.split("\n"):
        # Device line: "0000:01:00.0 VGA compatible controller [0300]: NVIDIA ... [10de:2684]"
        match = re.match(
            r'^(\w+):(\w+):(\w+)\.(\w+)\s+.*\[(\w{4})\]:\s+(.*)\[(\w{4}):(\w{4})\]',
            line
        )
        if match:
            current_device = PCIDevice(
                domain=match.group(1),
                bus=match.group(2),
                slot=match.group(3),
                function=match.group(4),
                class_code=match.group(5),
                description=match.group(6).strip(),
                vendor_id=match.group(7),
                device_id=match.group(8),
            )
            devices.append(current_device)
            continue

        # Driver line: "\tKernel driver in use: nvidia"
        driver_match = re.match(r'\s+Kernel driver in use:\s+(\S+)', line)
        if driver_match and current_device:
            current_device.driver = driver_match.group(1)

    return devices


def _parse_single_lspci_line(address: str, line: str) -> Optional[PCIDevice]:
    """Parse a single lspci -nns output line."""
    match = re.match(
        r'^[\w:.]+\s+.*\[(\w{4})\]:\s+(.*)\[(\w{4}):(\w{4})\]',
        line
    )
    if not match:
        return None
    parts = address.split(":")
    domain = parts[0]
    bus = parts[1]
    slot_func = parts[2].split(".")
    return PCIDevice(
        domain=domain, bus=bus, slot=slot_func[0], function=slot_func[1],
        class_code=match.group(1), description=match.group(2).strip(),
        vendor_id=match.group(3), device_id=match.group(4),
    )
