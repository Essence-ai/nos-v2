#!/bin/bash
# ============================================================
# NeuronOS Development Setup Script
# Run this on a fresh Arch Linux installation
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
INSTALL_DIR="/usr/local"

# Detect the Python site-packages version dynamically
PYTHON_SITEPKG_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "3.12")"

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
        libvirt-python \
        jq

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
        pipewire \
        libxss \
        libxpresent \
        libdecor

    # Scream dependencies (pipewire-pulse replaces pulseaudio)
    sudo pacman -S --noconfirm --needed \
        pipewire-pulse

    # Virtualization (bridge-utils is deprecated, iproute2 handles bridges)
    sudo pacman -S --noconfirm --needed \
        qemu-full \
        libvirt \
        virt-manager \
        edk2-ovmf \
        dnsmasq

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

    cd "$SCRIPT_DIR/upstream-scream/Receivers/unix"

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

    # Copy NeuronOS custom modules INTO the Calamares source tree
    log_info "Integrating NeuronOS modules into Calamares..."
    for module_dir in "$SCRIPT_DIR/neuronos-installer/modules/"*/; do
        module_name=$(basename "$module_dir")
        target="$SCRIPT_DIR/upstream-calamares/src/modules/$module_name"
        log_info "  Copying module: $module_name"
        mkdir -p "$target"
        cp -r "$module_dir"* "$target/"
    done

    # Copy NeuronOS branding into Calamares
    if [ -d "$SCRIPT_DIR/neuronos-installer/branding" ]; then
        log_info "  Copying NeuronOS branding..."
        cp -r "$SCRIPT_DIR/neuronos-installer/branding/"* "$SCRIPT_DIR/upstream-calamares/src/branding/"
    fi

    # Copy NeuronOS settings.conf
    if [ -f "$SCRIPT_DIR/neuronos-installer/settings.conf" ]; then
        log_info "  Copying NeuronOS settings.conf..."
        cp "$SCRIPT_DIR/neuronos-installer/settings.conf" "$SCRIPT_DIR/upstream-calamares/settings.conf"
    fi

    cd "$SCRIPT_DIR/upstream-calamares"

    # Clean previous build
    rm -rf build
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

    log_success "Calamares built and installed with NeuronOS modules"
}

