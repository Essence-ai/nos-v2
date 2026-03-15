"""
Determines the optimal execution path for a given application.

Routing priority: native > wine/proton > vm
"""

import fnmatch
import logging
import os
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


class ExecutionPath(Enum):
    """Execution path for an application."""
    NATIVE = "native"
    WINE = "wine"
    PROTON = "proton"
    VM = "vm"
    UNKNOWN = "unknown"


class AppRouter:
    """
    Routes applications to their optimal execution path.

    Uses a curated database of applications to determine whether
    to run natively, through Wine/Proton, or in the VM.
    """

    DEFAULT_DB_PATH = "/usr/share/neuronos/app_database.yaml"

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Check for local development path first
            local_path = Path(__file__).parent.parent / "data" / "app_database.yaml"
            if local_path.exists():
                db_path = str(local_path)
            else:
                db_path = self.DEFAULT_DB_PATH

        self._db_path = db_path
        self._apps: list[dict] = []
        self._load_database()

    def _load_database(self):
        """Load the application database from YAML."""
        if not os.path.exists(self._db_path):
            logger.warning(f"App database not found: {self._db_path}")
            return

        try:
            with open(self._db_path) as f:
                data = yaml.safe_load(f)
                self._apps = data.get("applications", [])
                logger.info(f"Loaded {len(self._apps)} applications from database")
        except Exception as e:
            logger.error(f"Failed to load app database: {e}")

    def route_executable(self, exe_path: str) -> tuple[ExecutionPath, Optional[dict]]:
        """
        Given a path to a downloaded .exe or .msi, determine how to run it.

        Returns:
            Tuple of (execution_path, app_entry or None)
        """
        filename = Path(exe_path).name.lower()

        for app in self._apps:
            patterns = app.get("exe_patterns", [])
            for pattern in patterns:
                if fnmatch.fnmatch(filename, pattern.lower()):
                    return ExecutionPath(app["path"]), app

        # No match in database — try Wine as default
        logger.info(f"No database match for {filename}, defaulting to Wine")
        return ExecutionPath.WINE, None

    def get_app_by_name(self, name: str) -> Optional[dict]:
        """Get an application entry by exact name."""
        for app in self._apps:
            if app.get("name", "").lower() == name.lower():
                return app
        return None

    def search(self, query: str) -> list[dict]:
        """
        Search the database by name, category, or alias.

        Args:
            query: Search query string

        Returns:
            List of matching application entries
        """
        query_lower = query.lower()
        results = []

        for app in self._apps:
            if (
                query_lower in app.get("name", "").lower()
                or query_lower in app.get("category", "").lower()
                or any(query_lower in a.lower() for a in app.get("aliases", []))
            ):
                results.append(app)

        return results

    def get_by_category(self, category: str) -> list[dict]:
        """Get all applications in a category."""
        category_lower = category.lower()
        return [
            app for app in self._apps
            if app.get("category", "").lower() == category_lower
        ]

    def get_native_alternatives(self, app_name: str) -> list[dict]:
        """
        Find native Linux alternatives for a given application.

        For example, if searching for "Photoshop", might return GIMP.
        """
        app = self.get_app_by_name(app_name)
        if not app:
            return []

        category = app.get("category", "")
        if not category:
            return []

        # Find native apps in the same category
        return [
            a for a in self._apps
            if a.get("category") == category
            and a.get("path") == "native"
            and a.get("name") != app_name
        ]

    def get_all_vm_apps(self) -> list[dict]:
        """Get all applications that require VM execution."""
        return [app for app in self._apps if app.get("path") == "vm"]

    def get_all_native_apps(self) -> list[dict]:
        """Get all native Linux applications."""
        return [app for app in self._apps if app.get("path") == "native"]

    def get_categories(self) -> list[str]:
        """Get all unique categories in the database."""
        categories = set()
        for app in self._apps:
            cat = app.get("category")
            if cat:
                categories.add(cat)
        return sorted(categories)
