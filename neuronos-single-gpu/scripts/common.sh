#!/bin/bash
# NeuronOS Single-GPU Common Functions

set -euo pipefail

# Load hardware profile
PROFILE="/etc/neuronos/hardware-profile.json"

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo "ERROR: jq is required but not installed" >&2
    exit 1
fi

# Load GPU configuration
load_gpu_config() {
    if [[ ! -f "$PROFILE" ]]; then
        echo "ERROR: Hardware profile not found at $PROFILE" >&2
        exit 1
    fi

    GPU_PCI=$(jq -r '.passthrough_gpu.pci_address // empty' "$PROFILE")
    GPU_VENDOR=$(jq -r '.passthrough_gpu.vendor // empty' "$PROFILE")
    CAPABILITY=$(jq -r '.capability // empty' "$PROFILE")

    if [[ -z "$GPU_PCI" ]]; then
        echo "ERROR: No passthrough GPU configured" >&2
        exit 1
    fi

    # Extract the audio PCI address (same slot, function 1)
    AUDIO_PCI="${GPU_PCI%.*}.1"

    # Determine modules to unload based on vendor
    case "$GPU_VENDOR" in
        nvidia)
            MODULES_TO_UNLOAD="nvidia_drm nvidia_modeset nvidia_uvm nvidia"
            MODULES_TO_LOAD="nvidia_drm"
            MODESET_PARAM="modeset=1"
            ;;
        amd)
            MODULES_TO_UNLOAD="amdgpu"
            MODULES_TO_LOAD="amdgpu"
            MODESET_PARAM=""
            ;;
        intel)
            MODULES_TO_UNLOAD="i915"
            MODULES_TO_LOAD="i915"
            MODESET_PARAM=""
            ;;
        *)
            echo "ERROR: Unknown GPU vendor: $GPU_VENDOR" >&2
            exit 1
            ;;
    esac

    export GPU_PCI AUDIO_PCI GPU_VENDOR CAPABILITY
    export MODULES_TO_UNLOAD MODULES_TO_LOAD MODESET_PARAM
}

# Check if we're in single-GPU mode
check_single_gpu_mode() {
    load_gpu_config
    if [[ "$CAPABILITY" != "single_gpu" ]]; then
        echo "INFO: Not in single-GPU mode, skipping" >&2
        exit 0
    fi
}

# Send desktop notification
notify_user() {
    local title="$1"
    local message="$2"
    local urgency="${3:-normal}"

    # Try to find the active user session
    local user_session
    user_session=$(loginctl list-sessions --no-legend | awk '{print $1}' | head -1)

    if [[ -n "$user_session" ]]; then
        local uid
        uid=$(loginctl show-session "$user_session" -p User --value)
        local user
        user=$(id -un "$uid" 2>/dev/null || echo "")

        if [[ -n "$user" ]]; then
            sudo -u "$user" DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$uid/bus" \
                notify-send --urgency="$urgency" --expire-time=5000 "$title" "$message" 2>/dev/null || true
        fi
    fi
}

# Log to systemd journal
log_info() {
    echo "INFO: $*"
    logger -t neuronos-gpu "$*"
}

log_warning() {
    echo "WARNING: $*" >&2
    logger -t neuronos-gpu -p warning "$*"
}

log_error() {
    echo "ERROR: $*" >&2
    logger -t neuronos-gpu -p err "$*"
}
