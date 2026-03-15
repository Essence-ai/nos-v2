# NeuronOS — Technical Implementation Guide

**For: The Engineer Who Has To Actually Build This**

---

## Part 0: Reading the Map Before Walking

The NeuronOS spec defines six core challenges and seven milestones. Before touching any code, you need to understand the dependency graph. Everything flows from hardware detection → VFIO config → VM lifecycle → Looking Glass display → application routing → installer polish. You cannot skip ahead. A broken VFIO config means the VM won't boot. A VM that won't boot means Looking Glass has nothing to display. Looking Glass with nothing to display means there's no product.

The build order is:

1. Proof of concept on physical hardware (manual, no code)
2. Automated hardware detection + VFIO config generation
3. VM lifecycle management + Looking Glass integration
4. Application routing + seamless install UX
5. Installer + onboarding
6. Hardware compat matrix + stability
7. Beta

This guide covers steps 1–4 in full technical detail.

---

## Part 1: Upstream Projects — What to Clone, Fork, or Use As-Is

Here is every upstream project NeuronOS depends on, what you do with each, and what you can safely ignore inside them.

### 1.1 Archiso (CLONE, don't fork)

**Repo:** `https://gitlab.archlinux.org/archlinux/archiso`
**What it is:** The official Arch Linux tool for building custom live/install ISOs.
**What you do:** Clone it and use it as a build tool. You don't modify Archiso itself — you create a *profile* (a configuration directory) that Archiso consumes to produce your ISO.

```bash
# Install archiso on your Arch dev machine
sudo pacman -S archiso

# Copy the releng profile as your starting point
cp -r /usr/share/archiso/configs/releng/ ~/neuronos-iso/
```

**Directory structure you care about inside your profile:**

```
neuronos-iso/
├── airootfs/           # Files overlaid onto the live filesystem
│   ├── etc/            # System config files (modprobe, dracut/mkinitcpio, systemd units)
│   ├── usr/            # Custom scripts, .desktop files
│   └── root/           # Auto-run scripts for live environment
├── packages.x86_64     # Package list — one package name per line
├── pacman.conf          # Pacman config (add custom repos here)
├── profiledef.sh        # ISO metadata (name, label, etc.)
└── efiboot/            # EFI boot configuration
```

**What to delete from the releng profile:**
- `airootfs/root/customize_airootfs.sh` — replace with your own
- Any packages in `packages.x86_64` you don't need (the releng list is minimal, you'll mostly be *adding*)
- The default MOTD and shell configs — replace with NeuronOS branding

**What to add to `packages.x86_64`:**

```
# Base system
base
base-devel
linux
linux-firmware
linux-headers
networkmanager
pipewire
pipewire-pulse
pipewire-alsa
wireplumber
bluez
bluez-utils

# Desktop
plasma-meta
kde-applications-meta
sddm
xdg-desktop-portal
xdg-desktop-portal-kde

# Virtualization stack
qemu-full
libvirt
virt-manager
edk2-ovmf
dnsmasq
bridge-utils
dmidecode

# GPU passthrough
vfio-pci           # (built into kernel, but the meta-reference is useful)

# Looking Glass (build from AUR or package yourself)
# looking-glass-client-git   # AUR — you'll need to package this into your custom repo

# Audio bridge
scream              # AUR — same, package it

# Filesystem + rollback
btrfs-progs
snapper
snap-pac
grub-btrfs

# Installer
calamares
calamares-git       # Or your fork

# Build tools for your custom apps
python
python-libvirt
python-pip
pyside6
qt6-base

# Misc
git
wget
curl
htop
neofetch
firefox
```

**Building the ISO:**

```bash
cd ~/neuronos-iso
sudo mkarchiso -v -w /tmp/archiso-tmp -o ~/neuronos-out .
```

This gives you a bootable `.iso` in `~/neuronos-out/`. Test it in a VM first (without GPU passthrough — just verify it boots to SDDM + Plasma), then on physical hardware.

---

### 1.2 Calamares (FORK)

**Repo:** `https://github.com/calamares/calamares`
**What it is:** The graphical installer framework. It's a C++/Qt application with a plugin architecture. Each "step" in the installer (welcome, locale, partition, users, install) is a module.
**What you do:** Fork it. You need to add custom modules, and you'll want to pin a stable version rather than track upstream HEAD.

```bash
git clone https://github.com/calamares/calamares.git neuronos-installer
cd neuronos-installer
git checkout v3.3.x  # Pin to latest stable branch
```

**What you keep:**
- The entire module system and core framework
- Standard modules: `welcome`, `locale`, `keyboard`, `partition`, `users`, `packages`, `bootloader`, `finished`
- The branding system (`src/branding/`)

**What you modify:**
- `src/branding/` — create a `neuronos/` branding directory with your logos, colors, stylesheet, and `branding.desc`
- `settings.conf` — the main config that defines which modules run and in what order

**What you add (custom modules):**

Create these in `src/modules/`:

```
src/modules/
├── neuronhwdetect/       # Hardware detection module (Python)
│   ├── module.desc       # Module metadata
│   ├── neuronhwdetect.conf
│   └── main.py           # Python entry point
├── neuronvfio/           # VFIO configuration writer (Python)
│   ├── module.desc
│   ├── neuronvfio.conf
│   └── main.py
├── neuronvmsetup/        # "Do you need Windows apps?" wizard (Python + QML)
│   ├── module.desc
│   ├── neuronvmsetup.conf
│   ├── main.py
│   └── neuronvmsetup.qml
└── neuronbtrfs/          # BTRFS subvolume + snapper setup (Python)
    ├── module.desc
    ├── neuronbtrfs.conf
    └── main.py
```

**Module descriptor format (`module.desc`):**

```yaml
---
type:       "job"          # "job" = runs silently, "viewmodule" = has a UI page
name:       "neuronhwdetect"
interface:  "python"
script:     "main.py"
```

**Calamares module execution order (in `settings.conf`):**

```yaml
sequence:
  - show:
    - welcome
    - locale
    - keyboard
    - partition
    - users
    - summary
  - exec:
    - partition        # Format disks
    - mount            # Mount target
    - unpackfs         # Copy filesystem
    - machineid
    - fstab
    - locale
    - keyboard
    - localecfg
    - users
    - networkcfg
    - packages
    - neuronhwdetect   # YOUR MODULE: detect GPUs + IOMMU
    - neuronvfio       # YOUR MODULE: write VFIO configs
    - neuronbtrfs      # YOUR MODULE: setup snapper
    - bootloader       # Writes GRUB (using VFIO params from neuronvfio)
    - neuronvmsetup    # YOUR MODULE: queue VM template download
    - finished
```