# ============================================================
# STEP 5: Install NeuronOS Python Packages
# ============================================================
install_neuronos_packages() {
    log_info "Installing NeuronOS Python packages..."

    cd "$SCRIPT_DIR"

    # Arch enables PEP 668 (externally managed env), so allow user-site installs
    # performed by this setup script.
    local pip_cmd="python -m pip install --user --break-system-packages"

    # Install neuronos-hardware
    $pip_cmd -e neuronos-hardware

    # Install neuronos-vm-manager
    $pip_cmd -e neuronos-vm-manager

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

    # Backup ALL of our custom NeuronOS files before overlaying releng base
    log_info "Backing up NeuronOS customizations..."
    local BACKUP_DIR="/tmp/neuronos-airootfs-bak"
    rm -rf "$BACKUP_DIR"
    cp -a "$SCRIPT_DIR/neuronos-iso/airootfs" "$BACKUP_DIR"
    cp "$SCRIPT_DIR/neuronos-iso/packages.x86_64" /tmp/neuronos-packages.x86_64.bak
    cp "$SCRIPT_DIR/neuronos-iso/profiledef.sh" /tmp/neuronos-profiledef.sh.bak
    cp "$SCRIPT_DIR/neuronos-iso/pacman.conf" /tmp/neuronos-pacman.conf.bak 2>/dev/null || true

    # Copy the releng profile directories we need (syslinux, efiboot, grub, airootfs)
    log_info "Copying boot directories from upstream archiso..."
    cp -r "$SCRIPT_DIR/upstream-archiso/configs/releng/syslinux" "$SCRIPT_DIR/neuronos-iso/"
    cp -r "$SCRIPT_DIR/upstream-archiso/configs/releng/efiboot" "$SCRIPT_DIR/neuronos-iso/"
    cp -r "$SCRIPT_DIR/upstream-archiso/configs/releng/grub" "$SCRIPT_DIR/neuronos-iso/"

    # Copy airootfs base from releng (provides root's shell config, etc.)
    log_info "Setting up airootfs base from releng..."
    cp -r "$SCRIPT_DIR/upstream-archiso/configs/releng/airootfs/"* "$SCRIPT_DIR/neuronos-iso/airootfs/" 2>/dev/null || true

    # Restore ALL NeuronOS customizations on top (our files take priority)
    log_info "Restoring NeuronOS customizations over releng base..."
    cp -a "$BACKUP_DIR/"* "$SCRIPT_DIR/neuronos-iso/airootfs/"

    # Copy bootstrap_packages if it exists
    if [ -f "$SCRIPT_DIR/upstream-archiso/configs/releng/bootstrap_packages" ]; then
        cp "$SCRIPT_DIR/upstream-archiso/configs/releng/bootstrap_packages" "$SCRIPT_DIR/neuronos-iso/"
    fi

    # Restore our custom top-level profile files
    cp /tmp/neuronos-packages.x86_64.bak "$SCRIPT_DIR/neuronos-iso/packages.x86_64"
    cp /tmp/neuronos-profiledef.sh.bak "$SCRIPT_DIR/neuronos-iso/profiledef.sh"
    cp /tmp/neuronos-pacman.conf.bak "$SCRIPT_DIR/neuronos-iso/pacman.conf" 2>/dev/null || true

    # Clean up backup
    rm -rf "$BACKUP_DIR"

    # Update syslinux config to say NeuronOS instead of Arch Linux
    if [ -f "$SCRIPT_DIR/neuronos-iso/syslinux/archiso_sys-linux.cfg" ]; then
        sed -i 's/Arch Linux/NeuronOS/g' "$SCRIPT_DIR/neuronos-iso/syslinux/"*.cfg
    fi

    # Update GRUB config to say NeuronOS
    if [ -f "$SCRIPT_DIR/neuronos-iso/grub/grub.cfg" ]; then
        sed -i 's/Arch Linux/NeuronOS/g' "$SCRIPT_DIR/neuronos-iso/grub/grub.cfg"
    fi

    # Create systemd service enable symlinks
    log_info "Creating systemd service symlinks..."
    mkdir -p "$SCRIPT_DIR/neuronos-iso/airootfs/etc/systemd/system/multi-user.target.wants"
    ln -sf /etc/systemd/system/neuronos-live-setup.service \
        "$SCRIPT_DIR/neuronos-iso/airootfs/etc/systemd/system/multi-user.target.wants/neuronos-live-setup.service" 2>/dev/null || true
    ln -sf /usr/lib/systemd/system/NetworkManager.service \
        "$SCRIPT_DIR/neuronos-iso/airootfs/etc/systemd/system/multi-user.target.wants/NetworkManager.service" 2>/dev/null || true

    # Make scripts executable
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
    local SITEPKG="$AIROOTFS/usr/lib/python${PYTHON_SITEPKG_VER}/site-packages"

    # --- Binaries ---

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
    if [ -f "$SCRIPT_DIR/upstream-scream/Receivers/unix/build/scream" ]; then
        log_info "Copying Scream receiver..."
        mkdir -p "$AIROOTFS/usr/bin"
        cp "$SCRIPT_DIR/upstream-scream/Receivers/unix/build/scream" "$AIROOTFS/usr/bin/scream-receiver"
        chmod +x "$AIROOTFS/usr/bin/scream-receiver"
        # Also copy as 'scream' for the systemd service
        cp "$SCRIPT_DIR/upstream-scream/Receivers/unix/build/scream" "$AIROOTFS/usr/bin/scream"
        chmod +x "$AIROOTFS/usr/bin/scream"
    else
        log_warning "Scream not built yet. Run option 4 first."
    fi

    # --- Python Packages (with proper site-packages and entry points) ---

    log_info "Installing neuronos-hardware Python package to ISO..."
    mkdir -p "$SITEPKG"
    cp -r "$SCRIPT_DIR/neuronos-hardware/neuron_hw" "$SITEPKG/"
    # Copy the hardware database
    mkdir -p "$AIROOTFS/usr/share/neuronos"
    cp -r "$SCRIPT_DIR/neuronos-hardware/data/"* "$AIROOTFS/usr/share/neuronos/" 2>/dev/null || true

    log_info "Installing neuronos-vm-manager Python package to ISO..."
    cp -r "$SCRIPT_DIR/neuronos-vm-manager/neuronvm" "$SITEPKG/"

    # Create console script entry points
    log_info "Creating entry point scripts..."
    mkdir -p "$AIROOTFS/usr/bin"

    cat > "$AIROOTFS/usr/bin/neuron-hwdetect" << 'HWEOF'
#!/usr/bin/env python3
from neuron_hw.cli import main
main()
HWEOF
    chmod +x "$AIROOTFS/usr/bin/neuron-hwdetect"

    cat > "$AIROOTFS/usr/bin/neuronvm" << 'VMEOF'
#!/usr/bin/env python3
from neuronvm.cli import main
main()
VMEOF
    chmod +x "$AIROOTFS/usr/bin/neuronvm"

    cat > "$AIROOTFS/usr/bin/neuronvm-launch" << 'LAUNCHEOF'
#!/usr/bin/env python3
from neuronvm.launcher import main
main()
LAUNCHEOF
    chmod +x "$AIROOTFS/usr/bin/neuronvm-launch"

    # --- VM Manager Data ---

    log_info "Copying VM manager data files..."
    mkdir -p "$AIROOTFS/usr/share/neuronos"
    cp -r "$SCRIPT_DIR/neuronos-vm-manager/data/"* "$AIROOTFS/usr/share/neuronos/" 2>/dev/null || true

    # Copy VM domain XML template
    if [ -f "$SCRIPT_DIR/neuronos-vm-manager/data/win11-neuron.xml" ]; then
        cp "$SCRIPT_DIR/neuronos-vm-manager/data/win11-neuron.xml" "$AIROOTFS/usr/share/neuronos/"
    fi

    # Copy VM setup script
    if [ -f "$SCRIPT_DIR/neuronos-vm-manager/data/vm-setup.py" ]; then
        mkdir -p "$AIROOTFS/usr/lib/neuronos"
        cp "$SCRIPT_DIR/neuronos-vm-manager/data/vm-setup.py" "$AIROOTFS/usr/lib/neuronos/"
        chmod +x "$AIROOTFS/usr/lib/neuronos/vm-setup.py"
    fi

    # --- Single-GPU Scripts ---

    log_info "Copying single-GPU scripts..."
    mkdir -p "$AIROOTFS/usr/lib/neuronos"
    cp "$SCRIPT_DIR/neuronos-single-gpu/scripts/"*.sh "$AIROOTFS/usr/lib/neuronos/"
    chmod +x "$AIROOTFS/usr/lib/neuronos/"*.sh

    # Copy libvirt hook
    mkdir -p "$AIROOTFS/etc/libvirt/hooks"
    cp "$SCRIPT_DIR/neuronos-single-gpu/hooks/qemu" "$AIROOTFS/etc/libvirt/hooks/"
    chmod +x "$AIROOTFS/etc/libvirt/hooks/qemu"

    # Copy single-GPU systemd services
    if [ -d "$SCRIPT_DIR/neuronos-single-gpu/systemd" ]; then
        mkdir -p "$AIROOTFS/etc/systemd/system"
        cp "$SCRIPT_DIR/neuronos-single-gpu/systemd/"*.service "$AIROOTFS/etc/systemd/system/" 2>/dev/null || true
    fi

    # Copy hardware detection systemd service
    if [ -f "$SCRIPT_DIR/neuronos-hardware/systemd/neuron-hw-check.service" ]; then
        mkdir -p "$AIROOTFS/etc/systemd/system"
        cp "$SCRIPT_DIR/neuronos-hardware/systemd/neuron-hw-check.service" "$AIROOTFS/etc/systemd/system/"
    fi

    # --- Calamares Integration ---

    log_info "Copying Calamares modules for installed system..."
    # Copy the neuronos-hardware package into Calamares module path too
    # so the neuronhwdetect module can import neuron_hw during installation
    local CALA_MODULES="$AIROOTFS/usr/lib/calamares/modules"
    for module_dir in "$SCRIPT_DIR/neuronos-installer/modules/"*/; do
        module_name=$(basename "$module_dir")
        log_info "  Copying Calamares module: $module_name"
        mkdir -p "$CALA_MODULES/$module_name"
        cp -r "$module_dir"* "$CALA_MODULES/$module_name/"
    done

    # Copy Calamares settings and branding
    if [ -f "$SCRIPT_DIR/neuronos-installer/settings.conf" ]; then
        mkdir -p "$AIROOTFS/etc/calamares"
        cp "$SCRIPT_DIR/neuronos-installer/settings.conf" "$AIROOTFS/etc/calamares/"
    fi
    if [ -d "$SCRIPT_DIR/neuronos-installer/branding" ]; then
        mkdir -p "$AIROOTFS/etc/calamares/branding"
        cp -r "$SCRIPT_DIR/neuronos-installer/branding/"* "$AIROOTFS/etc/calamares/branding/" 2>/dev/null || true
    fi

    # --- Post-Install Script ---
    # This script runs during Calamares installation to install
    # Looking Glass, Scream, and NeuronOS components to the target system
    log_info "Creating post-install integration script..."
    cat > "$AIROOTFS/usr/lib/neuronos/install-to-target.sh" << 'INSTALLEOF'
#!/bin/bash
# Called by Calamares post-install to copy NeuronOS components to the installed system
# Usage: install-to-target.sh <target_root>
set -e
TARGET="$1"
if [ -z "$TARGET" ]; then
    echo "ERROR: No target root specified"
    exit 1
fi

echo "Installing NeuronOS components to $TARGET..."

# Copy binaries
for bin in looking-glass-client scream scream-receiver neuron-hwdetect neuronvm neuronvm-launch \
           neuronos-welcome neuronos-vmmanager neuronos-onboarding; do
    if [ -f "/usr/bin/$bin" ]; then
        cp "/usr/bin/$bin" "$TARGET/usr/bin/"
        chmod +x "$TARGET/usr/bin/$bin"
    fi
done

# Copy Python packages
PYTHON_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
SRC_SITE="/usr/lib/python${PYTHON_VER}/site-packages"
DST_SITE="$TARGET/usr/lib/python${PYTHON_VER}/site-packages"
mkdir -p "$DST_SITE"
for pkg in neuron_hw neuronvm; do
    if [ -d "$SRC_SITE/$pkg" ]; then
        cp -r "$SRC_SITE/$pkg" "$DST_SITE/"
    fi
done

# Copy NeuronOS data files
mkdir -p "$TARGET/usr/share/neuronos"
cp -r /usr/share/neuronos/* "$TARGET/usr/share/neuronos/" 2>/dev/null || true

# Copy NeuronOS lib scripts
mkdir -p "$TARGET/usr/lib/neuronos"
cp -r /usr/lib/neuronos/* "$TARGET/usr/lib/neuronos/" 2>/dev/null || true
chmod +x "$TARGET/usr/lib/neuronos/"*.sh 2>/dev/null || true
chmod +x "$TARGET/usr/lib/neuronos/"*.py 2>/dev/null || true

# Copy libvirt hooks
mkdir -p "$TARGET/etc/libvirt/hooks"
if [ -f /etc/libvirt/hooks/qemu ]; then
    cp /etc/libvirt/hooks/qemu "$TARGET/etc/libvirt/hooks/"
    chmod +x "$TARGET/etc/libvirt/hooks/qemu"
fi

# Copy systemd services
for svc in neuronos-firstboot.service neuron-gpu-recovery.service neuron-hw-check.service; do
    if [ -f "/etc/systemd/system/$svc" ]; then
        cp "/etc/systemd/system/$svc" "$TARGET/etc/systemd/system/"
    fi
done

# Copy user services
mkdir -p "$TARGET/etc/systemd/user"
if [ -f /etc/systemd/user/scream-receiver.service ]; then
    cp /etc/systemd/user/scream-receiver.service "$TARGET/etc/systemd/user/"
fi

# Copy tmpfiles.d
mkdir -p "$TARGET/etc/tmpfiles.d"
for conf in /etc/tmpfiles.d/looking-glass.conf /etc/tmpfiles.d/scream-ivshmem.conf; do
    if [ -f "$conf" ]; then
        cp "$conf" "$TARGET/etc/tmpfiles.d/"
    fi
done

# Copy Calamares modules
if [ -d /usr/lib/calamares/modules ]; then
    mkdir -p "$TARGET/usr/lib/calamares/modules"
    cp -r /usr/lib/calamares/modules/neuron* "$TARGET/usr/lib/calamares/modules/" 2>/dev/null || true
fi

# Copy desktop entries and autostart
for desktop in neuronos-welcome.desktop neuronos-vmmanager.desktop neuronos-onboarding.desktop; do
    if [ -f "/usr/share/applications/$desktop" ]; then
        mkdir -p "$TARGET/usr/share/applications"
        cp "/usr/share/applications/$desktop" "$TARGET/usr/share/applications/"
    fi
done

# Copy onboarding autostart to skel
if [ -d /etc/skel/.config/autostart ]; then
    mkdir -p "$TARGET/etc/skel/.config/autostart"
    cp /etc/skel/.config/autostart/neuronos-onboarding.desktop "$TARGET/etc/skel/.config/autostart/" 2>/dev/null || true
fi

# Enable services on target
arch-chroot "$TARGET" systemctl enable libvirtd 2>/dev/null || true
arch-chroot "$TARGET" systemctl enable NetworkManager 2>/dev/null || true
arch-chroot "$TARGET" systemctl enable sddm 2>/dev/null || true
arch-chroot "$TARGET" systemctl enable neuron-gpu-recovery.service 2>/dev/null || true

echo "NeuronOS components installed to target."
INSTALLEOF
    chmod +x "$AIROOTFS/usr/lib/neuronos/install-to-target.sh"

    # --- Make all NeuronOS scripts executable ---
    chmod +x "$AIROOTFS/usr/bin/neuronos-welcome" 2>/dev/null || true
    chmod +x "$AIROOTFS/usr/bin/neuronos-vmmanager" 2>/dev/null || true
    chmod +x "$AIROOTFS/usr/bin/neuronos-onboarding" 2>/dev/null || true
    chmod +x "$AIROOTFS/usr/lib/neuronos/neuronos-firstboot.sh" 2>/dev/null || true

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
# STEP 10: Enable Services
# ============================================================
enable_services() {
    log_info "Enabling system services..."

    # These may not exist on a minimal build machine — that's OK,
    # they get enabled inside the ISO/installed system separately.
    sudo systemctl enable libvirtd 2>/dev/null || log_warning "libvirtd not found on build host (OK if only building ISO)"
    sudo systemctl enable NetworkManager 2>/dev/null || log_warning "NetworkManager not found on build host (OK if only building ISO)"

    # Add current user to required groups
    sudo usermod -aG libvirt,kvm "$USER" 2>/dev/null || true

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
    echo "1)  Full setup (everything)"
    echo "2)  Install dependencies only"
    echo "3)  Build Looking Glass"
    echo "4)  Build Scream"
    echo "5)  Build Calamares (with NeuronOS modules)"
    echo "6)  Install NeuronOS Python packages"
    echo "7)  Install single-GPU scripts"
    echo "8)  Setup Archiso profile"
    echo "9)  Copy components to ISO"
    echo "10) Build ISO"
    echo "11) Enable services"
    echo "0)  Exit"
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
            copy_components_to_iso
            enable_services
            log_success "Full setup complete!"
            log_info "Run 'sudo ./setup.sh' and select option 10 to build ISO"
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
    copy_components_to_iso
    enable_services
    log_success "Full setup complete!"
elif [[ "$1" == "--iso" ]]; then
    build_iso
else
    show_menu
fi
