# NeuronOS Single-GPU Switching

This repository contains the scripts and services for single-GPU passthrough on systems without a secondary display GPU.

## Overview

On systems with only one GPU, launching a VM with GPU passthrough requires:
1. Stopping the display manager
2. Unbinding the GPU from the Linux driver
3. Binding the GPU to VFIO
4. Starting the VM
5. (When VM stops) Reversing the process

This causes a brief screen blackout (~5-10 seconds) during transitions.

## Scripts

### gpu-switch-to-vm.sh

Prepares the GPU for VM passthrough:
- Notifies the user of impending screen blackout
- Stops the display manager
- Unbinds VT consoles and framebuffer
- Unloads GPU driver modules
- Loads VFIO modules
- Binds GPU to vfio-pci

### gpu-switch-to-host.sh

Returns the GPU to the Linux host:
- Unbinds GPU from vfio-pci
- Rescans PCI bus
- Loads GPU driver modules
- Rebinds VT consoles
- Restarts display manager
- Notifies user of completion

### gpu-recovery-check.sh

Recovery script for failed transitions:
- Runs at boot
- Checks if display manager failed to start
- Detects if GPU is stuck in VFIO mode
- Automatically recovers to working state

## libvirt Hook

The `hooks/qemu` script integrates with libvirt:
- Called automatically before VM starts (`prepare/begin`)
- Called automatically after VM stops (`release/end`)
- Only triggers for the NeuronOS Windows VM
- Only active in single-GPU mode

## Installation

```bash
# Copy scripts to system location
sudo cp scripts/*.sh /usr/lib/neuronos/
sudo chmod +x /usr/lib/neuronos/*.sh

# Install libvirt hook
sudo cp hooks/qemu /etc/libvirt/hooks/qemu
sudo chmod +x /etc/libvirt/hooks/qemu
sudo systemctl restart libvirtd

# Install recovery service
sudo cp systemd/neuron-gpu-recovery.service /etc/systemd/system/
sudo systemctl enable neuron-gpu-recovery.service
```

## Troubleshooting

### Black Screen After VM Exit

If the screen stays black after the VM shuts down:

1. Wait 30 seconds for automatic recovery
2. If no recovery, press Ctrl+Alt+F2 for TTY
3. Login and run: `sudo /usr/lib/neuronos/gpu-switch-to-host.sh`

### VM Won't Start

Check the libvirt logs:
```bash
journalctl -u libvirtd -f
```

Check the GPU switching logs:
```bash
journalctl -t neuronos-gpu
journalctl -t neuronos-libvirt-hook
```

### GPU Won't Unbind

The GPU driver might have processes using it:
```bash
# List processes using the GPU
lsof /dev/dri/*
lsof /dev/nvidia*

# Kill remaining processes
fuser -k /dev/dri/*
```

## Safety Features

- User notification before screen blackout
- Automatic recovery service on boot
- Logging to systemd journal
- Verification of GPU binding state
- Fallback error handling

## Hardware Support

Tested GPU vendors:
- NVIDIA (GeForce GTX/RTX series)
- AMD (Radeon RX series)
- Intel (Arc series)

Required system capabilities:
- IOMMU support (VT-d or AMD-Vi)
- Single GPU in isolated IOMMU group