**What you can ignore in the Calamares repo:**
- `src/modules/netinstall` — NeuronOS uses a live ISO with packages baked in, not a net installer
- `src/modules/oemid`, `src/modules/tracking` — OEM/telemetry stuff you don't need
- CI configs for distros you're not (`.github/workflows/` can be replaced with your own)

---

### 1.3 Looking Glass (CLONE, contribute upstream if needed)

**Repo:** `https://github.com/gnif/LookingGlass`
**What it is:** The shared-memory framebuffer display tool. Has two parts: a Windows "host" app that captures GPU output, and a Linux "client" app that displays it.

```bash
git clone --recursive https://github.com/gnif/LookingGlass.git
cd LookingGlass
```

**What you use:**
- `client/` — the Linux display client. Build this and package it.
- `host/` — the Windows capture application. This gets installed inside the Windows VM template.
- `module/kvmfr/` — the kernel module for shared memory transport (faster than IVSHMEM in some configs).

**Building the client:**

```bash
cd LookingGlass/client
mkdir build && cd build
cmake -DENABLE_WAYLAND=ON -DENABLE_X11=ON ..
make -j$(nproc)
# Binary: build/looking-glass-client
```

**What you don't modify:** The core Looking Glass code. It's actively maintained. You build a *wrapper* around `looking-glass-client` that handles:
- Auto-launching it when a VM app is requested
- Setting the correct `-F` (borderless) flags
- Managing window geometry
- Handling the lifecycle (kill client when VM shuts down)

**Key Looking Glass client flags you'll use:**

```bash
looking-glass-client \
  -F                          # Borderless fullscreen
  -m 97                       # Shared memory size (MB), must match QEMU config
  -p 0                        # Disable screensaver inhibit
  -K                          # Disable grab on focus
  -S                          # Disable screen saver
  app:renderer=egl            # Use EGL renderer (better Wayland compat)
  win:size=1920x1080          # Window size
  win:title="Adobe Photoshop" # Window title (so taskbar shows app name)
  input:grabKeyboard=no       # Don't grab keyboard by default
```

Your wrapper (part of `neuronos-vm-manager`) will construct these arguments dynamically.

---

### 1.4 Scream (CLONE)

**Repo:** `https://github.com/duncanthrax/scream`
**What it is:** Virtual sound card for Windows VMs. Sends audio from the VM to the Linux host over IVSHMEM or network.

```bash
git clone https://github.com/duncanthrax/scream.git
```

**What you use:**
- `Receivers/pulseaudio-ivshmem/` or `Receivers/pipewire/` — the Linux receiver. PipeWire is preferred since NeuronOS uses PipeWire.
- `Install/` — the Windows driver that gets installed in the VM template.

**What you don't touch:** The core Scream code. You package the receiver as a systemd service:

```ini
# /etc/systemd/user/scream-receiver.service
[Unit]
Description=Scream Audio Receiver
After=pipewire.service

[Service]
Type=simple
ExecStart=/usr/bin/scream -o pipewire -m /dev/shm/scream-ivshmem
Restart=on-failure

[Install]
WantedBy=default.target
```

---

### 1.5 QEMU/KVM + libvirt + OVMF (USE AS-IS)

**No cloning needed.** These are standard Arch packages:

```bash
sudo pacman -S qemu-full libvirt virt-manager edk2-ovmf dnsmasq
sudo systemctl enable --now libvirtd
sudo usermod -aG libvirt $USER
```

You interact with these entirely through libvirt's API (Python bindings: `python-libvirt`). You never invoke QEMU directly. Your VM configuration is a libvirt domain XML file.

---

### 1.6 Summary Table

| Project | Action | Modify? | Where it lives in NeuronOS |
|---------|--------|---------|---------------------------|
| Archiso | Clone profile template | Config only | `neuronos-iso/` |
| Calamares | Fork | Add modules + branding | `neuronos-installer/` |
| Looking Glass | Clone | Don't modify, build wrapper around it | `neuronos-vm-manager/` (wrapper) |
| Scream | Clone | Don't modify, package receiver | `neuronos-iso/` (package) |
| QEMU/KVM/libvirt/OVMF | pacman install | Never | System packages |
| KDE Plasma | pacman install | Theme config only | `neuronos-iso/` (dotfiles) |
| BTRFS/Snapper/grub-btrfs | pacman install | Config only | `neuronos-iso/` (config files) |

---

## Part 2: Proof of Concept (Week 1–2)

Before writing a single line of product code, you validate the entire GPU passthrough pipeline manually. This is non-negotiable. If this doesn't work on your hardware, nothing else matters.

### 2.1 Hardware Requirements for PoC

You need a machine with:
- **CPU:** Intel (VT-d support) or AMD (AMD-Vi support). 10th gen+ Intel or Ryzen 3000+ AMD.
- **Two GPUs:** An integrated GPU (Intel UHD or AMD APU) AND a discrete GPU (NVIDIA or AMD). The iGPU runs Linux, the dGPU goes to the VM.
- **RAM:** 16GB minimum (8GB for host, 8GB for VM).
- **Storage:** 100GB+ free (Windows VM image is ~40GB after setup).

### 2.2 Step-by-Step Manual PoC

**Step 1: Install Arch Linux (base + KDE)**

Follow the standard Arch installation. Use BTRFS for the filesystem. Install on the iGPU — make sure your monitor is connected to the motherboard video output, not the discrete GPU.

```bash
# During install, after pacstrap, add:
pacstrap /mnt base linux linux-firmware base-devel \
  networkmanager plasma-meta sddm \
  qemu-full libvirt virt-manager edk2-ovmf \
  looking-glass dnsmasq bridge-utils \
  btrfs-progs vim git wget

# Enable services
arch-chroot /mnt systemctl enable sddm NetworkManager libvirtd
```

**Step 2: Verify IOMMU support**

```bash
# Check CPU flags
grep -E '(vmx|svm)' /proc/cpuinfo
# vmx = Intel VT-x, svm = AMD-V

# Enable IOMMU in GRUB
sudo vim /etc/default/grub
# For Intel, add to GRUB_CMDLINE_LINUX_DEFAULT:
#   intel_iommu=on iommu=pt
# For AMD:
#   amd_iommu=on iommu=pt

sudo grub-mkconfig -o /boot/grub/grub.cfg
sudo reboot
```

**Step 3: Verify IOMMU is active and map groups**

