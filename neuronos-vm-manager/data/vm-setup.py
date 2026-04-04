#!/usr/bin/env python3
"""
NeuronOS VM Setup Script

Creates and configures the win11-neuron libvirt domain based on
the detected hardware profile. This is run during first-boot or
manually via `neuronvm-setup`.

Responsibilities:
- Reads hardware profile from /etc/neuronos/hardware-profile.json
- Customizes the VM domain XML template with actual PCI addresses
- Adjusts RAM/CPU based on system resources
- Defines the VM in libvirt
- Creates the disk image if it doesn't exist
"""

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

PROFILE_PATH = Path("/etc/neuronos/hardware-profile.json")
TEMPLATE_PATH = Path("/usr/share/neuronos/win11-neuron.xml")
DISK_PATH = Path("/var/lib/libvirt/images/win11-neuron.qcow2")
DISK_SIZE = "100G"


def load_hardware_profile() -> dict:
    """Load the hardware profile generated during installation."""
    if not PROFILE_PATH.exists():
        print(f"WARNING: Hardware profile not found at {PROFILE_PATH}")
        return {}
    return json.loads(PROFILE_PATH.read_text())


def get_resource_allocation() -> dict:
    """Calculate optimal VM resources based on system hardware."""
    total_ram_mb = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") // (1024 * 1024)
    total_cores = os.cpu_count() or 4

    host_ram_mb = max(4096, total_ram_mb // 4)
    host_cores = max(2, total_cores // 4)

    vm_ram_mb = min(total_ram_mb - host_ram_mb, 65536)
    vm_cores = min(total_cores - host_cores, 16)

    return {"ram_mb": vm_ram_mb, "cores": vm_cores}


def customize_domain_xml(profile: dict, resources: dict) -> str:
    """Customize the VM template XML with hardware-specific settings."""
    tree = ET.parse(TEMPLATE_PATH)
    root = tree.getroot()

    # Namespace for QEMU command line
    qemu_ns = "http://libvirt.org/schemas/domain/qemu/1.0"

    # Set memory
    for elem in root.iter("memory"):
        elem.set("unit", "MiB")
        elem.text = str(resources["ram_mb"])
    for elem in root.iter("currentMemory"):
        elem.set("unit", "MiB")
        elem.text = str(resources["ram_mb"])

    # Set CPU cores
    for elem in root.iter("vcpu"):
        elem.text = str(resources["cores"])
    for topology in root.iter("topology"):
        topology.set("cores", str(resources["cores"]))
        topology.set("threads", "1")
        topology.set("sockets", "1")

    # Add GPU passthrough devices if available
    capability = profile.get("capability", "no_passthrough")
    passthrough_gpu = profile.get("passthrough_gpu", {})

    if capability in ("dual_gpu", "single_gpu") and passthrough_gpu.get("pci_address"):
        devices = root.find("devices")
        pci_addr = passthrough_gpu["pci_address"]

        # Parse PCI address (format: "0000:01:00.0")
        parts = pci_addr.replace(".", ":").split(":")
        if len(parts) == 4:
            domain, bus, slot, function = parts

            # Add GPU device
            hostdev = ET.SubElement(devices, "hostdev")
            hostdev.set("mode", "subsystem")
            hostdev.set("type", "pci")
            hostdev.set("managed", "yes")
            source = ET.SubElement(hostdev, "source")
            address = ET.SubElement(source, "address")
            address.set("domain", f"0x{domain}")
            address.set("bus", f"0x{bus}")
            address.set("slot", f"0x{slot}")
            address.set("function", f"0x{function}")

            # Add GPU audio device (typically function 1)
            audio_hostdev = ET.SubElement(devices, "hostdev")
            audio_hostdev.set("mode", "subsystem")
            audio_hostdev.set("type", "pci")
            audio_hostdev.set("managed", "yes")
            audio_source = ET.SubElement(audio_hostdev, "source")
            audio_address = ET.SubElement(audio_source, "address")
            audio_address.set("domain", f"0x{domain}")
            audio_address.set("bus", f"0x{bus}")
            audio_address.set("slot", f"0x{slot}")
            audio_address.set("function", "0x1")

            # For dual-GPU, remove the QXL video device (Looking Glass handles display)
            if capability == "dual_gpu":
                for video in devices.findall("video"):
                    devices.remove(video)
                # Add a "none" video model
                video_elem = ET.SubElement(devices, "video")
                model = ET.SubElement(video_elem, "model")
                model.set("type", "none")

    # Add QEMU command line for Looking Glass IVSHMEM
    qemu_cmdline = root.find(f"{{{qemu_ns}}}commandline")
    if qemu_cmdline is None:
        qemu_cmdline = ET.SubElement(root, f"{{{qemu_ns}}}commandline")

    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def create_disk_image():
    """Create the VM disk image if it doesn't exist."""
    if DISK_PATH.exists():
        print(f"Disk image already exists: {DISK_PATH}")
        return

    DISK_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Creating VM disk image: {DISK_PATH} ({DISK_SIZE})")
    subprocess.run(
        ["qemu-img", "create", "-f", "qcow2", str(DISK_PATH), DISK_SIZE],
        check=True,
    )


def define_vm(xml_content: str):
    """Define the VM in libvirt."""
    # Write temp XML
    tmp_xml = Path("/tmp/win11-neuron.xml")
    tmp_xml.write_text(xml_content)

    try:
        # Check if domain already exists
        result = subprocess.run(
            ["virsh", "dominfo", "win11-neuron"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("VM domain 'win11-neuron' already exists. Updating...")
            subprocess.run(
                ["virsh", "undefine", "win11-neuron", "--nvram"],
                capture_output=True,
            )

        subprocess.run(["virsh", "define", str(tmp_xml)], check=True)
        print("VM domain 'win11-neuron' defined successfully.")
    finally:
        tmp_xml.unlink(missing_ok=True)


def setup_shared_memory():
    """Ensure shared memory files exist for Looking Glass and Scream."""
    shm_files = {
        "/dev/shm/looking-glass": 128 * 1024 * 1024,
        "/dev/shm/scream-ivshmem": 2 * 1024 * 1024,
    }

    for path, size in shm_files.items():
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.truncate(size)
            os.chmod(path, 0o660)
            print(f"Created shared memory: {path}")


def main():
    print("=== NeuronOS VM Setup ===")

    profile = load_hardware_profile()
    resources = get_resource_allocation()

    print(f"System capability: {profile.get('capability', 'unknown')}")
    print(f"Allocating VM resources: {resources['ram_mb']}MB RAM, {resources['cores']} cores")

    if profile.get("passthrough_gpu", {}).get("name"):
        print(f"Passthrough GPU: {profile['passthrough_gpu']['name']}")

    if not TEMPLATE_PATH.exists():
        print(f"ERROR: VM template not found at {TEMPLATE_PATH}")
        sys.exit(1)

    xml_content = customize_domain_xml(profile, resources)
    create_disk_image()
    setup_shared_memory()
    define_vm(xml_content)

    print("=== VM Setup Complete ===")


if __name__ == "__main__":
    main()
