# NeuronOS — Engineering Specification & Implementation Guide

**Document Status:** Active — Foundation Reference for All Engineering Work  
**Audience:** Software Engineering Team  
**Last Updated:** March 2026

---

## 1. What Is NeuronOS

NeuronOS is a Linux-based desktop operating system designed to be a genuine, everyday replacement for Windows and macOS. It is not a hobbyist distro, a developer tool, or a niche product for people who already know Linux. It is a consumer-grade operating system intended for the full spectrum of computer users: a teenager buying their first laptop, a retiree checking email, a software engineer running Docker containers, a video editor cutting a feature film in Premiere Pro, a mechanical engineer designing turbine blades in SolidWorks, and a gamer playing the latest AAA titles. Windows serves all of these people today. NeuronOS must do the same.

The fundamental problem NeuronOS solves is not that Linux is technically inferior to Windows or macOS. For most tasks — web browsing, email, document editing, software development, media playback — Linux already works as well or better. The problem is that a significant body of professional and creative software only runs on Windows or macOS. Adobe Creative Suite, Autodesk products, Microsoft Office (the full desktop version), most professional audio production software, and a meaningful percentage of PC games either do not exist on Linux or run poorly through existing compatibility layers. This software gap is the single largest barrier preventing mainstream Linux adoption. NeuronOS closes that gap.

NeuronOS does this through a hybrid architecture. Applications that run natively on Linux run natively. Applications that work well through Wine or Proton (the open-source Windows compatibility layers) run through those layers. Applications that require full Windows fidelity — particularly GPU-accelerated professional software like Photoshop, Premiere Pro, After Effects, AutoCAD, and SolidWorks — run inside a Windows virtual machine with direct GPU hardware access, displayed to the user through a low-latency borderless window that makes the application look and feel like it is running natively on their desktop. The user never interacts with the virtual machine directly. They never see a Windows desktop. They click an application icon, the application appears, and they use it. The underlying complexity is entirely invisible.

This is not a theoretical architecture. Every component exists and is proven individually. GPU passthrough virtual machines are used daily by thousands of Linux users. Looking Glass (the low-latency VM display tool) is a mature open-source project. Wine and Proton run the majority of Windows software and nearly all PC games. What does not exist today is a product that integrates all of these technologies into a single, seamless experience that a non-technical person can install and use. That integration is what NeuronOS builds, and that integration is what this engineering team is responsible for delivering.

---

## 2. Why This Product Exists

There is a circular problem in the desktop operating system market that has persisted for decades. People do not switch to Linux because the software they need does not run on Linux. Software companies do not build for Linux because not enough people use it. This creates a self-reinforcing monopoly for Windows and, to a lesser extent, macOS.

Valve broke this cycle for gaming. Five years ago, Linux gaming was impractical. Valve invested in Proton, shipped the Steam Deck running Linux, and now the Linux gaming ecosystem is thriving. Anti-cheat vendors have added Linux support. Game studios are testing on Linux. The cycle was broken not by convincing game developers to build for Linux first, but by making their existing Windows games run on Linux so well that users switched, and developer support followed.

NeuronOS applies the same strategy to the entire desktop software ecosystem, not just gaming. If a video editor can run Premiere Pro on NeuronOS at 98% of native Windows performance without any manual setup, they can switch. If enough people switch, Adobe faces market pressure to either build a native Linux version of Premiere Pro or lose customers to competitors who do. The GPU-passthrough VM layer is a transitional technology — a bridge that makes switching possible today, which in turn creates the market conditions that eventually make the bridge unnecessary.

The product exists because someone needs to build that bridge and package it as a product that normal people can use. That is what we are building.

---

## 3. The Core Technical Challenge

The central engineering challenge of NeuronOS is not building an operating system. The operating system already exists — we are building on Arch Linux, which provides the kernel, the package manager, the system services, and the foundational infrastructure. The central challenge is building the invisible virtualization layer that allows Windows and macOS applications to run seamlessly on a Linux desktop without the user knowing or caring that virtualization is involved.

This challenge breaks down into six interconnected problems, each of which must be solved to a high standard of reliability and usability. These six problems are the reason NeuronOS exists as a product. Everything else — the desktop theme, the bundled applications, the browser, the office suite — is commodity work that any Linux distribution can do. The six problems described below are what make NeuronOS different, and they are where this engineering team must focus its effort.

### 3.1 Automatic Hardware Detection and GPU Configuration

GPU passthrough — giving a virtual machine direct access to a physical graphics card — requires specific hardware support and specific system configuration. The CPU must support IOMMU (called VT-d on Intel and AMD-Vi on AMD). The system firmware must have IOMMU enabled. The GPU being passed through must be in its own IOMMU group (a hardware isolation boundary). And the system must be configured so that the Linux host does not claim the GPU before the virtual machine can use it.

