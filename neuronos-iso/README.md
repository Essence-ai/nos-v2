# NeuronOS ISO

This repository contains the Archiso configuration for building NeuronOS installation images.

## Building the ISO

### Prerequisites

- Arch Linux or Arch-based distribution
- `archiso` package installed

```bash
sudo pacman -S archiso
```

### Build Process

```bash
cd neuronos-iso
sudo mkarchiso -v -w /tmp/archiso-tmp -o ~/neuronos-out .
```

This will produce a bootable `.iso` file in `~/neuronos-out/`.

## Directory Structure

```
neuronos-iso/
├── airootfs/           # Files overlaid onto the live filesystem
│   ├── etc/            # System config files
│   ├── usr/            # Custom scripts, .desktop files
│   └── root/           # Auto-run scripts for live environment
├── packages.x86_64     # Package list
├── pacman.conf         # Pacman configuration
├── profiledef.sh       # ISO metadata
└── efiboot/            # EFI boot configuration
```

## Testing

1. Test in a VM first (without GPU passthrough)
2. Verify it boots to SDDM + KDE Plasma
3. Test on physical hardware with GPU passthrough capability

## CI/CD

ISO builds are automated via GitHub Actions. See `.github/workflows/build-iso.yml`.
