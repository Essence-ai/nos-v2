"""
NeuronOS Hardware Detection System

This module provides automatic GPU detection, IOMMU group analysis,
and VFIO configuration generation for GPU passthrough virtualization.
"""

from neuron_hw.detect import (
    GPUType,
    GPUVendor,
    PCIDevice,
    GPU,
    PassthroughCapability,
    HardwareProfile,
    detect_gpus,
    check_iommu,
    get_iommu_groups,
    build_hardware_profile,
)

from neuron_hw.vfio_config import (
    generate_grub_params,
    generate_modprobe_conf,
    generate_mkinitcpio_conf,
    write_configs,
)

__version__ = "0.1.0"
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
    "generate_grub_params",
    "generate_modprobe_conf",
    "generate_mkinitcpio_conf",
    "write_configs",
]