Today, setting this up requires the user to manually identify their hardware, edit bootloader configuration files, write kernel module configuration files, and verify IOMMU groupings through command-line tools. This process takes an experienced Linux user several hours. For a non-technical user, it is effectively impossible.

NeuronOS must do all of this automatically, silently, and correctly across a wide range of hardware. The hardware detection system must identify every GPU in the system and classify each one (integrated graphics versus discrete graphics, vendor, model, PCI bus address, IOMMU group membership). It must determine the optimal GPU configuration for the detected hardware — whether the system supports dual-GPU passthrough (integrated GPU for Linux, discrete GPU for the VM, with no screen interruption), single-GPU dynamic switching (the only GPU unbinds from Linux when the VM launches, causing a brief screen blackout), or no passthrough capability at all. It must then generate the correct bootloader parameters, kernel module configurations, and VFIO device bindings without any user input.

This system must handle edge cases gracefully. Some BIOS implementations disable IOMMU by default and cannot enable it without a firmware update. Some IOMMU group configurations put the GPU in a shared group with other devices, preventing clean isolation. Some laptops have non-standard GPU switching mechanisms (NVIDIA Optimus, AMD Switchable Graphics) that conflict with standard VFIO passthrough. The hardware detection system must identify all of these situations, inform the user of their options in plain language, and degrade gracefully when full passthrough is not possible.

The hardware detection system runs in two contexts: during installation (within the Calamares installer, as a custom module that executes before the partition screen) and at boot time (as a system service that verifies the configuration is still correct after hardware changes). It is the single most critical piece of custom code in NeuronOS, because if it fails or misconfigures the system, the entire VM experience breaks.

### 3.2 The Borderless VM Display (Looking Glass Integration)

When a user launches a Windows application through NeuronOS, they must see only the application. They must not see a Windows desktop, a Windows taskbar, a VM management window, or any other artifact of the virtualization layer. The application must appear as a window on their Linux desktop, just like any other application. They must be able to resize it, minimize it, move it between monitors, and Alt-Tab to and from it.

This is achieved through Looking Glass, an open-source project that captures the framebuffer of a virtual machine and displays it in a client window on the host with very low latency (under 1ms in optimal configurations). Looking Glass supports borderless window mode, which removes all window decorations and allows the VM display to appear as a bare application surface.

However, Looking Glass on its own does not deliver the experience NeuronOS requires. Out of the box, Looking Glass displays the entire VM screen, including the Windows desktop, taskbar, and any other elements. Achieving the "application window only" appearance requires additional work: the VM must be configured to auto-launch the desired application in a maximized or full-screen state, the Windows taskbar must be auto-hidden, and the Looking Glass client window must be sized and positioned to match the application's actual content area. The system must handle window state changes (the user minimizes the VM app, switches to a native Linux app, then switches back), multi-monitor configurations, and resolution changes.

The Looking Glass integration layer is a wrapper around the Looking Glass client that manages all of this automatically. When the user clicks a desktop shortcut for a VM application, the wrapper boots the VM (if not already running), waits for the application to launch, configures the Looking Glass client to display in borderless mode at the correct size and position, and manages the lifecycle of the VM and the display connection for the duration of the session. When the user closes the application, the wrapper determines whether to shut down the VM or keep it running for other VM applications.

### 3.3 The VM Lifecycle Manager

A virtual machine is a heavyweight resource. It consumes dedicated RAM, CPU cores, and (in the case of GPU passthrough) an entire graphics card. Managing VM lifecycle efficiently is critical both for system performance and for user experience.

NeuronOS uses a single shared Windows VM for all Windows applications, not one VM per application. This means the first Windows application launch incurs a VM boot cost (typically 10-20 seconds, depending on hardware), but subsequent Windows applications launch nearly instantly because the VM is already running. The VM lifecycle manager handles starting the VM when the first Windows application is requested, keeping the VM alive while any Windows application is running, shutting the VM down when the last Windows application is closed (with a configurable grace period to avoid unnecessary restarts), and suspending the VM to disk when the system goes to sleep.

The VM lifecycle manager also handles resource allocation. It must determine how much RAM to assign to the VM based on available system memory, how many CPU cores to assign based on the system's core count and current load, and whether to adjust these allocations dynamically as the user's workload changes. A user running Photoshop alone needs less VM resources than a user running Photoshop, Premiere Pro, and After Effects simultaneously.

The VM lifecycle manager communicates with the virtualization layer through libvirt, the standard Linux VM management API. VM configurations are stored as libvirt domain XML files. The manager is the primary consumer of the hardware detection system's output, using the detected GPU configuration to determine whether to launch in dual-GPU mode (no screen interruption) or single-GPU mode (screen blackout during launch).

