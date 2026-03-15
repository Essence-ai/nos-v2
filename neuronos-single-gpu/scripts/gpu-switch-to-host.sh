#!/bin/bash
# gpu-switch-to-host.sh
# Rebinds the GPU to the Linux host after the VM shuts down.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

load_gpu_config

log_info "Starting GPU switch back to host"
log_info "GPU: $GPU_PCI ($GPU_VENDOR)"

# 1. Unbind from vfio-pci
log_info "Unbinding GPU from VFIO..."
echo "$GPU_PCI" > /sys/bus/pci/drivers/vfio-pci/unbind 2>/dev/null || true

if lspci -s "$AUDIO_PCI" &>/dev/null; then
    log_info "Unbinding GPU audio from VFIO..."
    echo "$AUDIO_PCI" > /sys/bus/pci/drivers/vfio-pci/unbind 2>/dev/null || true
fi

# 2. Remove VFIO device IDs
log_info "Removing VFIO device bindings..."
GPU_ID=$(lspci -ns "$GPU_PCI" | awk '{print $3}')
echo "$GPU_ID" > /sys/bus/pci/drivers/vfio-pci/remove_id 2>/dev/null || true

if lspci -s "$AUDIO_PCI" &>/dev/null; then
    AUDIO_ID=$(lspci -ns "$AUDIO_PCI" | awk '{print $3}')
    echo "$AUDIO_ID" > /sys/bus/pci/drivers/vfio-pci/remove_id 2>/dev/null || true
fi

# 3. Rescan PCI bus to re-detect devices
log_info "Rescanning PCI bus..."
echo 1 > /sys/bus/pci/rescan 2>/dev/null || true
sleep 1

# 4. Reload GPU driver
log_info "Loading GPU driver modules..."
for mod in $MODULES_TO_LOAD; do
    if [[ -n "$MODESET_PARAM" ]]; then
        modprobe "$mod" "$MODESET_PARAM" || {
            log_warning "Failed to load $mod with modeset, trying without..."
            modprobe "$mod" || log_error "Failed to load $mod"
        }
    else
        modprobe "$mod" || log_error "Failed to load $mod"
    fi
done

# 5. Rebind VT console
log_info "Rebinding VT consoles..."
echo 1 > /sys/class/vtconsole/vtcon0/bind 2>/dev/null || true
echo 1 > /sys/class/vtconsole/vtcon1/bind 2>/dev/null || true

# 6. Wait for GPU driver to initialize
sleep 2

# 7. Restart display manager
log_info "Restarting display manager..."
systemctl start sddm || systemctl start gdm || systemctl start lightdm || {
    log_error "Failed to start display manager"
    exit 1
}

# Wait for display manager to fully start
sleep 3

# Notify user
notify_user "NeuronOS" \
    "Windows application has closed. Your graphics card has returned to your desktop."

log_info "GPU switch to host complete. Desktop restored."