```bash
# Verify IOMMU is on
dmesg | grep -i -e DMAR -e IOMMU
# Should see "IOMMU enabled" or "DMAR: IOMMU enabled"

# List all IOMMU groups and their devices
#!/bin/bash
for g in $(find /sys/kernel/iommu_groups/* -maxdepth 0 -type d | sort -V); do
    echo "IOMMU Group ${g##*/}:"
    for d in $g/devices/*; do
        echo -e "\t$(lspci -nns ${d##*/})"
    done
done
```

**CRITICAL:** Find your discrete GPU in the output. Note its:
- **PCI bus address** (e.g., `01:00.0`)
- **Vendor:Device IDs** (e.g., `10de:2684` for an NVIDIA RTX 4090)
- **IOMMU group number**

The GPU and its audio function (e.g., `01:00.1`) must be in the same IOMMU group, and ideally that group should contain ONLY those two devices. If other devices share the group, you'll need ACS override patches (a problem the hardware detection system must handle).

**Step 4: Bind the discrete GPU to VFIO**

```bash
# Create VFIO config
# Replace IDs with YOUR GPU's vendor:device IDs
sudo tee /etc/modprobe.d/vfio.conf <<EOF
options vfio-pci ids=10de:2684,10de:22ba
softdep nvidia pre: vfio-pci
softdep nouveau pre: vfio-pci
EOF

# Load VFIO modules early in initramfs
sudo tee /etc/mkinitcpio.conf.d/vfio.conf <<EOF
MODULES=(vfio_pci vfio vfio_iommu_type1)
EOF

# Rebuild initramfs
sudo mkinitcpio -P

sudo reboot
```

**Step 5: Verify VFIO binding**

```bash
# After reboot, check the GPU is bound to vfio-pci
lspci -nnk -s 01:00
# Should show: Kernel driver in use: vfio-pci
```

**Step 6: Create the Windows VM**

Download the Windows 11 ISO and VirtIO drivers ISO:
- Windows 11: `https://www.microsoft.com/software-download/windows11`
- VirtIO: `https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso`

Create the VM domain XML. Save this as `win11-passthrough.xml`:

```xml
<domain type='kvm' xmlns:qemu='http://libvirt.org/schemas/domain/qemu/1.0'>
  <name>win11-neuron</name>
  <memory unit='GiB'>8</memory>
  <vcpu placement='static'>6</vcpu>
  <cpu mode='host-passthrough' check='none' migratable='on'>
    <topology sockets='1' dies='1' cores='6' threads='1'/>
  </cpu>
  <os>
    <type arch='x86_64' machine='pc-q35-9.0'>hvm</type>
    <loader readonly='yes' type='pflash'>/usr/share/edk2/x64/OVMF_CODE.4m.fd</loader>
    <nvram template='/usr/share/edk2/x64/OVMF_VARS.4m.fd'/>
    <boot dev='cdrom'/>
  </os>
  <features>
    <acpi/>
    <apic/>
    <hyperv mode='custom'>
      <relaxed state='on'/>
      <vapic state='on'/>
      <spinlocks state='on' retries='8191'/>
      <vpindex state='on'/>
      <runtime state='on'/>
      <synic state='on'/>
      <stimer state='on'/>
      <vendor_id state='on' value='AuthenticAMD'/>
    </hyperv>
    <kvm>
      <hidden state='on'/>
    </kvm>
  </features>
  <clock offset='localtime'>
    <timer name='rtc' tickpolicy='catchup'/>
    <timer name='pit' tickpolicy='delay'/>
    <timer name='hpet' present='no'/>
    <timer name='hypervclock' present='yes'/>
  </clock>
  <devices>
    <!-- VirtIO disk -->
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2' discard='unmap'/>
      <source file='/var/lib/libvirt/images/win11.qcow2'/>
      <target dev='vda' bus='virtio'/>
    </disk>
    <!-- Windows ISO -->
    <disk type='file' device='cdrom'>
      <driver name='qemu' type='raw'/>
      <source file='/path/to/Win11.iso'/>
      <target dev='sda' bus='sata'/>
      <readonly/>
    </disk>
    <!-- VirtIO drivers ISO -->
    <disk type='file' device='cdrom'>
      <driver name='qemu' type='raw'/>
      <source file='/path/to/virtio-win.iso'/>
      <target dev='sdb' bus='sata'/>
      <readonly/>
    </disk>
    <!-- GPU passthrough -->
    <hostdev mode='subsystem' type='pci' managed='yes'>
      <source>
        <address domain='0x0000' bus='0x01' slot='0x00' function='0x0'/>
      </source>
    </hostdev>
    <!-- GPU audio function -->
    <hostdev mode='subsystem' type='pci' managed='yes'>
      <source>
        <address domain='0x0000' bus='0x01' slot='0x00' function='0x1'/>
      </source>
    </hostdev>
    <!-- Looking Glass shared memory -->
    <shmem name='looking-glass'>
      <model type='ivshmem-plain'/>
      <size unit='M'>128</size>
    </shmem>
    <!-- Scream audio shared memory -->
    <shmem name='scream-ivshmem'>
      <model type='ivshmem-plain'/>
      <size unit='M'>2</size>
    </shmem>
    <!-- VirtIO network -->
    <interface type='network'>
      <source network='default'/>
      <model type='virtio'/>
    </interface>
    <!-- Spice for initial setup (before Looking Glass works) -->
    <graphics type='spice' autoport='yes'/>
    <video>
      <model type='none'/>
    </video>
    <!-- Input -->
    <input type='mouse' bus='virtio'/>
    <input type='keyboard' bus='virtio'/>
  </devices>
  <qemu:commandline>
    <qemu:arg value='-device'/>
    <qemu:arg value='ivshmem-plain,memdev=ivshmem,bus=pcie.0'/>
    <qemu:arg value='-object'/>
    <qemu:arg value='memory-backend-file,id=ivshmem,share=on,mem-path=/dev/shm/looking-glass,size=128M'/>
  </qemu:commandline>
</domain>
```

**IMPORTANT NOTES on this XML:**
- Replace PCI addresses (`bus='0x01' slot='0x00'`) with YOUR GPU's actual addresses from `lspci`
- The `<kvm><hidden state='on'/>` and fake `vendor_id` prevent NVIDIA drivers from detecting they're in a VM (NVIDIA Code 43 workaround)
- `<hyperv>` features improve Windows performance significantly
- The `ivshmem` shared memory device is what Looking Glass uses to transfer frames

