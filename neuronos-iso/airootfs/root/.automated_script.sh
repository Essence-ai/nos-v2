#!/usr/bin/env bash
# NeuronOS Live Environment Initialization Script

# This script runs automatically when the live environment boots

set -e

# Enable NetworkManager
systemctl enable --now NetworkManager

# Enable libvirtd
systemctl enable --now libvirtd

# Enable SDDM display manager
systemctl enable sddm

# Create the shared memory files for Looking Glass and Scream
touch /dev/shm/looking-glass
chmod 0660 /dev/shm/looking-glass
chown root:kvm /dev/shm/looking-glass

touch /dev/shm/scream-ivshmem
chmod 0660 /dev/shm/scream-ivshmem
chown root:kvm /dev/shm/scream-ivshmem

echo "NeuronOS Live Environment Initialized"
