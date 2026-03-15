#!/bin/bash
# gpu-recovery-check.sh
# Runs at boot. If SDDM isn't running and the GPU is bound to vfio-pci,
# something went wrong during the last shutdown. Recover.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh" 2>/dev/null || {
    # If common.sh fails, we're in a broken state
    # Try basic recovery
    PROFILE="/etc/neuronos/hardware-profile.json"
    if [ -f "$PROFILE" ]; then
        GPU_PCI=$(jq -r '.passthrough_gpu.pci_address // empty' "$PROFILE")
    fi
}

# Wait for normal boot to complete
sleep 30

log_info "Running GPU recovery check..."

# Check if display manager is running
if systemctl is-active --quiet sddm || \
   systemctl is-active --quiet gdm || \
   systemctl is-active --quiet lightdm; then
    log_info "Display manager is running, no recovery needed"
    exit 0
fi

# Check if GPU is still bound to VFIO
if [ -n "$GPU_PCI" ] && lspci -ks "$GPU_PCI" 2>/dev/null | grep -q "vfio-pci"; then
    log_warning "GPU recovery triggered - SDDM not running, GPU still on VFIO"

    # Run the recovery
    "$SCRIPT_DIR/gpu-switch-to-host.sh" || {
        log_error "GPU recovery failed!"

        # Last resort: try to at least get a text console
        echo 1 > /sys/class/vtconsole/vtcon0/bind 2>/dev/null || true

        # Try to start a minimal display
        systemctl start sddm || true

        exit 1
    }

    log_info "GPU recovery completed successfully"
else
    log_info "GPU is not bound to VFIO, no recovery needed"
fi