```bash
# Create the disk image
sudo qemu-img create -f qcow2 /var/lib/libvirt/images/win11.qcow2 100G

# Create the shared memory file
sudo touch /dev/shm/looking-glass
sudo chown $USER:kvm /dev/shm/looking-glass
sudo chmod 0660 /dev/shm/looking-glass

# Create a tmpfiles.d rule so it persists across reboots
sudo tee /etc/tmpfiles.d/looking-glass.conf <<EOF
f /dev/shm/looking-glass 0660 $USER kvm -
EOF

# Same for Scream
sudo tee /etc/tmpfiles.d/scream-ivshmem.conf <<EOF
f /dev/shm/scream-ivshmem 0660 $USER kvm -
EOF

# Define and start the VM
sudo virsh define win11-passthrough.xml
sudo virsh start win11-neuron
```

**Step 7: Install Windows, then install VM guest tools**

Connect via `virt-viewer` or Spice initially. Install Windows 11, then:

1. Install VirtIO drivers from the mounted VirtIO ISO (Device Manager → Update driver → browse to VirtIO ISO)
2. Install the Looking Glass Host application (`looking-glass-host-setup.exe` — download from Looking Glass releases)
3. Install the Scream virtual audio driver from the Scream repo (`Install/` directory)
4. Disable Windows Defender, Cortana, telemetry, and unnecessary services
5. Shut down the VM

**Step 8: Test Looking Glass**

```bash
# Start the VM
sudo virsh start win11-neuron

# Wait ~15 seconds for Windows to boot, then:
looking-glass-client -F
```

You should see the Windows desktop in a borderless window on your Linux desktop. Move your mouse in and out. Open an application in Windows. Verify that:
- Display is sharp, no artifacts
- Mouse input is responsive
- Audio plays through Scream → PipeWire → your speakers
- GPU-accelerated apps (run GPU-Z or a game) show the passed-through GPU at full performance

**Step 9: Benchmark**

Run the same GPU benchmark (3DMark, Unigine Heaven, or a specific game) on:
1. Bare-metal Windows (install Windows directly, run benchmark, note scores)
2. The VM with passthrough

Performance should be within 1-5% for GPU-bound workloads. If it's significantly worse, check that the GPU driver is installed correctly in the VM and that no emulated video device is interfering.

**Step 10: Document everything**

Every command you ran, every config file you wrote, every edge case you hit. This becomes the specification for the automated systems.

---

## Part 3: Building the Hardware Detection System (`neuronos-hardware`)

This is the first real code you write. It automates everything you did manually in Part 2, Steps 2-5.

### 3.1 Architecture

```
neuronos-hardware/
├── neuron_hw/
│   ├── __init__.py
│   ├── detect.py          # GPU detection + classification
│   ├── iommu.py           # IOMMU group analysis
│   ├── vfio_config.py     # Generate VFIO config files
│   ├── grub_config.py     # Generate GRUB kernel parameters
│   ├── initramfs.py       # Generate mkinitcpio hooks
│   ├── compatibility.py   # Hardware compat database lookups
│   └── models.py          # Data classes for GPU, IOMMUGroup, etc.
├── data/
│   └── hardware_db.yaml   # Known hardware quirks + compat data
├── calamares_module/
│   ├── module.desc
│   └── main.py            # Calamares entry point (imports from neuron_hw)
├── systemd/
│   └── neuron-hw-check.service  # Boot-time verification service
├── tests/
│   ├── test_detect.py
│   ├── test_iommu.py
│   └── fixtures/          # Captured lspci/iommu outputs from real hardware
└── setup.py
```

### 3.2 Core Detection Logic (`detect.py`)

```python
"""
GPU detection and classification.
Parses lspci output to identify all GPUs, their types, and PCI topology.
"""
import subprocess
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class GPUType(Enum):
    INTEGRATED = "integrated"
    DISCRETE = "discrete"
    UNKNOWN = "unknown"


class GPUVendor(Enum):
    INTEL = "intel"
    AMD = "amd"
    NVIDIA = "nvidia"
    UNKNOWN = "unknown"


@dataclass
class PCIDevice:
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
        return f"{self.domain}:{self.bus}:{self.slot}.{self.function}"

    @property
    def vfio_id(self) -> str:
        return f"{self.vendor_id}:{self.device_id}"


@dataclass
class GPU:
    primary_device: PCIDevice          # The VGA/3D controller
    audio_device: Optional[PCIDevice]  # HDMI audio (same slot, function 1)
    gpu_type: GPUType = GPUType.UNKNOWN
    vendor: GPUVendor = GPUVendor.UNKNOWN
    name: str = ""


class PassthroughCapability(Enum):
    DUAL_GPU = "dual_gpu"          # iGPU for host, dGPU for VM (best)
    SINGLE_GPU = "single_gpu"      # Only one GPU, dynamic switching required
    NO_PASSTHROUGH = "no_passthrough"  # IOMMU not available or GPU not isolatable


@dataclass
class HardwareProfile:
    gpus: list[GPU] = field(default_factory=list)
    iommu_enabled: bool = False
    cpu_vendor: str = ""  # "intel" or "amd"
    capability: PassthroughCapability = PassthroughCapability.NO_PASSTHROUGH
    host_gpu: Optional[GPU] = None       # GPU that stays with Linux
    passthrough_gpu: Optional[GPU] = None # GPU that goes to the VM
    warnings: list[str] = field(default_factory=list)


def detect_gpus() -> list[GPU]:
    """Parse lspci to find all GPUs in the system."""
    # -nn gives numeric IDs, -mm gives machine-readable, -k shows kernel driver
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
            r'(DMAR:.*IOMMU enabled|AMD-Vi:.*IOMMU.*enabled)',
            result.stdout
        ))
    except subprocess.CalledProcessError:
        return False


def get_iommu_groups() -> dict[int, list[PCIDevice]]:
    """Map IOMMU group numbers to their member devices."""
    groups: dict[int, list[PCIDevice]] = {}
    iommu_base = "/sys/kernel/iommu_groups"

    # Walk /sys/kernel/iommu_groups/*/devices/*
    import os
    for group_dir in sorted(os.listdir(iommu_base)):
        group_num = int(group_dir)
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


def build_hardware_profile() -> HardwareProfile:
    """
    Main entry point. Detects all hardware and determines the optimal
    passthrough configuration.
    """
    profile = HardwareProfile()

    # Detect CPU vendor
    with open("/proc/cpuinfo") as f:
        cpuinfo = f.read()
    if "GenuineIntel" in cpuinfo:
        profile.cpu_vendor = "intel"
    elif "AuthenticAMD" in cpuinfo:
        profile.cpu_vendor = "amd"

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
    vendor_map = {"8086": GPUVendor.INTEL, "1002": GPUVendor.AMD, "10de": GPUVendor.NVIDIA}
    return vendor_map.get(vendor_id, GPUVendor.UNKNOWN)


def _classify_type(device: PCIDevice, vendor: GPUVendor) -> GPUType:
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
```

