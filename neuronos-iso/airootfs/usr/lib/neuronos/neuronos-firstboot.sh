#!/bin/bash
# ============================================================
# NeuronOS First Boot Setup
#
# Runs once after installation to:
# 1. Set up the VM domain from the hardware profile
# 2. Create the disk image
# 3. Configure shared memory
# 4. Enable required services
# ============================================================

set -e

SCRIPT_DIR="$(dirname "$0")"
LOG_TAG="neuronos-firstboot"

log() {
    echo "$1"
    logger -t "$LOG_TAG" "$1"
}

log "=== NeuronOS First Boot Setup Starting ==="

# Ensure libvirtd is running
if ! systemctl is-active --quiet libvirtd; then
    log "Starting libvirtd..."
    systemctl start libvirtd
fi

# Ensure the default network is available
virsh net-info default &>/dev/null || virsh net-start default &>/dev/null || true
virsh net-autostart default &>/dev/null || true

# Run the VM setup script (creates domain, disk image, shared memory)
if [ -f /usr/lib/neuronos/vm-setup.py ]; then
    log "Running VM setup..."
    python3 /usr/lib/neuronos/vm-setup.py
else
    log "WARNING: vm-setup.py not found, skipping VM configuration"
fi

# Create tmpfiles for shared memory persistence
cat > /etc/tmpfiles.d/neuronos-shm.conf << 'EOF'
f /dev/shm/looking-glass 0660 root kvm -
f /dev/shm/scream-ivshmem 0660 root kvm -
EOF
systemd-tmpfiles --create /etc/tmpfiles.d/neuronos-shm.conf

# Enable the scream receiver for all users
mkdir -p /etc/skel/.config/systemd/user/default.target.wants
ln -sf /etc/systemd/user/scream-receiver.service \
    /etc/skel/.config/systemd/user/default.target.wants/scream-receiver.service 2>/dev/null || true

# Enable scream for existing users
for home_dir in /home/*/; do
    user=$(basename "$home_dir")
    mkdir -p "$home_dir/.config/systemd/user/default.target.wants"
    ln -sf /etc/systemd/user/scream-receiver.service \
        "$home_dir/.config/systemd/user/default.target.wants/scream-receiver.service" 2>/dev/null || true
    chown -R "$user:$user" "$home_dir/.config/systemd" 2>/dev/null || true
done

log "=== NeuronOS First Boot Setup Complete ==="
