"""
Data models for NeuronOS hardware detection.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class GPUType(Enum):
    """Classification of GPU type."""
    INTEGRATED = "integrated"
    DISCRETE = "discrete"
    UNKNOWN = "unknown"


class GPUVendor(Enum):
    """GPU vendor identification."""
    INTEL = "intel"
    AMD = "amd"
    NVIDIA = "nvidia"
    UNKNOWN = "unknown"


class PassthroughCapability(Enum):
    """System's GPU passthrough capability level."""
    DUAL_GPU = "dual_gpu"          # iGPU for host, dGPU for VM (best)
    SINGLE_GPU = "single_gpu"      # Only one GPU, dynamic switching required
    NO_PASSTHROUGH = "no_passthrough"  # IOMMU not available or GPU not isolatable


@dataclass
class PCIDevice:
    """Represents a PCI device in the system."""
    domain: str          # e.g., "0000"
    bus: str             # e.g., "01"
    slot: str            # e.g., "00"
    function: str        # e.g., "0"
    vendor_id: str       # e.g., "10de"
    device_id: str       # e.g., "2684"
    class_code: str      # e.g., "0300" (VGA) or "0302" (3D controller)
    description: str     # Human-readable name
    driver: Optional[str] = None
    iommu_group: Optional[int] = None

    @property
    def address(self) -> str:
        """Full PCI address string."""
        return f"{self.domain}:{self.bus}:{self.slot}.{self.function}"

    @property
    def vfio_id(self) -> str:
        """Vendor:device ID format used for VFIO binding."""
        return f"{self.vendor_id}:{self.device_id}"

    @property
    def short_address(self) -> str:
        """Short PCI address without domain."""
        return f"{self.bus}:{self.slot}.{self.function}"


@dataclass
class GPU:
    """Represents a GPU with its associated devices."""
    primary_device: PCIDevice          # The VGA/3D controller
    audio_device: Optional[PCIDevice] = None  # HDMI audio (same slot, function 1)
    gpu_type: GPUType = GPUType.UNKNOWN
    vendor: GPUVendor = GPUVendor.UNKNOWN
    name: str = ""

    @property
    def all_devices(self) -> list[PCIDevice]:
        """All PCI devices associated with this GPU."""
        devices = [self.primary_device]
        if self.audio_device:
            devices.append(self.audio_device)
        return devices

    @property
    def vfio_ids(self) -> list[str]:
        """All VFIO IDs for this GPU."""
        return [d.vfio_id for d in self.all_devices]


@dataclass
class HardwareProfile:
    """Complete hardware profile for the system."""
    gpus: list[GPU] = field(default_factory=list)
    iommu_enabled: bool = False
    cpu_vendor: str = ""  # "intel" or "amd"
    capability: PassthroughCapability = PassthroughCapability.NO_PASSTHROUGH
    host_gpu: Optional[GPU] = None       # GPU that stays with Linux
    passthrough_gpu: Optional[GPU] = None # GPU that goes to the VM
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize the profile for JSON storage."""
        return {
            "cpu_vendor": self.cpu_vendor,
            "iommu_enabled": self.iommu_enabled,
            "capability": self.capability.value,
            "passthrough_gpu": {
                "name": self.passthrough_gpu.name if self.passthrough_gpu else None,
                "vendor": self.passthrough_gpu.vendor.value if self.passthrough_gpu else None,
                "pci_address": self.passthrough_gpu.primary_device.address if self.passthrough_gpu else None,
                "vfio_ids": ",".join(self.passthrough_gpu.vfio_ids) if self.passthrough_gpu else None,
            } if self.passthrough_gpu else None,
            "host_gpu": {
                "name": self.host_gpu.name if self.host_gpu else None,
                "pci_address": self.host_gpu.primary_device.address if self.host_gpu else None,
            } if self.host_gpu else None,
            "warnings": self.warnings,
        }