### 3.3 VFIO Config Generation (`vfio_config.py`)

```python
"""
Generate all system configuration files needed for VFIO passthrough.
"""
from neuron_hw.detect import HardwareProfile, PassthroughCapability


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

    return "\n".join(lines)


def generate_mkinitcpio_conf(profile: HardwareProfile) -> str:
    """Generate /etc/mkinitcpio.conf.d/vfio.conf content."""
    if profile.capability == PassthroughCapability.DUAL_GPU:
        return "MODULES=(vfio_pci vfio vfio_iommu_type1)"
    return ""


def write_configs(profile: HardwareProfile, target_root: str = "/"):
    """
    Write all config files to the target filesystem.
    target_root is "/" for live system or "/mnt" during installation.
    """
    import os

    # GRUB
    grub_params = generate_grub_params(profile)
    grub_default = os.path.join(target_root, "etc/default/grub")
    if os.path.exists(grub_default):
        with open(grub_default) as f:
            content = f.read()
        # Append our params to GRUB_CMDLINE_LINUX_DEFAULT
        import re
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

    # Save the profile for other NeuronOS components to read
    import json
    neuron_dir = os.path.join(target_root, "etc/neuronos")
    os.makedirs(neuron_dir, exist_ok=True)
    with open(os.path.join(neuron_dir, "hardware-profile.json"), "w") as f:
        json.dump(_profile_to_dict(profile), f, indent=2)


def _profile_to_dict(profile: HardwareProfile) -> dict:
    """Serialize the profile for JSON storage."""
    return {
        "cpu_vendor": profile.cpu_vendor,
        "iommu_enabled": profile.iommu_enabled,
        "capability": profile.capability.value,
        "passthrough_gpu": {
            "name": profile.passthrough_gpu.name if profile.passthrough_gpu else None,
            "vendor": profile.passthrough_gpu.vendor.value if profile.passthrough_gpu else None,
            "pci_address": profile.passthrough_gpu.primary_device.address if profile.passthrough_gpu else None,
            "vfio_ids": profile.passthrough_gpu.primary_device.vfio_id if profile.passthrough_gpu else None,
        },
        "host_gpu": {
            "name": profile.host_gpu.name if profile.host_gpu else None,
            "pci_address": profile.host_gpu.primary_device.address if profile.host_gpu else None,
        },
        "warnings": profile.warnings,
    }
```

### 3.4 Calamares Integration (`calamares_module/main.py`)

```python
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

    profile = build_hardware_profile()

    libcalamares.utils.debug(
        f"NeuronOS: Detected {len(profile.gpus)} GPU(s), "
        f"capability: {profile.capability.value}"
    )

    for warning in profile.warnings:
        libcalamares.utils.warning(f"NeuronOS: {warning}")

    # Write configs to the target filesystem
    write_configs(profile, target_root=root_mount)

    libcalamares.utils.debug("NeuronOS: VFIO configuration written.")

    # Store results in Calamares global storage for other modules to use
    libcalamares.globalstorage.insert(
        "neuron_hw_capability", profile.capability.value
    )
    libcalamares.globalstorage.insert(
        "neuron_hw_warnings", profile.warnings
    )

    return None  # Success
```

---

## Part 4: The Single-GPU Switching System (`neuronos-single-gpu`)

This is the most dangerous code in the project. A bug here means a black screen the user can't recover from.

### 4.1 Architecture

```
neuronos-single-gpu/
├── scripts/
│   ├── gpu-switch-to-vm.sh      # Unbind GPU from host, start VM
│   ├── gpu-switch-to-host.sh    # Stop VM, rebind GPU to host
│   └── common.sh                # Shared functions
├── hooks/
│   ├── qemu-hook.sh             # libvirt hook: /etc/libvirt/hooks/qemu
│   └── prepare-begin.sh         # Called by libvirt before VM starts
│   └── release-end.sh           # Called by libvirt after VM stops
└── systemd/
    └── neuron-gpu-recovery.service  # Failsafe: recovers display if switch fails
```

### 4.2 The GPU Switch Script

```bash
#!/bin/bash
# gpu-switch-to-vm.sh
# Unbinds the GPU from the Linux host and prepares it for VM passthrough.
# THIS WILL CAUSE A SCREEN BLACKOUT.

set -euo pipefail

# Load hardware profile
PROFILE="/etc/neuronos/hardware-profile.json"
GPU_PCI=$(jq -r '.passthrough_gpu.pci_address' "$PROFILE")
GPU_VENDOR=$(jq -r '.passthrough_gpu.vendor' "$PROFILE")

# Determine which driver modules to unload
case "$GPU_VENDOR" in
    nvidia)
        MODULES_TO_UNLOAD="nvidia_drm nvidia_modeset nvidia_uvm nvidia"
        ;;
    amd)
        MODULES_TO_UNLOAD="amdgpu"
        ;;
    intel)
        MODULES_TO_UNLOAD="i915"
        ;;
    *)
        echo "ERROR: Unknown GPU vendor: $GPU_VENDOR" >&2
        exit 1
        ;;
esac

# Send notification to user before we kill the display
notify-send --urgency=critical --expire-time=5000 \
    "NeuronOS" \
    "Starting Windows application. Your screen will go black for ~5 seconds while the graphics card switches."

sleep 3  # Give user time to read the notification

# --- POINT OF NO RETURN ---

# 1. Stop the display manager
echo "Stopping display manager..."
systemctl stop sddm

# Wait for all Xorg/Wayland sessions to terminate
sleep 2

# 2. Unbind VTconsole (framebuffer) to release the GPU
echo 0 > /sys/class/vtconsole/vtcon0/bind 2>/dev/null || true
echo 0 > /sys/class/vtconsole/vtcon1/bind 2>/dev/null || true

# 3. Unbind EFI framebuffer
echo "efi-framebuffer.0" > /sys/bus/platform/drivers/efi-framebuffer/unbind 2>/dev/null || true

# 4. Unload GPU driver modules
for mod in $MODULES_TO_UNLOAD; do
    if lsmod | grep -q "^$mod "; then
        echo "Unloading $mod..."
        modprobe -r "$mod" || {
            echo "WARNING: Failed to unload $mod, retrying..."
            sleep 1
            modprobe -r "$mod" || echo "ERROR: Could not unload $mod" >&2
        }
    fi
done

# 5. Load VFIO modules
modprobe vfio-pci

# 6. Bind the GPU to vfio-pci
# Get the GPU's vendor:device ID
GPU_ID=$(lspci -ns "$GPU_PCI" | awk '{print $3}')
echo "$GPU_ID" > /sys/bus/pci/drivers/vfio-pci/new_id 2>/dev/null || true

# Also bind the audio function if present
AUDIO_PCI="${GPU_PCI%.*}.1"
if lspci -s "$AUDIO_PCI" &>/dev/null; then
    AUDIO_ID=$(lspci -ns "$AUDIO_PCI" | awk '{print $3}')
    echo "$AUDIO_ID" > /sys/bus/pci/drivers/vfio-pci/new_id 2>/dev/null || true
fi

echo "GPU bound to VFIO. Ready for VM launch."
```