### 3.4 Single-GPU Dynamic Switching

The dual-GPU configuration (integrated graphics for Linux, discrete graphics for the VM) provides the best user experience because both the Linux desktop and the VM can display simultaneously. However, a substantial portion of the target market — budget laptops, older desktops, some gaming laptops with non-standard GPU switching — has only one GPU available for passthrough.

On these systems, launching a GPU-passthrough VM requires the GPU to be unbound from the Linux graphics driver and rebound to the VFIO passthrough driver. This means the Linux display server must be stopped, the GPU driver must be unloaded, the VFIO driver must be loaded and bound to the GPU, and the VM can then start with GPU access. When the VM shuts down, the process reverses. During both transitions, the screen goes black for approximately 5-10 seconds.

This is an unavoidable hardware limitation — there is no software workaround for the fact that a single GPU cannot serve two operating systems simultaneously (until AMD's SR-IOV technology reaches consumer GPUs, which is expected with the Radeon RX 9000 series in late 2026 or 2027). The engineering challenge is making this transition as smooth, reliable, and clearly communicated to the user as possible.

The single-GPU switching system must stop the Linux display manager cleanly, unload the GPU driver modules (nvidia, nouveau, amdgpu, or i915 depending on the hardware) without causing a kernel panic, load the VFIO driver modules and bind them to the GPU, start the VM, and monitor the VM for shutdown. On VM shutdown, it must reverse the process and restart the Linux display manager, returning the user to their Linux desktop exactly as they left it (same open applications, same window positions, same unsaved work). If any step in the process fails, the system must recover gracefully — the worst possible outcome is a user staring at a black screen with no way to recover short of a hard power cycle.

The single-GPU switching system must also communicate clearly with the user. Before initiating a switch, the system should display a notification: "Starting Adobe Premiere Pro. Your screen will go black for approximately 5 seconds while the graphics card switches to the application. Your Linux applications will continue running in the background." After the VM shuts down and the Linux desktop returns, a notification should confirm: "Adobe Premiere Pro has closed. Your graphics card has returned to your desktop." This communication is essential for user trust — a user who sees an unexplained black screen will assume their computer has crashed.

### 3.5 The Application Router

When a user installs or launches an application, NeuronOS must determine the optimal way to run it. There are three paths: native Linux execution (best performance, best integration), Wine/Proton execution (good for many applications and most games, no VM overhead), and GPU-passthrough VM execution (required for applications that need full Windows GPU acceleration, like Adobe Creative Suite and professional CAD software).

The application router is a decision engine backed by a curated database. The database contains entries for several hundred common applications, each tagged with the recommended execution path and any special configuration requirements. When a user downloads a Windows executable or searches for an application in NeuronStore, the router consults the database to determine the best path.

The routing priority is always native Linux first, then Wine/Proton, then VM. A user searching for "word processor" should be offered LibreOffice (native) before Microsoft Word (Wine) before Microsoft Word (VM). A user downloading a game should have it routed through Proton, not the VM, because Proton provides equal or better performance for the vast majority of games without the overhead of a full VM. The VM path is reserved for applications where Wine/Proton cannot deliver acceptable results — primarily GPU-accelerated professional creative and engineering tools.

The application database is not static. It must be updatable as new applications are tested and as Wine/Proton compatibility improves. An application that requires the VM today might work through Wine in six months. The database should be maintained as a versioned JSON or YAML file distributed through the NeuronOS update channel.

### 3.6 The Installer

The NeuronOS installer is the user's first interaction with the product. If the installer is confusing, intimidating, or fails, the user's relationship with NeuronOS ends before it begins. The installer must be as simple as or simpler than the Windows and macOS installers.

The installer is built on Calamares, the standard Linux distribution installer framework. Calamares supports custom modules written in Python, which is how NeuronOS's hardware detection, VFIO configuration, and VM setup are integrated into the installation process. The user-facing flow is minimal: select language, set timezone, enter username and password, select the installation disk, and click install. That is the entire user-facing interaction — five steps plus a progress bar.

Behind those five steps, the installer does significant additional work that the user never sees. The hardware detection module runs during the "preparing installation" phase, before the partition screen. It identifies all GPUs, classifies the system's passthrough capability, and generates the VFIO configuration. The partitioning module creates a BTRFS filesystem with subvolumes configured for automatic snapshotting (this enables the rollback system described later). The package installation module installs the base system, the KDE Plasma desktop, the NeuronVM Manager, and all required virtualization components. The post-install module writes the GRUB bootloader configuration with the correct IOMMU kernel parameters, installs the VFIO configuration files, and enables the necessary system services.

If the hardware detection module determines that the system does not support GPU passthrough (no IOMMU, no compatible GPU), the installer does not fail. It completes normally, and the user gets a fully functional Linux desktop with Wine/Proton compatibility. The VM features are simply not available, and the NeuronVM Manager displays an explanation of why and what hardware would be needed to enable them.

After first boot, a onboarding wizard runs exactly once. It welcomes the user, explains what NeuronOS can do in plain language, and asks one functional question: "Do you plan to use Windows-only software like Adobe Creative Suite, AutoCAD, or Microsoft Office? If yes, we will prepare compatibility in the background." If the user says yes, the system begins downloading the Windows VM template (approximately 15-20 GB) in the background while the user starts using their computer. By the time they go to install their first Windows application, the VM infrastructure is ready. If the user says no or is unsure, the download does not happen, and they can trigger it later from NeuronVM Manager if they change their mind.

---

## 4. Technology Stack

This section describes the technologies NeuronOS is built on, what role each plays, and why it was chosen.

### 4.1 Base Operating System: Arch Linux

Arch Linux is a minimal, rolling-release Linux distribution that provides the kernel, the package manager (pacman), the init system (systemd), and a repository of over 14,000 official packages plus over 100,000 community-maintained packages in the Arch User Repository (AUR).

Arch was chosen over alternatives (Ubuntu, Fedora, Debian) for three reasons. First, Arch always ships the latest stable Linux kernel, which means the best possible hardware support for new GPUs and CPUs. This is critical because GPU passthrough depends on kernel-level VFIO and IOMMU support, and newer hardware often requires newer kernel versions. Ubuntu LTS kernels lag by 6-12 months; Fedora by 3-6 months. For a product that needs to support the latest NVIDIA and AMD graphics cards on launch day, kernel freshness is non-negotiable. Second, Arch's minimal base (approximately 380 MB of RAM at idle with no desktop environment) gives NeuronOS the maximum possible headroom for VM resource allocation. Every megabyte of RAM the host OS does not use is a megabyte that can be allocated to a Windows VM running Photoshop or a game. Third, Arch provides Archiso, a purpose-built tool for creating custom distribution ISOs, which is significantly simpler to work with than Ubuntu's live-build or Fedora's Koji.

The rolling-release nature of Arch means that packages update continuously rather than in large version jumps. This is a stability concern that NeuronOS mitigates through a staged update system: all upstream Arch package updates are pulled into a NeuronOS staging repository, tested internally for two weeks across a matrix of supported hardware configurations, and only then released to NeuronOS users. Users also have BTRFS snapshots integrated into their boot menu, so if an update causes problems, they can boot into their previous system state without any technical knowledge — they simply select a previous snapshot from the boot screen.

### 4.2 Desktop Environment: KDE Plasma 6

KDE Plasma 6 is the graphical desktop environment — the taskbar, the application launcher, the window manager, the system settings panel, and the visual layer that users interact with every day.

KDE Plasma was chosen over GNOME (the other major Linux desktop environment) because KDE's default interface follows the same conventions as Windows: a taskbar at the bottom of the screen, an application menu in the lower-left corner, a system tray in the lower-right, and window management through minimize/maximize/close buttons in the title bar. GNOME follows a different design philosophy modeled after macOS and mobile interfaces, where there is no persistent taskbar and application switching is done through a full-screen overview. Making GNOME look and behave like Windows requires third-party extensions that break on GNOME version updates. KDE can be themed to match Windows conventions without any third-party dependencies, using only built-in configuration options that are guaranteed to survive updates.

KDE Plasma also uses the Qt framework for its applications, which is the same framework NeuronVM Manager is built with. This means NeuronOS's custom applications look and feel native within the desktop environment, sharing the same visual style, widget library, and interaction patterns.

### 4.3 Virtualization: QEMU/KVM with libvirt

QEMU is an open-source machine emulator and virtualizer. KVM (Kernel-based Virtual Machine) is a Linux kernel module that allows QEMU to use hardware-assisted virtualization for near-native performance. Together, QEMU/KVM is the standard Linux virtualization stack, used in production by cloud providers (AWS, Google Cloud, Azure's Linux hosts), enterprise environments, and the open-source community.

libvirt is a management layer that sits on top of QEMU/KVM and provides a stable API for creating, configuring, starting, stopping, and monitoring virtual machines. NeuronVM Manager communicates with the virtualization layer entirely through libvirt's Python bindings. This means NeuronVM Manager does not need to construct QEMU command lines directly or manage QEMU processes — libvirt handles all of that.

OVMF (Open Virtual Machine Firmware) provides UEFI firmware for virtual machines, which is required for modern Windows installations and for GPU passthrough to work correctly. It is a standard component of the QEMU/KVM stack.

### 4.4 GPU Passthrough: VFIO

VFIO (Virtual Function I/O) is a Linux kernel framework that allows a physical hardware device (in our case, a GPU) to be detached from the Linux host and given directly to a virtual machine. The virtual machine then has unmediated, direct access to the GPU hardware. There is no emulation layer, no translation overhead, and no performance loss beyond approximately 1-3%.

VFIO works in conjunction with the IOMMU (Input-Output Memory Management Unit), a CPU feature that provides hardware-level memory isolation between devices. The IOMMU ensures that the GPU's memory transactions are isolated to the virtual machine's memory space, preventing the VM from accessing host memory and vice versa.

The VFIO configuration process involves identifying the PCI bus addresses and device IDs of the GPU to be passed through, binding that GPU to the VFIO kernel driver instead of its normal graphics driver (nvidia, amdgpu, etc.), and telling the bootloader to enable IOMMU at boot time. NeuronOS's hardware detection system automates this entire process.

### 4.5 VM Display: Looking Glass

Looking Glass is an open-source application that captures the framebuffer of a virtual machine through shared memory and displays it in a window on the host system with extremely low latency. In the dual-GPU configuration, Looking Glass is the mechanism by which the user sees the VM's display output on their Linux desktop.

Looking Glass communicates between the VM and the host through a shared memory file (`/dev/shm/looking-glass`). The VM side runs a small host application that captures the GPU's framebuffer and writes it to shared memory. The Linux side runs the Looking Glass client, which reads from shared memory and renders the framebuffer in a window. Because this communication happens through memory rather than over a network, latency is negligible.

Looking Glass supports borderless window mode, automatic window resizing to match the VM's resolution, keyboard and mouse input capture and forwarding, and clipboard sharing between host and VM. The NeuronOS Looking Glass wrapper builds on these capabilities to provide the seamless application-window experience described in Section 3.2.

### 4.6 VM Audio: Scream

Scream is an open-source virtual audio driver for Windows that sends audio from a Windows VM to the Linux host over a virtual network connection. On the Linux host, a Scream receiver captures the audio stream and plays it through PipeWire (the Linux audio system). This allows audio from VM applications (a video playing in Premiere Pro, a game's soundtrack, a Zoom call running in the VM) to play through the same speakers and audio configuration as native Linux applications, with mixing handled by PipeWire.

### 4.7 Installer: Calamares

Calamares is an open-source, modular installer framework used by many Linux distributions (EndeavourOS, Manjaro, Garuda, KDE Neon, and others). It provides a graphical installer with a step-by-step wizard interface and supports custom modules written in Python or C++.

NeuronOS extends Calamares with four custom modules: a hardware detection module that identifies GPUs and passthrough capability, a VFIO configuration module that writes the necessary system files, a VM setup module that handles the "Do you need Windows applications?" question and queues the VM template download, and a branding module that provides NeuronOS-specific visual design for the installer screens.

### 4.8 Filesystem and Rollback: BTRFS with Snapper

NeuronOS uses the BTRFS filesystem, which supports copy-on-write snapshots. Before every system update, a snapshot of the current system state is automatically created. These snapshots are registered with the GRUB bootloader through grub-btrfs, which means they appear as selectable entries in the boot menu. If a system update causes problems, the user can reboot, select a previous snapshot from the boot menu, and immediately return to a known-working state. This provides a safety net comparable to the atomic rollback capability of immutable distributions, but on a mutable system that allows the deep system-level modifications NeuronOS requires for GPU passthrough configuration.

---

## 5. What We Are NOT Building

It is equally important to understand what is outside the scope of this engineering effort. NeuronOS does not need to innovate in any of the following areas, because mature solutions already exist.

We are not building a web browser. Firefox, Chromium, and other browsers are available as standard packages and work perfectly on every Linux distribution. NeuronOS installs whichever browser the user chooses.

We are not building an office suite. LibreOffice, OnlyOffice, and other office suites are mature Linux applications. Users install them the same way they install any application.

We are not building a gaming platform. Steam, Heroic Games Launcher, and Lutris are the established Linux gaming tools. Proton is maintained by Valve with a team of full-time engineers and a multi-million-dollar budget. NeuronOS ensures these tools are available and easy to install, but does not modify, fork, or maintain them.

We are not building a theme or visual design system from scratch. KDE Plasma has an extensive theming infrastructure with hundreds of existing themes. NeuronOS applies and configures an existing theme to achieve the desired visual identity.

We are not building a package manager. Arch Linux's pacman and Flatpak are mature, proven package management systems. NeuronOS uses them as-is.

We are not building a kernel. Arch Linux provides the standard Linux kernel, and CachyOS provides performance-optimized kernel builds with the BORE scheduler and LTO compilation that we can use.

Every hour of engineering time spent on these solved problems is an hour not spent on the six core challenges described in Section 3. The six core challenges are the entire product. Everything else is configuration.

---

## 6. How We Get Started

Development begins with a proof-of-concept phase that validates the core technical assumptions before any product code is written. This phase is the go/no-go gate for the entire project. If the proof of concept succeeds, all subsequent work is execution. If it fails, we need to understand why and adjust before investing further.

### 6.1 Proof of Concept (Weeks 1-2)

The proof of concept is a manual, hands-on exercise performed on physical hardware. The goal is to verify that GPU passthrough works on representative hardware and that Looking Glass delivers acceptable display quality and latency.

The team sets up an Arch Linux installation on a development machine that has both an integrated GPU and a discrete GPU. Following the Arch Wiki's PCI passthrough guide, the team manually configures IOMMU, VFIO device binding, and a Windows 11 VM with GPU passthrough. Looking Glass is installed and configured in borderless mode. A GPU-intensive Windows application (Adobe Photoshop trial, Blender Windows build, or a demanding game) is run inside the VM, and its performance is measured against the same application running on a bare-metal Windows installation on the same hardware.

The success criteria are clear. GPU passthrough must work and be stable (no crashes, no kernel panics, no display corruption during a sustained one-hour workload). Application performance in the VM must be within 5% of native Windows performance for GPU-bound tasks. Looking Glass must display the VM output at the host's native resolution with no perceptible latency during normal application use. The single-GPU switching path must also be tested on a system with only one GPU, verifying that the GPU unbind/rebind cycle completes reliably and the Linux desktop recovers correctly.

Every command run during the proof of concept must be documented, because these commands become the specification for the automated hardware detection and VFIO configuration systems built in subsequent phases.

### 6.2 Development Environment Setup (Week 2)

In parallel with the proof of concept, the development environment and project infrastructure are established. This includes the GitHub organization with repositories for each major component (the Archiso configuration, the NeuronVM Manager, the Calamares modules, the Looking Glass wrapper, and the hardware detection system), the CI/CD pipeline for building NeuronOS ISOs automatically from the Archiso configuration, and the internal hardware test matrix (a list of target hardware configurations that all releases must be tested against before shipping).

The ISO build pipeline uses Archiso to produce bootable ISO images from the NeuronOS configuration. Developers should be able to push a change to the Archiso configuration repository and receive a built ISO within 30 minutes through automated CI, ready to be tested in a VM or on physical hardware.

---

## 7. Feature Milestones

The following milestones represent the sequential gates that NeuronOS must pass through before it is ready for public release. Each milestone builds on the previous one. The milestones are ordered by dependency — later milestones cannot begin until earlier ones are complete, with some limited parallelization where noted. Time estimates assume a team of three to four engineers working full-time.

### Milestone 1: Bootable ISO with Automatic VFIO Configuration

**Target: Weeks 3-8 (6 weeks)**

This milestone produces a bootable NeuronOS ISO that installs Arch Linux with KDE Plasma, detects the system's GPU hardware, and automatically configures VFIO passthrough without any user intervention.

The work includes creating the Archiso configuration with the NeuronOS package list (base system, KDE Plasma, QEMU/KVM, libvirt, OVMF, Looking Glass, Scream, and supporting tools), building the hardware detection system as a Python application that identifies all GPUs, determines the optimal passthrough configuration, and generates the appropriate system files, building the VFIO configuration system that writes GRUB kernel parameters, modprobe configuration, and initramfs hooks based on the hardware detection output, integrating the hardware detection and VFIO configuration into Calamares as custom installer modules, and setting up the BTRFS filesystem with snapper for automatic pre-update snapshots with GRUB integration.

The milestone is complete when a developer can boot the NeuronOS ISO on a machine with an iGPU and a discrete GPU, click through a 5-step installer, reboot, and find that the discrete GPU is automatically bound to VFIO and ready for VM passthrough — without having edited any configuration files or opened a terminal.

### Milestone 2: VM Launch with Looking Glass Borderless Display

**Target: Weeks 9-14 (6 weeks)**

This milestone produces a functional NeuronVM Manager application that can launch a Windows VM with GPU passthrough and display its output through Looking Glass in borderless mode on the Linux desktop.

The work includes building the NeuronVM Manager as a Qt6/PySide6 desktop application with a main window that shows installed VM applications and provides VM management controls, building the VM lifecycle manager that handles starting, stopping, suspending, and resource-allocating VMs through libvirt, building the Looking Glass wrapper that launches the Looking Glass client in borderless mode with the correct window geometry and input configuration, building the single-GPU switching system for systems without a secondary GPU (display manager stop, GPU driver unload, VFIO bind, VM launch, and the reverse process on VM shutdown), creating the pre-built Windows 11 VM template (a minimal Windows installation with VirtIO drivers, the Looking Glass host application, and the Scream audio driver pre-installed, with telemetry disabled and bloatware removed), and building the VM audio pipeline using Scream and PipeWire so that VM audio plays through the host's speakers and responds to the host's volume controls.

The milestone is complete when a developer can open NeuronVM Manager, click a button to launch the Windows VM, see the Windows desktop appear in a borderless window on their Linux desktop with no visible VM chrome, hear audio from Windows applications through their speakers, and shut down the VM cleanly with the Linux desktop returning to its previous state.

### Milestone 3: Seamless Application Installation and Launch

**Target: Weeks 15-20 (6 weeks)**

This milestone makes the VM layer invisible to the user. Instead of interacting with a VM, the user installs and launches Windows applications as if they were native.

The work includes building the download monitor that watches the user's Downloads directory for Windows executables and macOS disk images using inotify, and presents a prompt offering to install the application, building the application installer that mounts a downloaded Windows installer into the running VM (or starts the VM if it is not running), allowing the user to complete the installation process through the Looking Glass window, building the desktop entry creator that generates Linux desktop shortcuts for applications installed in the VM so that clicking the shortcut automatically boots the VM, launches the application, and opens Looking Glass in borderless mode, building the application router with its curated database of several hundred applications and their recommended execution paths (native, Wine, or VM), and building the NeuronStore frontend — a graphical application catalog where users can browse and install applications, with the routing logic transparently handling whether each application is installed natively, through Wine, or in a VM.

The milestone is complete when a user can download Photoshop's Windows installer in their browser, be prompted by NeuronOS to install it, click through the Photoshop installer inside a Looking Glass window, and then find an "Adobe Photoshop" icon on their desktop that, when clicked, boots the VM (if not running), launches Photoshop, and displays it in a borderless window — all without the user seeing a Windows desktop or knowing a VM is involved.

### Milestone 4: Multi-Application Simultaneous Workflow

**Target: Weeks 21-24 (4 weeks)**

This milestone ensures that the system works under realistic professional workloads where multiple applications — some native, some in VMs — run simultaneously.

The work includes implementing dynamic resource allocation so the VM's CPU and RAM allocation adjusts based on the user's current workload and available system resources, implementing shared folder access between the Linux host and the Windows VM so files can be exchanged between native and VM applications (the user saves a file in Photoshop in the VM and opens it in GIMP on Linux without manually transferring anything), implementing clipboard sharing so the user can copy text or images in a native Linux application and paste them into a VM application and vice versa (Looking Glass provides basic clipboard sharing that must be extended and made reliable), and testing and optimizing the system under sustained multi-application workloads — for example, DaVinci Resolve running natively on Linux performing a color grade while Premiere Pro runs in the VM performing an edit, with the user switching between them, sharing files, and using both audio outputs simultaneously without crackling, stuttering, or resource starvation.

The milestone is complete when a professional user can run their real production workflow across native and VM applications simultaneously, with acceptable performance, reliable file sharing, and no user-facing complexity.

### Milestone 5: First-Boot Experience and Onboarding

**Target: Weeks 25-28 (4 weeks, can partially overlap with Milestone 4)**

This milestone builds the complete first-time user experience, from installation through the first hour of use.

The work includes polishing the Calamares installer to its final visual design and interaction flow (5 steps maximum for the user), building the first-boot onboarding wizard that runs after the initial reboot (welcome screen, "Do you need Windows applications?" question, background VM template download), building the migration assistant that helps users transfer files, bookmarks, and settings from an existing Windows or macOS installation (either from a mounted partition on the same machine or from a network share), writing all user-facing text, notifications, and error messages in clear, non-technical language (this includes the single-GPU switching notifications, the VM download progress indicators, and the hardware compatibility messages), and testing the end-to-end flow with non-technical users — people who have never used Linux — to identify and fix usability problems.

The milestone is complete when a non-technical person can install NeuronOS from a USB drive, complete the onboarding process, install a Windows application, and begin using it, all without assistance and without opening a terminal.

### Milestone 6: Hardware Compatibility Testing and Stability

**Target: Weeks 29-36 (8 weeks)**

This milestone validates NeuronOS across a broad range of hardware and ensures stability under sustained use.

The work includes testing on a minimum of 50 hardware configurations spanning Intel and AMD CPUs (10th-14th gen Intel, Ryzen 3000-7000 AMD), NVIDIA and AMD discrete GPUs (GTX 1650 through RTX 4090, RX 6600 through RX 7900 XTX), laptop and desktop form factors from multiple manufacturers (Dell, HP, Lenovo, ASUS, Framework, System76), and systems with varying RAM (8GB through 128GB), building the automated test suite that verifies hardware detection correctness, VFIO configuration correctness, VM boot/shutdown reliability, Looking Glass display quality, and single-GPU switching reliability on each tested configuration, documenting all known hardware compatibility issues and workarounds in a user-facing compatibility database that the hardware detection system references, running extended stability tests (72-hour continuous VM operation, repeated VM start/stop cycles, update/rollback cycles) to identify and fix reliability issues, and building the staged update system that pulls upstream Arch packages into a NeuronOS staging repository, runs automated tests, and releases validated packages to users.

The milestone is complete when NeuronOS installs, configures, and operates correctly on at least 90% of tested hardware configurations, and the system has been stable under sustained use testing for a minimum of two weeks without a critical failure.

### Milestone 7: Beta Program and Public Release Preparation

**Target: Weeks 37-44 (8 weeks)**

This milestone moves from internal testing to real-world validation with external users.

The work includes recruiting and onboarding 500-1,000 beta testers with diverse hardware and use cases (light users, gamers, creative professionals, software developers), building the feedback and bug reporting system that allows beta testers to submit reports directly from NeuronOS with automatic system information collection, triaging and fixing bugs reported during beta testing with priority given to issues that block core functionality (hardware detection failures, VM launch failures, display or audio problems), writing user documentation covering installation, first-time setup, application installation, troubleshooting, and hardware compatibility, and preparing the NeuronOS website, download infrastructure, and any release marketing materials.

The milestone is complete when the beta program has run for a minimum of four weeks, critical bugs identified during beta have been resolved, and the team has confidence that the product is stable and usable for its target audience.

---

## 8. Key Engineering Principles

There are several principles that must guide all engineering decisions throughout the project.

**No terminal exposure.** Every feature, every configuration option, every error recovery path must have a graphical interface. If a user needs to open a terminal to accomplish something, that is a bug. The terminal may exist for advanced users who want it, but it must never be required.

**Fail gracefully, not silently.** When something does not work — hardware is incompatible, a VM fails to start, a GPU driver fails to load — the system must tell the user what happened in plain language, what their options are, and offer to help. It must never display a cryptic error code, a kernel log, or a stack trace. It must never fail silently, leaving the user confused about why a feature is not working.

**The VM is invisible.** At no point in normal operation should the user be aware they are interacting with a virtual machine. The term "virtual machine" should not appear in any user-facing interface except in advanced settings. Users interact with "Windows applications" and "macOS applications," not with VMs.

**Prioritize the hard problems.** The engineering team should resist the temptation to spend time on visual polish, bundled application selection, or other commodity work before the six core challenges (Section 3) are solved. A beautiful desktop with broken GPU passthrough is worthless. A rough-looking desktop with flawless GPU passthrough is a viable product.

---

## 9. Repository Structure

The NeuronOS project is organized across the following repositories. Each repository has a clear scope and a clear owner.

**neuronos-iso** contains the Archiso configuration, the package list, the filesystem customizations, and the CI pipeline that produces bootable ISO images. This is the "definition" of the operating system — the complete specification of what NeuronOS contains.

**neuronos-vm-manager** contains the NeuronVM Manager application: the Qt6/PySide6 GUI, the VM lifecycle manager, the Looking Glass wrapper, the download monitor, the desktop entry creator, the application router and its database, and the NeuronStore frontend. This is the largest custom codebase and the core of the product.

**neuronos-hardware** contains the hardware detection system and the VFIO configuration generator. This code runs during installation (as a Calamares module) and at boot time (as a systemd service). It also contains the hardware compatibility database.

**neuronos-installer** contains the Calamares fork with NeuronOS's custom modules (hardware detection, VFIO configuration, VM setup wizard, branding), the Calamares configuration files, and the installer's visual assets.

**neuronos-single-gpu** contains the single-GPU switching system: the scripts that stop the display manager, unload GPU drivers, bind VFIO, launch the VM, and reverse the process on shutdown. This is isolated in its own repository because it is the most hardware-sensitive and stability-critical component.

**neuronos-docs** contains all user-facing documentation, the hardware compatibility list, and the engineering team's internal documentation (architecture decisions, testing procedures, release checklists).

---

## 10. Summary

NeuronOS is an integration product. Its value lies not in any single technology, but in the assembly of proven, existing technologies into a seamless experience that hides extraordinary complexity behind ordinary interactions. A user clicks an icon, and an application appears. They do not know that behind that click, a virtual machine booted, a GPU was passed through a hardware isolation boundary, a shared-memory framebuffer was captured and rendered in a borderless window, and audio was routed through a virtual network driver. They do not need to know. They just need it to work, every time, on their hardware, without surprises.

That is what we are building. The six core challenges in Section 3 are the entire product. The milestones in Section 7 are the path to delivering it. Everything else is details.
