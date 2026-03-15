"""
Configuration management for NeuronOS VM Manager.
"""

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class VMConfig:
    """VM configuration settings."""
    domain_name: str = "win11-neuron"
    ram_mb: int = 8192
    cpu_cores: int = 4
    auto_resource_allocation: bool = True
    grace_period_seconds: int = 300


@dataclass
class LookingGlassConfig:
    """Looking Glass configuration settings."""
    shm_path: str = "/dev/shm/looking-glass"
    shm_size_mb: int = 128
    borderless: bool = True
    capture_input: bool = True
    escape_key: str = "KEY_RIGHTCTRL"
    default_width: int = 1920
    default_height: int = 1080


@dataclass
class AppRoutingConfig:
    """Application routing configuration."""
    prefer_native: bool = True
    prefer_wine_over_vm: bool = True
    database_path: str = "/usr/share/neuronos/app_database.yaml"


@dataclass
class DownloadMonitorConfig:
    """Download monitor configuration."""
    enabled: bool = True
    watch_dirs: list[str] = field(default_factory=lambda: [str(Path.home() / "Downloads")])
    prompt_on_new_executable: bool = True


@dataclass
class NeuronOSConfig:
    """Main configuration for NeuronOS VM Manager."""
    vm: VMConfig = field(default_factory=VMConfig)
    looking_glass: LookingGlassConfig = field(default_factory=LookingGlassConfig)
    app_routing: AppRoutingConfig = field(default_factory=AppRoutingConfig)
    download_monitor: DownloadMonitorConfig = field(default_factory=DownloadMonitorConfig)

    # Paths
    config_dir: str = str(Path.home() / ".config" / "neuronos")
    data_dir: str = str(Path.home() / ".local" / "share" / "neuronos")
    log_level: str = "INFO"


class ConfigManager:
    """
    Manages NeuronOS configuration.

    Configuration is stored in ~/.config/neuronos/config.json
    """

    CONFIG_FILE = "config.json"

    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            config_dir = str(Path.home() / ".config" / "neuronos")

        self._config_dir = Path(config_dir)
        self._config_file = self._config_dir / self.CONFIG_FILE
        self._config: Optional[NeuronOSConfig] = None

    def load(self) -> NeuronOSConfig:
        """Load configuration from disk."""
        if self._config is not None:
            return self._config

        if self._config_file.exists():
            try:
                with open(self._config_file) as f:
                    data = json.load(f)
                self._config = self._from_dict(data)
                logger.info(f"Loaded configuration from {self._config_file}")
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
                self._config = NeuronOSConfig()
        else:
            self._config = NeuronOSConfig()

        return self._config

    def save(self, config: Optional[NeuronOSConfig] = None):
        """Save configuration to disk."""
        if config is not None:
            self._config = config

        if self._config is None:
            self._config = NeuronOSConfig()

        self._config_dir.mkdir(parents=True, exist_ok=True)

        with open(self._config_file, "w") as f:
            json.dump(self._to_dict(self._config), f, indent=2)

        logger.info(f"Saved configuration to {self._config_file}")

    def reset(self):
        """Reset configuration to defaults."""
        self._config = NeuronOSConfig()
        self.save()

    def _to_dict(self, config: NeuronOSConfig) -> dict:
        """Convert config to dictionary."""
        return {
            "vm": asdict(config.vm),
            "looking_glass": asdict(config.looking_glass),
            "app_routing": asdict(config.app_routing),
            "download_monitor": asdict(config.download_monitor),
            "config_dir": config.config_dir,
            "data_dir": config.data_dir,
            "log_level": config.log_level,
        }

    def _from_dict(self, data: dict) -> NeuronOSConfig:
        """Create config from dictionary."""
        return NeuronOSConfig(
            vm=VMConfig(**data.get("vm", {})),
            looking_glass=LookingGlassConfig(**data.get("looking_glass", {})),
            app_routing=AppRoutingConfig(**data.get("app_routing", {})),
            download_monitor=DownloadMonitorConfig(**data.get("download_monitor", {})),
            config_dir=data.get("config_dir", str(Path.home() / ".config" / "neuronos")),
            data_dir=data.get("data_dir", str(Path.home() / ".local" / "share" / "neuronos")),
            log_level=data.get("log_level", "INFO"),
        )


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config() -> NeuronOSConfig:
    """Get the global configuration."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager.load()


def save_config(config: NeuronOSConfig):
    """Save the global configuration."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    _config_manager.save(config)