```bash
#!/bin/bash
# gpu-switch-to-host.sh
# Rebinds the GPU to the Linux host after the VM shuts down.

set -euo pipefail

PROFILE="/etc/neuronos/hardware-profile.json"
GPU_PCI=$(jq -r '.passthrough_gpu.pci_address' "$PROFILE")
GPU_VENDOR=$(jq -r '.passthrough_gpu.vendor' "$PROFILE")

# 1. Unbind from vfio-pci
echo "$GPU_PCI" > /sys/bus/pci/drivers/vfio-pci/unbind 2>/dev/null || true
AUDIO_PCI="${GPU_PCI%.*}.1"
echo "$AUDIO_PCI" > /sys/bus/pci/drivers/vfio-pci/unbind 2>/dev/null || true

# 2. Remove VFIO modules
modprobe -r vfio-pci

# 3. Reload GPU driver
case "$GPU_VENDOR" in
    nvidia)
        modprobe nvidia_drm modeset=1
        ;;
    amd)
        modprobe amdgpu
        ;;
    intel)
        modprobe i915
        ;;
esac

# 4. Rebind VT console
echo 1 > /sys/class/vtconsole/vtcon0/bind 2>/dev/null || true
echo 1 > /sys/class/vtconsole/vtcon1/bind 2>/dev/null || true

# 5. Restart display manager
sleep 1
systemctl start sddm

echo "GPU returned to host. Desktop restored."
```

### 4.3 The libvirt Hook

libvirt supports hooks — scripts that run automatically before/after VM lifecycle events. This is how you connect the GPU switching to VM start/stop.

```bash
#!/bin/bash
# /etc/libvirt/hooks/qemu
# Called by libvirt for every VM lifecycle event.
# Arguments: $1=VM_NAME $2=OPERATION $3=SUB_OPERATION

VM_NAME="$1"
OPERATION="$2"
SUB_OPERATION="$3"

# Only act on our NeuronOS VM
if [ "$VM_NAME" != "win11-neuron" ]; then
    exit 0
fi

# Check if we're in single-GPU mode
CAPABILITY=$(jq -r '.capability' /etc/neuronos/hardware-profile.json)
if [ "$CAPABILITY" != "single_gpu" ]; then
    exit 0
fi

case "$OPERATION/$SUB_OPERATION" in
    prepare/begin)
        /usr/lib/neuronos/gpu-switch-to-vm.sh
        ;;
    release/end)
        /usr/lib/neuronos/gpu-switch-to-host.sh
        ;;
esac
```

### 4.4 Failsafe Recovery

```ini
# /etc/systemd/system/neuron-gpu-recovery.service
# If the GPU switch fails and SDDM doesn't come back within 30 seconds,
# force a recovery.
[Unit]
Description=NeuronOS GPU Recovery Failsafe
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/lib/neuronos/gpu-recovery-check.sh
RemainAfterExit=no
```

```bash
#!/bin/bash
# gpu-recovery-check.sh
# Runs at boot. If SDDM isn't running and the GPU is bound to vfio-pci,
# something went wrong. Recover.

sleep 30  # Wait for normal boot to complete

if ! systemctl is-active --quiet sddm; then
    if lspci -ks "$GPU_PCI" | grep -q "vfio-pci"; then
        logger "NeuronOS: GPU recovery triggered — SDDM not running, GPU still on VFIO"
        /usr/lib/neuronos/gpu-switch-to-host.sh
    fi
fi
```

---

## Part 5: VM Lifecycle Manager (Core of `neuronos-vm-manager`)

### 5.1 Architecture

```
neuronos-vm-manager/
├── neuronvm/
│   ├── __init__.py
│   ├── lifecycle.py       # VM start/stop/suspend, resource allocation
│   ├── looking_glass.py   # Looking Glass client wrapper
│   ├── domain_xml.py      # Generate/modify libvirt domain XML
│   ├── app_router.py      # Decision engine: native vs Wine vs VM
│   ├── download_monitor.py # inotify watcher for .exe/.msi files
│   ├── desktop_entry.py   # Generate .desktop files for VM apps
│   └── config.py          # Settings, paths, constants
├── data/
│   └── app_database.yaml  # Curated application routing database
├── ui/                    # Qt6/PySide6 GUI
│   ├── main_window.py
│   ├── app_list.py
│   ├── settings.py
│   └── resources/
├── main.py                # Entry point
└── setup.py
```

### 5.2 VM Lifecycle Manager (`lifecycle.py`)

