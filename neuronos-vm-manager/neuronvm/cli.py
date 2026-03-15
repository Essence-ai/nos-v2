"""
Command-line interface for NeuronOS VM Manager.
"""

import argparse
import logging
import sys

from neuronvm.lifecycle import VMLifecycleManager
from neuronvm.looking_glass import LookingGlassWrapper
from neuronvm.app_router import AppRouter


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="NeuronOS VM Manager CLI"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # status command
    subparsers.add_parser("status", help="Show VM status")

    # start command
    subparsers.add_parser("start", help="Start the VM")

    # stop command
    stop_parser = subparsers.add_parser("stop", help="Stop the VM")
    stop_parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="Force stop (power off)"
    )

    # pause/resume commands
    subparsers.add_parser("pause", help="Pause the VM")
    subparsers.add_parser("resume", help="Resume the VM")

    # route command
    route_parser = subparsers.add_parser("route", help="Determine execution path for an app")
    route_parser.add_argument("executable", help="Path to executable or app name")

    # search command
    search_parser = subparsers.add_parser("search", help="Search application database")
    search_parser.add_argument("query", help="Search query")

    # resources command
    subparsers.add_parser("resources", help="Show resource allocation")

    args = parser.parse_args()

    # Set up logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s"
    )

    if args.command == "status":
        cmd_status()
    elif args.command == "start":
        cmd_start()
    elif args.command == "stop":
        cmd_stop(args.force)
    elif args.command == "pause":
        cmd_pause()
    elif args.command == "resume":
        cmd_resume()
    elif args.command == "route":
        cmd_route(args.executable)
    elif args.command == "search":
        cmd_search(args.query)
    elif args.command == "resources":
        cmd_resources()
    else:
        parser.print_help()
        sys.exit(1)


def cmd_status():
    """Show VM status."""
    manager = VMLifecycleManager()

    print("NeuronOS VM Status")
    print("=" * 40)

    if manager.is_running():
        print("State: Running")
        info = manager.get_vm_info()
        if info:
            print(f"Memory: {info['memory_kb'] // 1024} MB")
            print(f"vCPUs: {info['vcpus']}")
    elif manager.is_paused():
        print("State: Paused")
    else:
        print("State: Stopped")

    print(f"Capability: {manager.capability}")

    apps = manager.get_active_apps()
    if apps:
        print(f"Active apps: {', '.join(apps)}")
    else:
        print("Active apps: None")


def cmd_start():
    """Start the VM."""
    manager = VMLifecycleManager()

    if manager.is_running():
        print("VM is already running")
        return

    print("Starting VM...")
    try:
        if manager.start_vm():
            print("VM started successfully")
        else:
            print("Failed to start VM", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_stop(force: bool = False):
    """Stop the VM."""
    manager = VMLifecycleManager()

    if not manager.is_running():
        print("VM is not running")
        return

    print("Stopping VM..." + (" (force)" if force else ""))
    try:
        manager.stop_vm(force=force)
        print("VM stopped")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_pause():
    """Pause the VM."""
    manager = VMLifecycleManager()

    if not manager.is_running():
        print("VM is not running")
        return

    print("Pausing VM...")
    try:
        manager.pause_vm()
        print("VM paused")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_resume():
    """Resume the VM."""
    manager = VMLifecycleManager()

    if not manager.is_paused():
        print("VM is not paused")
        return

    print("Resuming VM...")
    try:
        manager.resume_vm()
        print("VM resumed")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_route(executable: str):
    """Determine execution path for an application."""
    router = AppRouter()

    path, app_entry = router.route_executable(executable)

    print(f"Executable: {executable}")
    print(f"Execution path: {path.value}")

    if app_entry:
        print(f"Matched application: {app_entry.get('name')}")
        print(f"Category: {app_entry.get('category', 'Unknown')}")
        if app_entry.get("notes"):
            print(f"Notes: {app_entry['notes']}")

        # Show native alternatives for VM apps
        if path.value == "vm":
            alternatives = router.get_native_alternatives(app_entry.get("name", ""))
            if alternatives:
                print("\nNative alternatives:")
                for alt in alternatives:
                    print(f"  - {alt.get('name')}")


def cmd_search(query: str):
    """Search the application database."""
    router = AppRouter()

    results = router.search(query)

    if not results:
        print(f"No applications found matching '{query}'")
        return

    print(f"Found {len(results)} application(s):")
    print()

    for app in results:
        print(f"  {app.get('name')}")
        print(f"    Category: {app.get('category', 'Unknown')}")
        print(f"    Path: {app.get('path', 'unknown')}")
        if app.get("package"):
            print(f"    Package: {app['package']}")
        print()


def cmd_resources():
    """Show resource allocation."""
    manager = VMLifecycleManager()

    resources = manager.get_resource_allocation()

    print("System Resources")
    print("=" * 40)
    print(f"Total RAM: {resources['total_ram_mb']} MB")
    print(f"Total CPU cores: {resources['total_cores']}")
    print()
    print("Allocation:")
    print(f"  Host RAM: {resources['host_ram_mb']} MB")
    print(f"  Host cores: {resources['host_cores']}")
    print(f"  VM RAM: {resources['ram_mb']} MB")
    print(f"  VM cores: {resources['cores']}")


if __name__ == "__main__":
    main()
