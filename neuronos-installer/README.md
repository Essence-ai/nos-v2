# NeuronOS Installer

Custom Calamares-based installer for NeuronOS with integrated GPU passthrough configuration.

## Overview

The NeuronOS installer extends Calamares with custom modules:

- **neuronhwdetect**: Detects GPUs and determines passthrough capability
- **neuronvfio**: Writes VFIO configuration files
- **neuronbtrfs**: Configures snapper for system snapshots
- **neuronvmsetup**: Prompts for Windows application support

## Installation

The installer is integrated into the NeuronOS ISO. To build:

1. Clone this repository
2. Build Calamares with the NeuronOS modules
3. Include in the Archiso configuration

## Module Structure

```
neuronos-installer/
├── settings.conf           # Calamares settings
├── branding/
│   └── neuronos/
│       ├── branding.desc   # Branding configuration
│       └── show.qml        # Installation slideshow
└── modules/
    ├── neuronhwdetect/     # (from neuronos-hardware)
    ├── neuronvfio/
    ├── neuronbtrfs/
    └── neuronvmsetup/
```

## Custom Modules

### neuronhwdetect

Runs hardware detection from `neuronos-hardware` package.

- Detects all GPUs
- Determines passthrough capability
- Stores results in Calamares global storage

### neuronvfio

Writes VFIO configuration based on detected hardware.

- Writes `/etc/modprobe.d/vfio.conf`
- Updates GRUB kernel parameters
- Rebuilds initramfs

### neuronbtrfs

Configures BTRFS snapshots for system rollback.

- Creates snapper configuration
- Enables timeline snapshots
- Integrates with grub-btrfs

### neuronvmsetup

Handles VM template setup.

- Asks user if they need Windows apps
- Queues VM template download for first boot
- Enables first-boot service

## Branding

The NeuronOS branding includes:

- Custom slideshow during installation
- NeuronOS logo and colors
- Progress indicators

## Development

To test modules:

```bash
# Run Calamares in debug mode
calamares -d

# Test individual modules
python -m modules.neuronvfio.main
```

## Dependencies

- Calamares 3.3+
- Python 3.10+
- libcalamares Python bindings