```python
"""
Manages the Windows VM lifecycle through libvirt.
Handles start, stop, suspend, and dynamic resource allocation.
"""
import libvirt
import json
import time
import threading
from pathlib import Path
from typing import Optional


class VMLifecycleManager:
    DOMAIN_NAME = "win11-neuron"
    GRACE_PERIOD_SECONDS = 300  # Keep VM alive 5 min after last app closes

    def __init__(self):
        self._conn: Optional[libvirt.virConnect] = None
        self._domain: Optional[libvirt.virDomain] = None
        self._active_apps: set[str] = set()
        self._shutdown_timer: Optional[threading.Timer] = None
        self._hw_profile = self._load_hw_profile()

    def _load_hw_profile(self) -> dict:
        profile_path = Path("/etc/neuronos/hardware-profile.json")
        if profile_path.exists():
            return json.loads(profile_path.read_text())
        return {}

    def _connect(self):
        if self._conn is None or not self._conn.isAlive():
            self._conn = libvirt.open("qemu:///system")
        try:
            self._domain = self._conn.lookupByName(self.DOMAIN_NAME)
        except libvirt.libvirtError:
            self._domain = None

    def is_running(self) -> bool:
        self._connect()
        if self._domain is None:
            return False
        state, _ = self._domain.state()
        return state == libvirt.VIR_DOMAIN_RUNNING

    def start_vm(self) -> bool:
        """Start the VM. Returns True if VM is now running."""
        if self.is_running():
            return True

        self._connect()
        if self._domain is None:
            raise RuntimeError(f"VM domain '{self.DOMAIN_NAME}' not found. "
                               f"Run the VM setup wizard first.")

        # Cancel any pending shutdown
        if self._shutdown_timer:
            self._shutdown_timer.cancel()
            self._shutdown_timer = None

        try:
            self._domain.create()  # libvirt "create" = start
            # Wait for VM to be fully booted (poll for QEMU guest agent)
            for _ in range(60):  # 60 second timeout
                if self.is_running():
                    time.sleep(1)
                    # TODO: Check for Looking Glass host readiness
                    return True
                time.sleep(1)
            return False
        except libvirt.libvirtError as e:
            raise RuntimeError(f"Failed to start VM: {e}")

    def stop_vm(self, force: bool = False):
        """Gracefully shut down the VM (or force-kill if needed)."""
        if not self.is_running():
            return

        try:
            if force:
                self._domain.destroy()  # Immediate power off
            else:
                self._domain.shutdown()  # Graceful ACPI shutdown
                # Wait up to 30 seconds for shutdown
                for _ in range(30):
                    if not self.is_running():
                        return
                    time.sleep(1)
                # Force kill if graceful failed
                self._domain.destroy()
        except libvirt.libvirtError as e:
            raise RuntimeError(f"Failed to stop VM: {e}")

    def register_app(self, app_name: str):
        """Called when a VM app is launched. Starts VM if needed."""
        self._active_apps.add(app_name)
        if self._shutdown_timer:
            self._shutdown_timer.cancel()
            self._shutdown_timer = None
        if not self.is_running():
            self.start_vm()

    def unregister_app(self, app_name: str):
        """Called when a VM app closes. Schedules shutdown if no apps left."""
        self._active_apps.discard(app_name)
        if not self._active_apps:
            self._shutdown_timer = threading.Timer(
                self.GRACE_PERIOD_SECONDS,
                self._grace_period_expired
            )
            self._shutdown_timer.start()

    def _grace_period_expired(self):
        """No apps have been launched during the grace period. Shut down."""
        if not self._active_apps:
            self.stop_vm()

    def get_resource_allocation(self) -> dict:
        """
        Calculate optimal VM resource allocation based on system resources.
        """
        import os

        total_ram_mb = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') // (1024 * 1024)
        total_cores = os.cpu_count() or 4

        # Reserve minimum resources for the Linux host
        host_ram_mb = max(4096, total_ram_mb // 4)  # At least 4GB or 25%
        host_cores = max(2, total_cores // 4)        # At least 2 cores or 25%

        vm_ram_mb = total_ram_mb - host_ram_mb
        vm_cores = total_cores - host_cores

        # Cap VM resources at reasonable maximums
        vm_ram_mb = min(vm_ram_mb, 65536)  # 64GB max
        vm_cores = min(vm_cores, 16)        # 16 cores max

        return {
            "ram_mb": vm_ram_mb,
            "cores": vm_cores,
            "host_ram_mb": host_ram_mb,
            "host_cores": host_cores,
        }
```

### 5.3 Looking Glass Wrapper (`looking_glass.py`)

```python
"""
Wrapper around the Looking Glass client that provides the seamless
application-window experience.
"""
import subprocess
import threading
from typing import Optional


class LookingGlassWrapper:
    LG_CLIENT_PATH = "/usr/bin/looking-glass-client"
    SHM_PATH = "/dev/shm/looking-glass"

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._monitor_thread: Optional[threading.Thread] = None

    def launch(self, app_name: str = "Windows Application",
               width: int = 1920, height: int = 1080):
        """Launch Looking Glass client in borderless mode."""
        if self._process and self._process.poll() is None:
            # Already running — just bring to front
            # (use wmctrl or xdotool to focus the window)
            return

        cmd = [
            self.LG_CLIENT_PATH,
            "-F",                           # Borderless
            "-m", "128",                    # Shared memory size
            "-S",                           # Disable screensaver
            f"app:renderer=egl",
            f"win:size={width}x{height}",
            f"win:title={app_name}",
            "win:autoResize=yes",
            "input:autoCapture=yes",
            "input:escapeKey=KEY_RIGHTCTRL",
            "spice:enable=no",              # We don't use Spice display
        ]

        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Monitor the process in a background thread
        self._monitor_thread = threading.Thread(
            target=self._monitor, daemon=True
        )
        self._monitor_thread.start()

    def _monitor(self):
        """Watch the Looking Glass process and handle exit."""
        if self._process:
            self._process.wait()
            # Looking Glass exited — either user closed it or VM shut down
            # Fire a callback or event here

    def stop(self):
        if self._process and self._process.poll() is None:
            self._process.terminate()
            self._process.wait(timeout=5)

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None
```

---

## Part 6: Application Routing Database

### 6.1 Database Format (`app_database.yaml`)

```yaml
# Application routing database
# Execution paths: native | wine | proton | vm
# Priority: native > wine/proton > vm (always prefer least overhead)

applications:
  # Native Linux apps — always prefer these
  - name: "LibreOffice"
    package: "libreoffice-fresh"
    path: native
    category: "Office"
    aliases: ["word processor", "spreadsheet", "office suite"]

  - name: "GIMP"
    package: "gimp"
    path: native
    category: "Image Editing"
    aliases: ["photo editor", "image editor"]

  - name: "DaVinci Resolve"
    package: "davinci-resolve"  # AUR
    path: native
    category: "Video Editing"

  # Wine/Proton apps — good compatibility, no VM overhead
  - name: "Microsoft Office 365"
    path: wine
    wine_prefix: "office365"
    wine_version: "wine-staging"
    category: "Office"
    notes: "Installs via official installer. Some features limited."

  # VM-required apps — need full Windows GPU acceleration
  - name: "Adobe Photoshop"
    path: vm
    category: "Image Editing"
    exe_patterns: ["*Photoshop*Setup*.exe", "*photoshop*.exe"]
    install_command: null  # User provides their own installer
    notes: "Requires GPU passthrough for acceptable performance."

  - name: "Adobe Premiere Pro"
    path: vm
    category: "Video Editing"
    exe_patterns: ["*Premiere*Setup*.exe"]

  - name: "Adobe After Effects"
    path: vm
    category: "Motion Graphics"
    exe_patterns: ["*After*Effects*Setup*.exe"]

  - name: "Autodesk AutoCAD"
    path: vm
    category: "CAD"
    exe_patterns: ["*AutoCAD*Setup*.exe", "*acad*.exe"]

  - name: "SolidWorks"
    path: vm
    category: "CAD/CAM"
    exe_patterns: ["*SolidWorks*Setup*.exe"]

  # Games — always route through Proton (not the VM)
  - name: "Steam Games"
    path: proton
    category: "Gaming"
    notes: "Managed by Steam + Proton. NeuronOS ensures Steam is available."
    package: "steam"
```

