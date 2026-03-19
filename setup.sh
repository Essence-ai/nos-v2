#!/bin/bash
# ============================================================
# NeuronOS Development Setup Script
# Run this on a fresh Arch Linux installation
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
INSTALL_DIR="/usr/local"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================================
# STEP 1: Install System Dependencies
# ============================================================
install_dependencies() {
    log_info "Installing system dependencies..."

    sudo pacman -Syu --noconfirm

    # Base development tools
    sudo pacman -S --noconfirm --needed \
        base-devel \
        git \
        cmake \
        meson \
        ninja \
        pkgconf \
        python \
        python-pip \
        python-yaml \
        python-libvirt

    # Archiso for building ISOs
    sudo pacman -S --noconfirm --needed archiso

    # Calamares dependencies
    sudo pacman -S --noconfirm --needed \
        qt6-base \
        qt6-svg \
        qt6-tools \
        kpmcore \
        yaml-cpp \
        libpwquality \
        icu \
        boost \
        extra-cmake-modules \
        ki18n \
        kconfig \
        kcoreaddons \
        kdbusaddons \
        kwidgetsaddons \
        kcrash \
        polkit-qt6

    # Looking Glass dependencies
    sudo pacman -S --noconfirm --needed \
        cmake \
        gcc \
        libgl \
        libegl \
        fontconfig \
        spice-protocol \
        wayland-protocols \
        libxkbcommon \
        libsamplerate \
        libpulse \
        pipewire

    # Scream dependencies
    sudo pacman -S --noconfirm --needed \
        pulseaudio \
        pipewire-pulse

    # Virtualization
    sudo pacman -S --noconfirm --needed \
        qemu-full \
        libvirt \
        virt-manager \
        edk2-ovmf \
        dnsmasq \
        bridge-utils

    log_success "System dependencies installed"
}

# ============================================================
# STEP 2: Build Looking Glass Client
# ============================================================
build_looking_glass() {
    log_info "Building Looking Glass client..."

    cd "$SCRIPT_DIR/upstream-looking-glass/client"

    mkdir -p build
    cd build

    cmake \
        -DENABLE_WAYLAND=ON \
        -DENABLE_X11=ON \
        -DENABLE_PIPEWIRE=ON \
        -DCMAKE_INSTALL_PREFIX="$INSTALL_DIR" \
        ..

    make -j$(nproc)

    sudo make install

    log_success "Looking Glass client built and installed"
}

# ============================================================
# STEP 3: Build Scream Receiver
# ============================================================
build_scream() {
    log_info "Building Scream receiver..."

    cd "$SCRIPT_DIR/upstream-scream/Receivers/pipewire"

    mkdir -p build
    cd build

    cmake ..
    make -j$(nproc)

    sudo cp scream "$INSTALL_DIR/bin/"

    log_success "Scream receiver built and installed"
}

# ============================================================
# STEP 4: Build Calamares with NeuronOS Modules
# ============================================================
build_calamares() {
    log_info "Building Calamares installer with NeuronOS modules..."

    cd "$SCRIPT_DIR/upstream-calamares"

    mkdir -p build
    cd build

    cmake \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX=/usr \
        -DCMAKE_INSTALL_LIBDIR=lib \
        -DWITH_QT6=ON \
        -DSKIP_MODULES="tracking" \
        ..

    make -j$(nproc)

    sudo make install

    log_success "Calamares built and installed"
}

# ============================================================
# STEP 5: Install NeuronOS Python Packages
# ============================================================
install_neuronos_packages() {
    log_info "Installing NeuronOS Python packages..."

    cd "$SCRIPT_DIR"

    # Install neuronos-hardware
    pip install --user -e neuronos-hardware

    # Install neuronos-vm-manager
    pip install --user -e neuronos-vm-manager

    log_success "NeuronOS Python packages installed"
}

