#!/bin/bash
# gpu-switch-to-vm.sh
# Unbinds the GPU from the Linux host and prepares it for VM passthrough.
# THIS WILL CAUSE A SCREEN BLACKOUT.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

check_single_gpu_mode
load_gpu_config

log_info "Starting GPU switch to VM mode"
log_info "GPU: $GPU_PCI ($GPU_VENDOR)"

# Send notification to user before we kill the display
notify_user "NeuronOS" \
    "Starting Windows application. Your screen will go black for ~5 seconds while the graphics card switches." \
    "critical"

# Give user time to read the notification
sleep 3

# --- POINT OF NO RETURN ---
log_info "Stopping display manager..."

# 1. Stop the display manager
systemctl stop sddm || systemctl stop gdm || systemctl stop lightdm || {
    log_error "Failed to stop display manager"
    exit 1
}

# Wait for all Xorg/Wayland sessions to terminate
sleep 2

# 2. Unbind VTconsole (framebuffer) to release the GPU
log_info "Unbinding VT consoles..."
echo 0 > /sys/class/vtconsole/vtcon0/bind 2>/dev/null || true
echo 0 > /sys/class/vtconsole/vtcon1/bind 2>/dev/null || true

# 3. Unbind EFI framebuffer
log_info "Unbinding EFI framebuffer..."
echo "efi-framebuffer.0" > /sys/bus/platform/drivers/efi-framebuffer/unbind 2>/dev/null || true

# 4. Unload GPU driver modules
log_info "Unloading GPU driver modules..."
for mod in $MODULES_TO_UNLOAD; do
    if lsmod | grep -q "^$mod "; then
        log_info "Unloading $mod..."
        modprobe -r "$mod" || {
            log_warning "Failed to unload $mod, retrying..."
            sleep 1
            modprobe -r "$mod" || log_error "Could not unload $mod"
        }
    fi
done

# 5. Load VFIO modules
log_info "Loading VFIO modules..."
modprobe vfio-pci

# 6. Bind the GPU to vfio-pci
log_info "Binding GPU to VFIO..."
GPU_ID=$(lspci -ns "$GPU_PCI" | awk '{print $3}')
echo "$GPU_ID" > /sys/bus/pci/drivers/vfio-pci/new_id 2>/dev/null || true

# Also bind the audio function if present
if lspci -s "$AUDIO_PCI" &>/dev/null; then
    log_info "Binding GPU audio to VFIO..."
    AUDIO_ID=$(lspci -ns "$AUDIO_PCI" | awk '{print $3}')
    echo "$AUDIO_ID" > /sys/bus/pci/drivers/vfio-pci/new_id 2>/dev/null || true
fi

# Verify binding
if lspci -ks "$GPU_PCI" | grep -q "vfio-pci"; then
    log_info "GPU successfully bound to VFIO"
else
    log_error "GPU binding verification failed"
    # Attempt recovery
    "$SCRIPT_DIR/gpu-switch-to-host.sh"
    exit 1
fi

log_info "GPU switch to VM complete. Ready for VM launch."
