# NeuronOS Architecture

## Overview

NeuronOS is built on a modular architecture with six core repositories:

```
┌─────────────────────────────────────────────────────────────────┐
│                         NeuronOS                                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ neuronos-   │  │ neuronos-   │  │   neuronos-vm-manager   │  │
│  │    iso      │  │  installer  │  │   (Core Application)    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ neuronos-   │  │ neuronos-   │  │     neuronos-docs       │  │
│  │  hardware   │  │  single-gpu │  │    (Documentation)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                    Arch Linux + KDE Plasma                       │
├─────────────────────────────────────────────────────────────────┤
│          QEMU/KVM + libvirt + VFIO + Looking Glass              │
└─────────────────────────────────────────────────────────────────┘
```

## Repository Responsibilities

### neuronos-iso

**Purpose**: Build system for NeuronOS installation images.

**Contents**:
- Archiso profile configuration
- Package list
- System configuration overlays
- CI/CD for ISO builds

### neuronos-hardware

**Purpose**: Hardware detection and VFIO configuration.

**Contents**:
- GPU detection (`detect.py`)
- VFIO configuration generation (`vfio_config.py`)
- Hardware compatibility database
- Calamares integration module

**Key Classes**:
- `HardwareProfile`: Complete system hardware profile
- `GPU`: GPU device with vendor, type, PCI address
- `PassthroughCapability`: DUAL_GPU, SINGLE_GPU, NO_PASSTHROUGH

### neuronos-vm-manager

**Purpose**: Core VM management application.

**Contents**:
- VM lifecycle management
- Looking Glass integration
- Application routing
- Download monitoring
- Desktop entry generation

**Key Classes**:
- `VMLifecycleManager`: Start/stop/pause VM
- `LookingGlassWrapper`: Borderless VM display
- `AppRouter`: Route apps to native/Wine/VM
- `DownloadMonitor`: Watch for new executables

### neuronos-installer

**Purpose**: Custom Calamares installer.

**Contents**:
- Calamares settings and branding
- Custom installer modules
- Installation slideshow

### neuronos-single-gpu

**Purpose**: GPU switching for single-GPU systems.

**Contents**:
- GPU unbind/rebind scripts
- libvirt hooks
- Recovery service

### neuronos-docs

**Purpose**: All documentation.

**Contents**:
- User guides
- Developer documentation
- Hardware compatibility lists
- Troubleshooting guides

## Data Flow

### Installation Flow

```
ISO Boot → Calamares → Hardware Detection → VFIO Config
    ↓
Partition → Install Packages → Configure Boot → First Boot
    ↓
Onboarding → VM Template Download (optional) → Ready
```

### Application Launch Flow

```
User clicks app icon
    ↓
AppRouter.route_executable()
    ↓
┌─────────────────┬──────────────────┬──────────────────┐
│     NATIVE      │       WINE       │        VM        │
├─────────────────┼──────────────────┼──────────────────┤
│ Launch directly │ Launch via Wine  │ Start VM if      │
│                 │                  │ not running      │
│                 │                  │     ↓            │
│                 │                  │ Launch Looking   │
│                 │                  │ Glass            │
│                 │                  │     ↓            │
│                 │                  │ Launch app in VM │
└─────────────────┴──────────────────┴──────────────────┘
```

### Single-GPU Switch Flow

```
VM Start Request
    ↓
libvirt hook: prepare/begin
    ↓
gpu-switch-to-vm.sh
    ↓
1. Notify user
2. Stop display manager
3. Unbind VT consoles
4. Unload GPU drivers
5. Load VFIO
6. Bind GPU to vfio-pci
    ↓
VM runs with GPU
    ↓
VM Shutdown
    ↓
libvirt hook: release/end
    ↓
gpu-switch-to-host.sh
    ↓
1. Unbind from VFIO
2. Load GPU drivers
3. Bind VT consoles
4. Start display manager
5. Notify user
```

## Configuration Files

### System Configuration

| File | Purpose |
|------|---------|
| `/etc/neuronos/hardware-profile.json` | Detected hardware configuration |
| `/etc/modprobe.d/vfio.conf` | VFIO device bindings |
| `/etc/mkinitcpio.conf.d/vfio.conf` | Initramfs VFIO modules |
| `/etc/default/grub` | IOMMU kernel parameters |

### User Configuration

| File | Purpose |
|------|---------|
| `~/.config/neuronos/config.json` | VM Manager settings |
| `~/.local/share/neuronos/` | Application data |
| `~/.local/share/applications/neuronos-*.desktop` | VM app launchers |

## Key Technologies

### Virtualization Stack

- **QEMU**: Machine emulator
- **KVM**: Hardware virtualization
- **libvirt**: VM management API
- **OVMF**: UEFI firmware

### GPU Passthrough

- **VFIO**: Device isolation framework
- **IOMMU**: Memory isolation (VT-d/AMD-Vi)
- **Looking Glass**: Low-latency VM display

### Desktop

- **KDE Plasma 6**: Desktop environment
- **PySide6/Qt6**: Application framework
- **systemd**: Service management

## Development Workflow

1. **Hardware Changes**: Update `neuronos-hardware`
2. **VM Features**: Update `neuronos-vm-manager`
3. **Install Changes**: Update `neuronos-installer`
4. **GPU Switching**: Update `neuronos-single-gpu`
5. **Build ISO**: Rebuild `neuronos-iso`
6. **Document**: Update `neuronos-docs`