# ============================================================
# STEP 6: Install Single-GPU Scripts
# ============================================================
install_single_gpu_scripts() {
    log_info "Installing single-GPU switching scripts..."

    sudo mkdir -p /usr/lib/neuronos

    sudo cp "$SCRIPT_DIR/neuronos-single-gpu/scripts/"*.sh /usr/lib/neuronos/
    sudo chmod +x /usr/lib/neuronos/*.sh

    # Install libvirt hook
    sudo mkdir -p /etc/libvirt/hooks
    sudo cp "$SCRIPT_DIR/neuronos-single-gpu/hooks/qemu" /etc/libvirt/hooks/qemu
    sudo chmod +x /etc/libvirt/hooks/qemu

    # Install systemd service
    sudo cp "$SCRIPT_DIR/neuronos-single-gpu/systemd/"*.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable neuron-gpu-recovery.service

    log_success "Single-GPU scripts installed"
}

# ============================================================
# STEP 7: Setup Archiso Profile
# ============================================================
setup_archiso_profile() {
    log_info "Setting up Archiso profile for NeuronOS..."

    # Backup our custom files
    cp "$SCRIPT_DIR/neuronos-iso/packages.x86_64" /tmp/neuronos-packages.x86_64.bak
    cp "$SCRIPT_DIR/neuronos-iso/profiledef.sh" /tmp/neuronos-profiledef.sh.bak

    # Copy the releng profile directories we need (syslinux, efiboot, grub, airootfs)
    log_info "Copying boot directories from upstream archiso..."
    cp -r "$SCRIPT_DIR/upstream-archiso/configs/releng/syslinux" "$SCRIPT_DIR/neuronos-iso/"
    cp -r "$SCRIPT_DIR/upstream-archiso/configs/releng/efiboot" "$SCRIPT_DIR/neuronos-iso/"
    cp -r "$SCRIPT_DIR/upstream-archiso/configs/releng/grub" "$SCRIPT_DIR/neuronos-iso/"

    # Copy airootfs base and merge with our customizations
    log_info "Setting up airootfs..."
    cp -r "$SCRIPT_DIR/upstream-archiso/configs/releng/airootfs/"* "$SCRIPT_DIR/neuronos-iso/airootfs/" 2>/dev/null || true

    # Copy bootstrap_packages if it exists
    if [ -f "$SCRIPT_DIR/upstream-archiso/configs/releng/bootstrap_packages" ]; then
        cp "$SCRIPT_DIR/upstream-archiso/configs/releng/bootstrap_packages" "$SCRIPT_DIR/neuronos-iso/"
    fi

    # Restore our custom files
    cp /tmp/neuronos-packages.x86_64.bak "$SCRIPT_DIR/neuronos-iso/packages.x86_64"
    cp /tmp/neuronos-profiledef.sh.bak "$SCRIPT_DIR/neuronos-iso/profiledef.sh"

    # Update syslinux config to say NeuronOS instead of Arch Linux
    if [ -f "$SCRIPT_DIR/neuronos-iso/syslinux/archiso_sys-linux.cfg" ]; then
        sed -i 's/Arch Linux/NeuronOS/g' "$SCRIPT_DIR/neuronos-iso/syslinux/"*.cfg
    fi

    # Update GRUB config to say NeuronOS
    if [ -f "$SCRIPT_DIR/neuronos-iso/grub/grub.cfg" ]; then
        sed -i 's/Arch Linux/NeuronOS/g' "$SCRIPT_DIR/neuronos-iso/grub/grub.cfg"
    fi

    # Create systemd service enable symlinks (can't do this on Windows)
    log_info "Creating systemd service symlinks..."
    mkdir -p "$SCRIPT_DIR/neuronos-iso/airootfs/etc/systemd/system/multi-user.target.wants"
    ln -sf /etc/systemd/system/neuronos-live-setup.service \
        "$SCRIPT_DIR/neuronos-iso/airootfs/etc/systemd/system/multi-user.target.wants/neuronos-live-setup.service" 2>/dev/null || true
    ln -sf /usr/lib/systemd/system/NetworkManager.service \
        "$SCRIPT_DIR/neuronos-iso/airootfs/etc/systemd/system/multi-user.target.wants/NetworkManager.service" 2>/dev/null || true

    # Make the setup script executable
    chmod +x "$SCRIPT_DIR/neuronos-iso/airootfs/usr/local/bin/neuronos-live-setup" 2>/dev/null || true

    # Remove .gitkeep files
    find "$SCRIPT_DIR/neuronos-iso/airootfs" -name ".gitkeep" -delete 2>/dev/null || true

    log_success "Archiso profile setup complete"
}

# ============================================================
# STEP 8: Copy Built Components to ISO
# ============================================================
copy_components_to_iso() {
    log_info "Copying NeuronOS components to ISO..."

    local AIROOTFS="$SCRIPT_DIR/neuronos-iso/airootfs"

    # Copy Looking Glass if built
    if [ -f "$SCRIPT_DIR/upstream-looking-glass/client/build/looking-glass-client" ]; then
        log_info "Copying Looking Glass client..."
        mkdir -p "$AIROOTFS/usr/bin"
        cp "$SCRIPT_DIR/upstream-looking-glass/client/build/looking-glass-client" "$AIROOTFS/usr/bin/"
        chmod +x "$AIROOTFS/usr/bin/looking-glass-client"
    else
        log_warning "Looking Glass not built yet. Run option 3 first."
    fi

    # Copy Scream receiver if built
    if [ -f "$SCRIPT_DIR/upstream-scream/Receivers/pipewire/build/scream" ]; then
        log_info "Copying Scream receiver..."
        mkdir -p "$AIROOTFS/usr/bin"
        cp "$SCRIPT_DIR/upstream-scream/Receivers/pipewire/build/scream" "$AIROOTFS/usr/bin/scream-receiver"
        chmod +x "$AIROOTFS/usr/bin/scream-receiver"
    else
        log_warning "Scream not built yet. Run option 4 first."
    fi

    # Copy neuronos-hardware Python package
    log_info "Copying neuronos-hardware package..."
    mkdir -p "$AIROOTFS/usr/lib/python3.12/site-packages"
    cp -r "$SCRIPT_DIR/neuronos-hardware/neuron_hw" "$AIROOTFS/usr/lib/python3.12/site-packages/"
    cp -r "$SCRIPT_DIR/neuronos-hardware/data" "$AIROOTFS/usr/share/neuronos/" 2>/dev/null || true

    # Copy neuronos-vm-manager Python package
    log_info "Copying neuronos-vm-manager package..."
    cp -r "$SCRIPT_DIR/neuronos-vm-manager/neuronvm" "$AIROOTFS/usr/lib/python3.12/site-packages/"
    mkdir -p "$AIROOTFS/usr/share/neuronos"
    cp -r "$SCRIPT_DIR/neuronos-vm-manager/data/"* "$AIROOTFS/usr/share/neuronos/" 2>/dev/null || true

    # Copy single-GPU scripts
    log_info "Copying single-GPU scripts..."
    mkdir -p "$AIROOTFS/usr/lib/neuronos"
    cp "$SCRIPT_DIR/neuronos-single-gpu/scripts/"*.sh "$AIROOTFS/usr/lib/neuronos/"
    chmod +x "$AIROOTFS/usr/lib/neuronos/"*.sh

    # Copy libvirt hook
    mkdir -p "$AIROOTFS/etc/libvirt/hooks"
    cp "$SCRIPT_DIR/neuronos-single-gpu/hooks/qemu" "$AIROOTFS/etc/libvirt/hooks/"
    chmod +x "$AIROOTFS/etc/libvirt/hooks/qemu"

    # Make NeuronOS apps executable
    chmod +x "$AIROOTFS/usr/bin/neuronos-welcome" 2>/dev/null || true
    chmod +x "$AIROOTFS/usr/bin/neuronos-vmmanager" 2>/dev/null || true

    log_success "Components copied to ISO"
}

# ============================================================
# STEP 9: Build NeuronOS ISO
# ============================================================
build_iso() {
    log_info "Building NeuronOS ISO..."

    # Check if syslinux directory exists (profile setup check)
    if [ ! -d "$SCRIPT_DIR/neuronos-iso/syslinux" ]; then
        log_warning "Archiso profile not fully set up. Running setup_archiso_profile first..."
        setup_archiso_profile
    fi

    # Copy built components to the ISO
    copy_components_to_iso

    # Clean previous build artifacts
    if [ -d "$BUILD_DIR/iso-work" ]; then
        log_info "Cleaning previous build directory..."
        sudo rm -rf "$BUILD_DIR/iso-work"
    fi

    mkdir -p "$BUILD_DIR/iso-work"
    mkdir -p "$BUILD_DIR/iso-output"

    cd "$SCRIPT_DIR/neuronos-iso"

    sudo mkarchiso -v \
        -w "$BUILD_DIR/iso-work" \
        -o "$BUILD_DIR/iso-output" \
        .

    log_success "NeuronOS ISO built successfully!"
    log_info "ISO location: $BUILD_DIR/iso-output/"
    ls -lh "$BUILD_DIR/iso-output/"*.iso
}

# ============================================================
# STEP 9: Enable Services
# ============================================================
enable_services() {
    log_info "Enabling system services..."

    sudo systemctl enable libvirtd
    sudo systemctl enable NetworkManager

    # Add current user to required groups
    sudo usermod -aG libvirt,kvm "$USER"

    log_success "Services enabled"
    log_warning "You may need to log out and back in for group changes to take effect"
}

# ============================================================
# Main Menu
# ============================================================
show_menu() {
    echo ""
    echo "=============================================="
    echo "  NeuronOS Development Setup"
    echo "=============================================="
    echo ""
    echo "1) Full setup (everything)"
    echo "2) Install dependencies only"
    echo "3) Build Looking Glass"
    echo "4) Build Scream"
    echo "5) Build Calamares"
    echo "6) Install NeuronOS Python packages"
    echo "7) Install single-GPU scripts"
    echo "8) Setup Archiso profile"
    echo "9) Copy components to ISO"
    echo "10) Build ISO"
    echo "11) Enable services"
    echo "0) Exit"
    echo ""
    read -p "Select option: " choice

    case $choice in
        1)
            install_dependencies
            build_looking_glass
            build_scream
            build_calamares
            install_neuronos_packages
            install_single_gpu_scripts
            setup_archiso_profile
            enable_services
            log_success "Full setup complete!"
            log_info "Run 'sudo ./setup.sh' and select option 9 to build ISO"
            ;;
        2) install_dependencies ;;
        3) build_looking_glass ;;
        4) build_scream ;;
        5) build_calamares ;;
        6) install_neuronos_packages ;;
        7) install_single_gpu_scripts ;;
        8) setup_archiso_profile ;;
        9) copy_components_to_iso ;;
        10) build_iso ;;
        11) enable_services ;;
        0) exit 0 ;;
        *)
            log_error "Invalid option"
            show_menu
            ;;
    esac
}

# ============================================================
# Entry Point
# ============================================================
if [[ "$1" == "--full" ]]; then
    install_dependencies
    build_looking_glass
    build_scream
    build_calamares
    install_neuronos_packages
    install_single_gpu_scripts
    setup_archiso_profile
    enable_services
    log_success "Full setup complete!"
elif [[ "$1" == "--iso" ]]; then
    build_iso
else
    show_menu
fi
