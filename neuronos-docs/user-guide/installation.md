# NeuronOS Installation Guide

## System Requirements

### Minimum Requirements

- **CPU**: 64-bit processor with IOMMU support
  - Intel: 10th gen or newer with VT-d
  - AMD: Ryzen 3000 series or newer with AMD-Vi
- **RAM**: 16 GB (8 GB for host + 8 GB for VM)
- **Storage**: 100 GB free space (SSD recommended)
- **GPU**: Discrete GPU for VM passthrough

### Recommended Configuration

- **CPU**: Modern multi-core processor (8+ cores)
- **RAM**: 32 GB or more
- **Storage**: 250 GB NVMe SSD
- **GPUs**: Integrated GPU + Discrete GPU (dual-GPU setup)

## Pre-Installation Checklist

### 1. BIOS/UEFI Settings

Enable these settings before installing:

- **IOMMU/VT-d** (Intel) or **AMD-Vi/SVM** (AMD)
- **Virtualization Extensions** (VT-x or AMD-V)
- **Above 4G Decoding** (for GPU passthrough)

### 2. Dual-GPU vs Single-GPU

**Dual-GPU (Recommended)**:
- Integrated GPU (Intel UHD, AMD APU) runs your desktop
- Discrete GPU (NVIDIA RTX, AMD RX) goes to Windows VM
- Seamless experience with no screen interruption

**Single-GPU**:
- Screen goes black when launching Windows apps (~5 seconds)
- Desktop returns when Windows app closes
- Works but less convenient

### 3. Backup Your Data

NeuronOS installation will erase the target drive. Back up important data first.

## Creating Installation Media

### Download

1. Download the latest NeuronOS ISO from the official website
2. Verify the checksum:
   ```bash
   sha256sum neuronos-2026.03.iso
   ```

### Create Bootable USB

**Linux**:
```bash
sudo dd if=neuronos-2026.03.iso of=/dev/sdX bs=4M status=progress
sync
```

**Windows**:
Use Rufus or balenaEtcher to write the ISO to USB.

## Installation Steps

### 1. Boot from USB

- Insert USB drive and restart computer
- Enter boot menu (usually F12, F2, or Del)
- Select the USB drive

### 2. Welcome Screen

- Select your language
- Click "Install NeuronOS"

### 3. Locale Settings

- Choose your timezone
- Select your keyboard layout

### 4. Disk Partitioning

**Automatic (Recommended)**:
- Select target disk
- Choose "Erase disk and install NeuronOS"
- BTRFS filesystem will be configured automatically

**Manual**:
- Create partitions manually if needed
- Recommended layout:
  - EFI: 512 MB (FAT32)
  - Root: Remaining space (BTRFS)

### 5. User Account

- Enter your username
- Create a strong password
- Set hostname

### 6. Summary

- Review installation settings
- Click "Install" to begin

### 7. Wait for Installation

Installation takes approximately 10-15 minutes. The slideshow will show NeuronOS features.

### 8. Reboot

Remove USB drive and restart when prompted.

## First Boot

### Onboarding Wizard

After first boot, the onboarding wizard will:

1. Welcome you to NeuronOS
2. Detect your hardware configuration
3. Ask: "Do you plan to use Windows applications?"
   - If Yes: VM template will download in background (~15-20 GB)
   - If No: Skip VM setup (can enable later)

### Hardware Detection Results

The wizard will show your passthrough capability:

- **Dual-GPU**: Best experience, no interruptions
- **Single-GPU**: Works with brief screen blackout
- **No Passthrough**: Native Linux apps only

## Post-Installation

### System Updates

```bash
sudo pacman -Syu
```

### Installing Applications

- Use the NeuronStore for recommended apps
- Native Linux apps install normally
- Windows apps are routed automatically

### Troubleshooting

See the [Troubleshooting Guide](../troubleshooting/installation-issues.md) for common issues.
