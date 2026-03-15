# NeuronOS Hardware Detection System

This repository contains the hardware detection system and VFIO configuration generator for NeuronOS.

## Overview

The hardware detection system:
- Detects all GPUs in the system
- Classifies GPUs as integrated or discrete
- Determines the optimal passthrough configuration
- Generates VFIO configuration files automatically

## Installation

```bash
pip install -e .
```

## Usage

### Command Line

```bash
# Detect hardware and show configuration
neuron-hwdetect detect

# Output as JSON
neuron-hwdetect detect --json

# Write configuration files (requires root)
sudo neuron-hwdetect configure

# Dry run to see what would be written
neuron-hwdetect configure --dry-run

# Output GRUB kernel parameters only
neuron-hwdetect grub-params
```

### Python API

```python
from neuron_hw import build_hardware_profile, write_configs

# Detect hardware
profile = build_hardware_profile()

print(f"Capability: {profile.capability.value}")
print(f"Passthrough GPU: {profile.passthrough_gpu.name}")

# Write configuration
write_configs(profile, target_root="/")
```

## Calamares Integration

The `calamares_module/` directory contains a Calamares installer module.
Copy it to your Calamares modules directory:

```bash
cp -r calamares_module/ /usr/lib/calamares/modules/neuronhwdetect/
```

Add to your Calamares `settings.conf`:

```yaml
sequence:
  - exec:
    - neuronhwdetect
```

## Configuration Files Generated

- `/etc/default/grub` - IOMMU kernel parameters
- `/etc/modprobe.d/vfio.conf` - VFIO device bindings
- `/etc/mkinitcpio.conf.d/vfio.conf` - Initramfs modules
- `/etc/neuronos/hardware-profile.json` - Hardware profile for other components

## Testing

```bash
pip install -e ".[dev]"
pytest
```

## Hardware Compatibility

See `data/hardware_db.yaml` for the list of verified GPUs and known quirks.
