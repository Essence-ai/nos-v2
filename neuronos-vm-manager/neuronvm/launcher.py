"""
Application launcher for NeuronOS.

This module is the entry point for launching applications through
NeuronOS, whether they run natively, via Wine, or in the VM.
"""

import argparse
import logging
import sys
import time

from neuronvm.lifecycle import VMLifecycleManager
from neuronvm.looking_glass import LookingGlassWrapper
from neuronvm.app_router import AppRouter, ExecutionPath
from neuronvm.config import get_config

logger = logging.getLogger(__name__)


def main():
    """Main entry point for neuronvm-launch."""
    parser = argparse.ArgumentParser(
        description="Launch applications through NeuronOS"
    )
    parser.add_argument(
        "app_id",
        help="Application ID or executable path"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--force-vm",
        action="store_true",
        help="Force VM execution even if Wine is suggested"
    )
    parser.add_argument(
        "--force-wine",
        action="store_true",
        help="Force Wine execution"
    )

    args = parser.parse_args()

    # Set up logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s"
    )

    try:
        launch_app(
            args.app_id,
            force_vm=args.force_vm,
            force_wine=args.force_wine
        )
    except Exception as e:
        logger.error(f"Failed to launch application: {e}")
        sys.exit(1)


def launch_app(
    app_id: str,
    force_vm: bool = False,
    force_wine: bool = False
):
    """
    Launch an application.

    Args:
        app_id: Application ID or executable path
        force_vm: Force VM execution
        force_wine: Force Wine execution
    """
    config = get_config()
    router = AppRouter()

    # Determine execution path
    path, app_entry = router.route_executable(app_id)

    if force_vm:
        path = ExecutionPath.VM
    elif force_wine:
        path = ExecutionPath.WINE

    app_name = app_entry.get("name", app_id) if app_entry else app_id

    logger.info(f"Launching {app_name} via {path.value}")

    if path == ExecutionPath.NATIVE:
        launch_native(app_id, app_entry)
    elif path == ExecutionPath.WINE:
        launch_wine(app_id, app_entry)
    elif path == ExecutionPath.PROTON:
        launch_proton(app_id, app_entry)
    elif path == ExecutionPath.VM:
        launch_vm(app_id, app_entry, config)
    else:
        raise RuntimeError(f"Unknown execution path: {path}")


def launch_native(app_id: str, app_entry: dict = None):
    """Launch a native Linux application."""
    import subprocess

    if app_entry and app_entry.get("package"):
        # Launch via package name
        package = app_entry["package"]
        # Try common launchers
        for cmd in [package, package.lower(), package.replace("-", "")]:
            try:
                subprocess.Popen([cmd])
                return
            except FileNotFoundError:
                continue

    # Try launching directly
    subprocess.Popen([app_id])


def launch_wine(app_id: str, app_entry: dict = None):
    """Launch an application via Wine."""
    import subprocess

    wine_cmd = ["wine"]

    if app_entry:
        wine_prefix = app_entry.get("wine_prefix")
        if wine_prefix:
            import os
            os.environ["WINEPREFIX"] = f"~/.wine/{wine_prefix}"

        wine_version = app_entry.get("wine_version")
        if wine_version == "wine-staging":
            wine_cmd = ["wine-staging"]

    wine_cmd.append(app_id)
    subprocess.Popen(wine_cmd)


def launch_proton(app_id: str, app_entry: dict = None):
    """Launch an application via Proton (Steam)."""
    import subprocess

    # For Proton apps, we typically launch through Steam
    logger.info("Proton apps should be launched through Steam")

    # Try to open Steam with the game
    subprocess.Popen(["steam", f"steam://rungameid/{app_id}"])


def launch_vm(app_id: str, app_entry: dict, config):
    """Launch an application in the Windows VM."""
    manager = VMLifecycleManager()
    lg_wrapper = LookingGlassWrapper()

    app_name = app_entry.get("name", app_id) if app_entry else app_id

    # Register the app with the lifecycle manager
    manager.register_app(app_name)

    try:
        # Start VM if not running
        if not manager.is_running():
            logger.info("Starting VM...")
            if not manager.start_vm():
                raise RuntimeError("Failed to start VM")

            # Wait for VM to be fully booted
            logger.info("Waiting for VM to be ready...")
            time.sleep(10)  # TODO: Proper readiness check

        # Launch Looking Glass
        logger.info("Launching Looking Glass...")
        lg_wrapper.launch(
            app_name=app_name,
            width=config.looking_glass.default_width,
            height=config.looking_glass.default_height,
            borderless=config.looking_glass.borderless,
            capture_input=config.looking_glass.capture_input,
            escape_key=config.looking_glass.escape_key,
        )

        # Set up exit callback
        def on_lg_exit(return_code):
            logger.info(f"Looking Glass exited with code {return_code}")
            manager.unregister_app(app_name)

        lg_wrapper.add_exit_callback(on_lg_exit)

        # TODO: Launch the actual application inside the VM
        # This would require communication with the VM via QEMU Guest Agent
        # or a custom agent running inside Windows

        logger.info(f"Application {app_name} launched in VM")

    except Exception as e:
        manager.unregister_app(app_name)
        raise


if __name__ == "__main__":
    main()
