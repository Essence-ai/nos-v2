"""
Hardware compatibility database lookups.
Contains known hardware quirks and workarounds.
"""

import os
import yaml
from typing import Optional
from dataclasses import dataclass


@dataclass
class HardwareQuirk:
    """Describes a known hardware quirk and its workaround."""
    device_id: str
    vendor_id: str
    description: str
    workaround: str
    severity: str  # "info", "warning", "error"


@dataclass
class CompatibilityEntry:
    """Compatibility status for a specific hardware device."""
    vendor_id: str
    device_id: str
    name: str
    status: str  # "verified", "works", "partial", "broken"
    notes: str
    quirks: list[HardwareQuirk]


class CompatibilityDatabase:
    """Hardware compatibility database."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(__file__),
                "..", "data", "hardware_db.yaml"
            )
        self._db_path = db_path
        self._data = self._load_database()

    def _load_database(self) -> dict:
        """Load the compatibility database from YAML."""
        if not os.path.exists(self._db_path):
            return {"gpus": [], "quirks": []}
        with open(self._db_path) as f:
            return yaml.safe_load(f) or {"gpus": [], "quirks": []}

    def lookup_gpu(self, vendor_id: str, device_id: str) -> Optional[CompatibilityEntry]:
        """Look up a GPU in the compatibility database."""
        for entry in self._data.get("gpus", []):
            if entry.get("vendor_id") == vendor_id and entry.get("device_id") == device_id:
                quirks = self._get_quirks_for_device(vendor_id, device_id)
                return CompatibilityEntry(
                    vendor_id=entry["vendor_id"],
                    device_id=entry["device_id"],
                    name=entry.get("name", ""),
                    status=entry.get("status", "unknown"),
                    notes=entry.get("notes", ""),
                    quirks=quirks
                )
        return None

    def _get_quirks_for_device(self, vendor_id: str, device_id: str) -> list[HardwareQuirk]:
        """Get all quirks that apply to a specific device."""
        quirks = []
        for q in self._data.get("quirks", []):
            if q.get("vendor_id") == vendor_id:
                # Check if quirk applies to all devices or this specific one
                if q.get("device_id") is None or q.get("device_id") == device_id:
                    quirks.append(HardwareQuirk(
                        device_id=device_id,
                        vendor_id=vendor_id,
                        description=q.get("description", ""),
                        workaround=q.get("workaround", ""),
                        severity=q.get("severity", "info")
                    ))
        return quirks

    def get_all_verified_gpus(self) -> list[CompatibilityEntry]:
        """Get all GPUs that have been verified to work."""
        verified = []
        for entry in self._data.get("gpus", []):
            if entry.get("status") == "verified":
                quirks = self._get_quirks_for_device(
                    entry["vendor_id"],
                    entry["device_id"]
                )
                verified.append(CompatibilityEntry(
                    vendor_id=entry["vendor_id"],
                    device_id=entry["device_id"],
                    name=entry.get("name", ""),
                    status="verified",
                    notes=entry.get("notes", ""),
                    quirks=quirks
                ))
        return verified