### 6.2 Router Logic (`app_router.py`)

```python
"""
Determines the optimal execution path for a given application.
"""
import fnmatch
import yaml
from pathlib import Path
from enum import Enum
from typing import Optional


class ExecutionPath(Enum):
    NATIVE = "native"
    WINE = "wine"
    PROTON = "proton"
    VM = "vm"
    UNKNOWN = "unknown"


class AppRouter:
    def __init__(self, db_path: str = "/usr/share/neuronos/app_database.yaml"):
        with open(db_path) as f:
            self._db = yaml.safe_load(f)
        self._apps = self._db.get("applications", [])

    def route_executable(self, exe_path: str) -> tuple[ExecutionPath, Optional[dict]]:
        """
        Given a path to a downloaded .exe or .msi, determine how to run it.
        Returns (path, app_entry) or (UNKNOWN, None).
        """
        filename = Path(exe_path).name

        for app in self._apps:
            patterns = app.get("exe_patterns", [])
            for pattern in patterns:
                if fnmatch.fnmatch(filename, pattern):
                    return ExecutionPath(app["path"]), app

        # No match in database — default heuristic
        # Check if Wine can handle it (try Wine first, fall back to VM)
        return ExecutionPath.WINE, None  # Default: try Wine

    def search(self, query: str) -> list[dict]:
        """Search the database by name, category, or alias."""
        query_lower = query.lower()
        results = []
        for app in self._apps:
            if (query_lower in app["name"].lower()
                    or query_lower in app.get("category", "").lower()
                    or any(query_lower in a.lower()
                           for a in app.get("aliases", []))):
                results.append(app)
        return results
```

---

## Part 7: What to Build First — Priority Execution Order

Here's your concrete sprint plan for the first 8 weeks:

**Weeks 1–2: Proof of Concept (manual)**
- Set up dual-GPU Arch system
- Manually configure VFIO, VM, Looking Glass, Scream
- Document every command and config file
- Benchmark VM vs bare metal
- Test single-GPU switching on a second machine

**Weeks 3–5: `neuronos-hardware` + `neuronos-single-gpu`**
- Implement `detect.py` and `vfio_config.py`
- Build test suite using captured `lspci` output from multiple real machines
- Implement single-GPU switching scripts
- Implement libvirt hooks
- Build failsafe recovery service
- Test on at least 3 different hardware configs

**Weeks 5–8: `neuronos-iso` + `neuronos-installer`**
- Create the Archiso profile with full package list
- Fork Calamares, add `neuronhwdetect` and `neuronvfio` modules
- Add NeuronOS branding to Calamares
- Set up CI to auto-build ISOs
- Test: boot ISO → install → reboot → verify VFIO is configured automatically

**Weeks 9–14: `neuronos-vm-manager`**
- Build VM lifecycle manager
- Build Looking Glass wrapper
- Build VM template (minimal Windows 11 with drivers pre-installed)
- Build Scream audio pipeline
- Integrate everything: click button → VM boots → Looking Glass displays → audio works

**Weeks 15–20: Application routing + seamless UX**
- Build the download monitor (inotify)
- Build the application router with database
- Build desktop entry generator
- Build NeuronStore frontend
- Test: download Photoshop installer → prompted to install → installs in VM → desktop shortcut appears → clicking shortcut launches seamlessly

---

## Part 8: Key Technical Gotchas

Things that will bite you and how to handle them:

**NVIDIA Code 43:** NVIDIA drivers detect they're in a VM and refuse to work. The fix is in the domain XML: `<kvm><hidden state='on'/>` plus a fake `<vendor_id>`. This is already in the PoC XML above.

**IOMMU group pollution:** If the GPU shares an IOMMU group with other devices (common on consumer motherboards), you need the ACS override patch. This is a kernel patch — CachyOS and some other kernels include it. Consider shipping a kernel with this patch, or documenting which motherboards need it.

**Looking Glass shared memory permissions:** The `/dev/shm/looking-glass` file must be owned by the user running the VM and readable by the user running the Looking Glass client. Use `tmpfiles.d` to create it with correct permissions at boot.

**Audio latency with Scream:** The default Scream configuration adds ~10ms of latency. For most users this is fine. For music production it's not. Document this limitation.

**BTRFS + QEMU:** QCOW2 images on BTRFS should have copy-on-write disabled (`chattr +C`) or they'll fragment badly and performance will degrade. Set this in the VM setup.

```bash
mkdir -p /var/lib/libvirt/images
chattr +C /var/lib/libvirt/images
```

**Memory ballooning vs. static allocation:** Start with static RAM allocation (simpler, more predictable). Dynamic memory with `virtio-balloon` is an optimization for later.

**Wayland vs. X11:** KDE Plasma 6 defaults to Wayland. Looking Glass works on Wayland via EGL, but some input capture features work better on X11. Test both. You may need to default to X11 initially and switch to Wayland when Looking Glass Wayland support matures.

---

## Part 9: Repository Setup Checklist

```bash
# Create the GitHub org
# github.com/neuronos/

# Initialize all repos
for repo in neuronos-iso neuronos-vm-manager neuronos-hardware \
            neuronos-installer neuronos-single-gpu neuronos-docs; do
    mkdir "$repo"
    cd "$repo"
    git init
    echo "# $repo" > README.md
    git add . && git commit -m "Initial commit"
    cd ..
done

# Set up the ISO build CI (GitHub Actions example)
# .github/workflows/build-iso.yml in neuronos-iso
```

Your CI pipeline for ISO builds:

```yaml
name: Build NeuronOS ISO
on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    container:
      image: archlinux:latest
    steps:
      - uses: actions/checkout@v4
      - name: Install archiso
        run: pacman -Syu --noconfirm archiso
      - name: Build ISO
        run: mkarchiso -v -w /tmp/work -o /tmp/out .
      - name: Upload ISO
        uses: actions/upload-artifact@v4
        with:
          name: neuronos-iso
          path: /tmp/out/*.iso
```

---

This guide gives you the technical foundation to go from "I've read the spec" to "I have a bootable ISO with automatic GPU passthrough." The spec's Milestones 1 and 2 are fully covered here with implementation-ready code and architecture. Milestones 3+ build on this foundation with the application routing and UX layers.

Start with the PoC. If the GPU passthrough works on your hardware, everything else is execution.
