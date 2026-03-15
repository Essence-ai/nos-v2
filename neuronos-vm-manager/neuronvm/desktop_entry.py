"""
Generate .desktop files for applications installed in the VM.

Creates entries that launch applications seamlessly through
the NeuronOS VM infrastructure.
"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class DesktopEntryGenerator:
    """
    Generates .desktop files for VM applications.

    These entries allow users to launch VM applications from
    their desktop/application menu like native apps.
    """

    DESKTOP_DIR = Path.home() / ".local" / "share" / "applications"
    ICONS_DIR = Path.home() / ".local" / "share" / "icons" / "neuronos"

    TEMPLATE = """[Desktop Entry]
Version=1.1
Type=Application
Name={name}
Comment={comment}
Exec=neuronvm-launch "{app_id}"
Icon={icon}
Terminal=false
Categories={categories}
Keywords={keywords}
StartupNotify=true
StartupWMClass={wm_class}
X-NeuronOS-AppId={app_id}
X-NeuronOS-ExecutionPath={execution_path}
"""

    def __init__(self):
        # Ensure directories exist
        self.DESKTOP_DIR.mkdir(parents=True, exist_ok=True)
        self.ICONS_DIR.mkdir(parents=True, exist_ok=True)

    def create_entry(
        self,
        app_id: str,
        name: str,
        execution_path: str = "vm",
        comment: Optional[str] = None,
        icon: Optional[str] = None,
        categories: Optional[list[str]] = None,
        keywords: Optional[list[str]] = None,
        wm_class: Optional[str] = None,
    ) -> Path:
        """
        Create a .desktop entry for a VM application.

        Args:
            app_id: Unique identifier for the application
            name: Display name
            execution_path: "vm", "wine", "native"
            comment: Description/tooltip
            icon: Icon name or path
            categories: XDG categories (e.g., ["Graphics", "Photography"])
            keywords: Search keywords
            wm_class: Window manager class for window matching

        Returns:
            Path to the created .desktop file
        """
        if comment is None:
            comment = f"{name} (via NeuronOS)"

        if icon is None:
            icon = "application-x-executable"

        if categories is None:
            categories = ["Application"]

        if keywords is None:
            keywords = [name.lower()]

        if wm_class is None:
            wm_class = name.replace(" ", "")

        content = self.TEMPLATE.format(
            name=name,
            comment=comment,
            app_id=app_id,
            icon=icon,
            categories=";".join(categories) + ";",
            keywords=";".join(keywords) + ";",
            wm_class=wm_class,
            execution_path=execution_path,
        )

        # Create safe filename
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in app_id)
        desktop_file = self.DESKTOP_DIR / f"neuronos-{safe_name}.desktop"

        desktop_file.write_text(content)
        desktop_file.chmod(0o755)

        logger.info(f"Created desktop entry: {desktop_file}")
        return desktop_file

    def remove_entry(self, app_id: str) -> bool:
        """
        Remove a .desktop entry.

        Returns True if the entry was removed.
        """
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in app_id)
        desktop_file = self.DESKTOP_DIR / f"neuronos-{safe_name}.desktop"

        if desktop_file.exists():
            desktop_file.unlink()
            logger.info(f"Removed desktop entry: {desktop_file}")
            return True
        return False

    def list_entries(self) -> list[dict]:
        """
        List all NeuronOS desktop entries.

        Returns list of dicts with entry metadata.
        """
        entries = []

        for desktop_file in self.DESKTOP_DIR.glob("neuronos-*.desktop"):
            try:
                entry = self._parse_desktop_file(desktop_file)
                if entry:
                    entries.append(entry)
            except Exception as e:
                logger.error(f"Failed to parse {desktop_file}: {e}")

        return entries

    def _parse_desktop_file(self, path: Path) -> Optional[dict]:
        """Parse a .desktop file into a dict."""
        content = path.read_text()

        entry = {"path": str(path)}

        for line in content.split("\n"):
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            if key == "Name":
                entry["name"] = value
            elif key == "Comment":
                entry["comment"] = value
            elif key == "Icon":
                entry["icon"] = value
            elif key == "X-NeuronOS-AppId":
                entry["app_id"] = value
            elif key == "X-NeuronOS-ExecutionPath":
                entry["execution_path"] = value

        return entry if "app_id" in entry else None

    def save_icon(self, app_id: str, icon_data: bytes, format: str = "png") -> Path:
        """
        Save an icon for an application.

        Args:
            app_id: Application identifier
            icon_data: Raw icon data
            format: Image format (png, svg, etc.)

        Returns:
            Path to the saved icon
        """
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in app_id)
        icon_path = self.ICONS_DIR / f"{safe_name}.{format}"

        icon_path.write_bytes(icon_data)
        logger.info(f"Saved icon: {icon_path}")

        return icon_path

    def update_desktop_database(self):
        """
        Update the desktop database to recognize new entries.

        Calls update-desktop-database if available.
        """
        try:
            import subprocess
            subprocess.run(
                ["update-desktop-database", str(self.DESKTOP_DIR)],
                check=False,
                capture_output=True,
            )
        except FileNotFoundError:
            pass  # update-desktop-database not available
