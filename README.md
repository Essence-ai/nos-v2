# NeuronOS

**The desktop operating system that runs all your applications.**

NeuronOS is a Linux-based desktop OS designed to seamlessly run Windows applications alongside native Linux software through GPU passthrough virtualization.

## Repository Structure

This is a **self-contained** repository with all dependencies included:

```
NeuronOS/
├── upstream-archiso/        # Archiso (for building ISOs)
├── upstream-calamares/      # Calamares installer (with NeuronOS modules)
├── upstream-looking-glass/  # Looking Glass (VM display)
├── upstream-scream/         # Scream (VM audio)
│
├── neuronos-iso/            # NeuronOS ISO configuration
├── neuronos-hardware/       # Hardware detection (Python)
├── neuronos-vm-manager/     # VM management (Python)
├── neuronos-installer/      # Calamares modules & branding
├── neuronos-single-gpu/     # GPU switching scripts
├── neuronos-docs/           # Documentation
│
├── setup.sh                 # Main setup/build script
├── Makefile                 # Development shortcuts
└── requirements.txt         # Python dependencies
```

## Quick Start

### Prerequisites

- Fresh Arch Linux installation (VM or bare metal)
- At least 8 GB RAM, 50 GB disk space
- Internet connection

### Build Instructions

```bash
# 1. Clone this repository
git clone https://github.com/YOUR_USERNAME/NeuronOS.git
cd NeuronOS

# 2. Make setup script executable
chmod +x setup.sh

# 3. Run full setup (installs deps, builds everything)
./setup.sh --full

# 4. Build the ISO
sudo ./setup.sh --iso
```

The ISO will be created in `build/iso-output/`.

### Interactive Setup

Run `./setup.sh` without arguments for an interactive menu:

```
1) Full setup (everything)
2) Install dependencies only
3) Build Looking Glass
4) Build Scream
5) Build Calamares
6) Install NeuronOS Python packages
7) Install single-GPU scripts
8) Setup Archiso profile
9) Build ISO
10) Enable services
0) Exit
```

## Upstream Projects

| Project | Location | Purpose |
|---------|----------|---------|
| [Archiso](https://gitlab.archlinux.org/archlinux/archiso) | `upstream-archiso/` | ISO build framework |
| [Calamares](https://github.com/calamares/calamares) | `upstream-calamares/` | Graphical installer |
| [Looking Glass](https://github.com/gnif/LookingGlass) | `upstream-looking-glass/` | Low-latency VM display |
| [Scream](https://github.com/duncanthrax/scream) | `upstream-scream/` | VM audio driver |

NeuronOS modules are already integrated into `upstream-calamares/src/modules/`:
- `neuronhwdetect` - Hardware detection
- `neuronvfio` - VFIO configuration
- `neuronbtrfs` - Snapper setup
- `neuronvmsetup` - VM template wizard

## Development

### Python Packages

```bash
# Install in development mode
pip install -e neuronos-hardware[dev]
pip install -e neuronos-vm-manager[dev,gui]

# Run tests
pytest neuronos-hardware/
pytest neuronos-vm-manager/
```

### Hardware Detection CLI

```bash
# Detect hardware
neuron-hwdetect detect

# Show as JSON
neuron-hwdetect detect --json

# Generate GRUB parameters
neuron-hwdetect grub-params
```

### VM Manager CLI

```bash
# Check VM status
neuronvm status

# Start/stop VM
neuronvm start
neuronvm stop

# Route an application
neuronvm route "Photoshop_Setup.exe"
```

## System Requirements

### Minimum

- **CPU**: Intel 10th gen+ or AMD Ryzen 3000+ with IOMMU
- **RAM**: 16 GB
- **GPU**: Discrete GPU for passthrough
- **Storage**: 100 GB SSD

### Recommended (Dual-GPU Setup)

- Integrated GPU (Intel UHD, AMD APU) for Linux display
- Discrete GPU (NVIDIA RTX, AMD RX) for VM passthrough
- 32 GB RAM
- NVMe SSD

## Documentation

- [Installation Guide](neuronos-docs/user-guide/installation.md)
- [Architecture Overview](neuronos-docs/developer-guide/architecture.md)
- [Technical Implementation Guide](NeuronOS_Technical_Guide.md)

## License

MIT License - see [LICENSE](LICENSE)

## Acknowledgments

NeuronOS builds on these excellent open-source projects:
- [Arch Linux](https://archlinux.org/)
- [KDE Plasma](https://kde.org/)
- [QEMU/KVM](https://www.qemu.org/)
- [Looking Glass](https://looking-glass.io/)
- [Calamares](https://calamares.io/)
