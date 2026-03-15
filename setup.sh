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

    # Copy the releng profile as a base
    cp -r "$SCRIPT_DIR/upstream-archiso/configs/releng/"* "$SCRIPT_DIR/neuronos-iso/"

    # Our packages.x86_64 already has the merged list, no need to copy

    # Copy NeuronOS airootfs customizations
    # These overlay on top of the releng airootfs

    log_success "Archiso profile setup complete"
}

# ============================================================
# STEP 8: Build NeuronOS ISO
# ============================================================
build_iso() {
    log_info "Building NeuronOS ISO..."

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
    echo "9) Build ISO"
    echo "10) Enable services"
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
        9) build_iso ;;
        10) enable_services ;;
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
