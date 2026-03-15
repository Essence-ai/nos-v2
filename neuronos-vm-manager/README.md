# NeuronOS VM Manager

The core VM management application for NeuronOS. Provides seamless Windows application integration through GPU passthrough virtualization.

## Overview

NeuronOS VM Manager:
- Manages the Windows VM lifecycle (start, stop, pause, resume)
- Routes applications to their optimal execution path (native, Wine, or VM)
- Integrates Looking Glass for seamless display
- Monitors downloads for new Windows executables
- Creates desktop entries for installed VM applications

## Installation

```bash
# Install with GUI support
pip install -e ".[gui]"

# Install with download monitoring
pip install -e ".[monitor]"

# Install all extras
pip install -e ".[gui,monitor,dev]"
```

## Dependencies

- Python 3.10+
- libvirt-python
- PyYAML
- PySide6 (for GUI)
- Looking Glass client
- QEMU/KVM with GPU passthrough configured

## Command Line Usage

```bash
# Show VM status
neuronvm status

# Start the VM
neuronvm start

# Stop the VM
neuronvm stop
neuronvm stop --force  # Force power off

# Pause/resume
neuronvm pause
neuronvm resume

# Route an application
neuronvm route "Photoshop_Setup.exe"

# Search application database
neuronvm search "video editor"

# Show resource allocation
neuronvm resources
```

## Launching Applications

```bash
# Launch an application by ID
neuronvm-launch "Adobe Photoshop"

# Launch with verbose output
neuronvm-launch -v "Adobe Premiere Pro"

# Force VM execution
neuronvm-launch --force-vm myapp.exe

# Force Wine execution
neuronvm-launch --force-wine myapp.exe
```

## Python API

```python
from neuronvm import VMLifecycleManager, AppRouter, LookingGlassWrapper

# VM Lifecycle
manager = VMLifecycleManager()
manager.start_vm()
print(f"VM running: {manager.is_running()}")
manager.stop_vm()

# Application Routing
router = AppRouter()
path, app_entry = router.route_executable("Photoshop_Setup.exe")
print(f"Execution path: {path.value}")

# Looking Glass
lg = LookingGlassWrapper()
lg.launch(app_name="Adobe Photoshop", width=1920, height=1080)
```

## Configuration

Configuration is stored in `~/.config/neuronos/config.json`:

```json
{
  "vm": {
    "domain_name": "win11-neuron",
    "ram_mb": 8192,
    "cpu_cores": 4,
    "auto_resource_allocation": true,
    "grace_period_seconds": 300
  },
  "looking_glass": {
    "shm_path": "/dev/shm/looking-glass",
    "shm_size_mb": 128,
    "borderless": true,
    "escape_key": "KEY_RIGHTCTRL"
  }
}
```

## Application Database

The application routing database is stored in `data/app_database.yaml`. It contains:

- Known applications and their optimal execution paths
- Filename patterns for automatic detection
- Native alternatives for VM-required apps
- Category classifications

## Architecture

```
neuronvm/
├── lifecycle.py       # VM start/stop/suspend
├── looking_glass.py   # Looking Glass wrapper
├── app_router.py      # Application routing
├── download_monitor.py # Download directory watcher
├── desktop_entry.py   # .desktop file generation
├── config.py          # Configuration management
├── cli.py             # Command-line interface
└── launcher.py        # Application launcher
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black neuronvm/

# Type checking
mypy neuronvm/
```
