"""
Tests for GPU detection functionality.
"""

import pytest
from neuron_hw.models import GPUType, GPUVendor, PCIDevice, GPU
from neuron_hw.detect import _classify_vendor, _classify_type, _parse_lspci


class TestClassifyVendor:
    def test_nvidia(self):
        assert _classify_vendor("10de") == GPUVendor.NVIDIA

    def test_amd(self):
        assert _classify_vendor("1002") == GPUVendor.AMD

    def test_intel(self):
        assert _classify_vendor("8086") == GPUVendor.INTEL

    def test_unknown(self):
        assert _classify_vendor("0000") == GPUVendor.UNKNOWN


class TestClassifyType:
    def test_intel_igpu(self):
        device = PCIDevice(
            domain="0000", bus="00", slot="02", function="0",
            vendor_id="8086", device_id="9a49",
            class_code="0300", description="Intel UHD Graphics"
        )
        assert _classify_type(device, GPUVendor.INTEL) == GPUType.INTEGRATED

    def test_intel_arc_dgpu(self):
        device = PCIDevice(
            domain="0000", bus="03", slot="00", function="0",
            vendor_id="8086", device_id="56a0",
            class_code="0300", description="Intel Arc A770"
        )
        assert _classify_type(device, GPUVendor.INTEL) == GPUType.DISCRETE

    def test_nvidia_dgpu(self):
        device = PCIDevice(
            domain="0000", bus="01", slot="00", function="0",
            vendor_id="10de", device_id="2684",
            class_code="0300", description="NVIDIA GeForce RTX 4090"
        )
        assert _classify_type(device, GPUVendor.NVIDIA) == GPUType.DISCRETE

    def test_amd_igpu(self):
        device = PCIDevice(
            domain="0000", bus="06", slot="00", function="0",
            vendor_id="1002", device_id="164e",
            class_code="0300", description="AMD Radeon Graphics"
        )
        assert _classify_type(device, GPUVendor.AMD) == GPUType.INTEGRATED

    def test_amd_dgpu(self):
        device = PCIDevice(
            domain="0000", bus="03", slot="00", function="0",
            vendor_id="1002", device_id="744c",
            class_code="0300", description="AMD Radeon RX 7900 XTX"
        )
        assert _classify_type(device, GPUVendor.AMD) == GPUType.DISCRETE


class TestParseLspci:
    def test_parse_single_gpu(self):
        output = """0000:01:00.0 VGA compatible controller [0300]: NVIDIA Corporation GA102 [GeForce RTX 3090] [10de:2204] (rev a1)
\tKernel driver in use: nvidia
0000:01:00.1 Audio device [0403]: NVIDIA Corporation GA102 High Definition Audio Controller [10de:1aef] (rev a1)
\tKernel driver in use: snd_hda_intel"""

        devices = _parse_lspci(output)
        assert len(devices) == 2

        vga = devices[0]
        assert vga.domain == "0000"
        assert vga.bus == "01"
        assert vga.slot == "00"
        assert vga.function == "0"
        assert vga.vendor_id == "10de"
        assert vga.device_id == "2204"
        assert vga.class_code == "0300"
        assert vga.driver == "nvidia"

        audio = devices[1]
        assert audio.function == "1"
        assert audio.class_code == "0403"

    def test_parse_dual_gpu(self):
        output = """0000:00:02.0 VGA compatible controller [0300]: Intel Corporation UHD Graphics [8086:9a49] (rev 01)
\tKernel driver in use: i915
0000:01:00.0 VGA compatible controller [0300]: NVIDIA Corporation GA102 [GeForce RTX 3090] [10de:2204] (rev a1)
\tKernel driver in use: vfio-pci"""

        devices = _parse_lspci(output)
        assert len(devices) == 2

        igpu = devices[0]
        assert igpu.vendor_id == "8086"
        assert igpu.driver == "i915"

        dgpu = devices[1]
        assert dgpu.vendor_id == "10de"
        assert dgpu.driver == "vfio-pci"


class TestPCIDevice:
    def test_address(self):
        device = PCIDevice(
            domain="0000", bus="01", slot="00", function="0",
            vendor_id="10de", device_id="2684",
            class_code="0300", description="Test"
        )
        assert device.address == "0000:01:00.0"

    def test_vfio_id(self):
        device = PCIDevice(
            domain="0000", bus="01", slot="00", function="0",
            vendor_id="10de", device_id="2684",
            class_code="0300", description="Test"
        )
        assert device.vfio_id == "10de:2684"


class TestGPU:
    def test_all_devices_with_audio(self):
        primary = PCIDevice(
            domain="0000", bus="01", slot="00", function="0",
            vendor_id="10de", device_id="2684",
            class_code="0300", description="GPU"
        )
        audio = PCIDevice(
            domain="0000", bus="01", slot="00", function="1",
            vendor_id="10de", device_id="1aef",
            class_code="0403", description="Audio"
        )
        gpu = GPU(primary_device=primary, audio_device=audio)

        assert len(gpu.all_devices) == 2
        assert gpu.vfio_ids == ["10de:2684", "10de:1aef"]

    def test_all_devices_without_audio(self):
        primary = PCIDevice(
            domain="0000", bus="01", slot="00", function="0",
            vendor_id="10de", device_id="2684",
            class_code="0300", description="GPU"
        )
        gpu = GPU(primary_device=primary)

        assert len(gpu.all_devices) == 1
        assert gpu.vfio_ids == ["10de:2684"]
