"""
Command-line interface for NeuronOS hardware detection.
"""

import argparse
import json
import sys

from neuron_hw.detect import build_hardware_profile
from neuron_hw.vfio_config import write_configs, generate_grub_params


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="NeuronOS Hardware Detection System"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # detect command
    detect_parser = subparsers.add_parser(
        "detect", help="Detect hardware and show configuration"
    )
    detect_parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )

    # configure command
    config_parser = subparsers.add_parser(
        "configure", help="Write VFIO configuration files"
    )
    config_parser.add_argument(
        "--target", default="/", help="Target filesystem root (default: /)"
    )
    config_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be written"
    )

    # grub-params command
    grub_parser = subparsers.add_parser(
        "grub-params", help="Output GRUB kernel parameters"
    )

    args = parser.parse_args()

    if args.command == "detect":
        cmd_detect(args)
    elif args.command == "configure":
        cmd_configure(args)
    elif args.command == "grub-params":
        cmd_grub_params(args)
    else:
        parser.print_help()
        sys.exit(1)


def cmd_detect(args):
    """Run hardware detection and display results."""
    profile = build_hardware_profile()

    if args.json:
        print(json.dumps(profile.to_dict(), indent=2))
        return

    print("=" * 60)
    print("NeuronOS Hardware Detection Report")
    print("=" * 60)
    print()

    print(f"CPU Vendor: {profile.cpu_vendor or 'Unknown'}")
    print(f"IOMMU Enabled: {'Yes' if profile.iommu_enabled else 'No'}")
    print(f"Passthrough Capability: {profile.capability.value}")
    print()

    print("Detected GPUs:")
    for i, gpu in enumerate(profile.gpus, 1):
        print(f"  {i}. {gpu.name}")
        print(f"     Type: {gpu.gpu_type.value}")
        print(f"     Vendor: {gpu.vendor.value}")
        print(f"     PCI Address: {gpu.primary_device.address}")
        if gpu.audio_device:
            print(f"     Audio Device: {gpu.audio_device.address}")
        print()

    if profile.host_gpu:
        print(f"Host GPU (stays with Linux): {profile.host_gpu.name}")
    if profile.passthrough_gpu:
        print(f"Passthrough GPU (goes to VM): {profile.passthrough_gpu.name}")
    print()

    if profile.warnings:
        print("Warnings:")
        for warning in profile.warnings:
            print(f"  ! {warning}")
        print()


def cmd_configure(args):
    """Write VFIO configuration files."""
    profile = build_hardware_profile()

    if args.dry_run:
        print("Dry run - would write the following configurations:")
        print()
        print("GRUB Parameters:")
        print(f"  {generate_grub_params(profile)}")
        print()
        print(f"Target directory: {args.target}")
        return

    try:
        write_configs(profile, target_root=args.target)
        print(f"Configuration written to {args.target}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_grub_params(args):
    """Output GRUB kernel parameters."""
    profile = build_hardware_profile()
    print(generate_grub_params(profile))


if __name__ == "__main__":
    main()
