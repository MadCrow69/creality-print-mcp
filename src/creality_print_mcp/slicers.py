"""Where each supported slicer keeps its profiles.

Creality Print, OrcaSlicer and Bambu Studio share the same profile format (OrcaSlicer is a fork of
Bambu Studio, Creality Print 6+ is a fork of OrcaSlicer):

    <config_dir>/user/<user_id>/{process,filament,machine}/<name>.json   user presets (only the overrides)
    <config_dir>/system/<vendor>/{process,filament,machine}/<name>.json  vendor presets

Every preset may point to its parent through "inherits".
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Slicer:
    key: str
    display_name: str
    # Path segments under the platform's application-data directory.
    app_dir: tuple[str, ...]
    # Creality Print keeps one sub-folder per version (6.0, 7.0, 7.3...); the others don't.
    versioned: bool = False


SLICERS: dict[str, Slicer] = {
    "creality": Slicer("creality", "Creality Print", ("Creality", "Creality Print"), versioned=True),
    "orca": Slicer("orca", "OrcaSlicer", ("OrcaSlicer",)),
    "bambu": Slicer("bambu", "Bambu Studio", ("BambuStudio",)),
}

DEFAULT_SLICER = "creality"


def _app_data_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def get_slicer() -> Slicer:
    key = os.environ.get("SLICER", DEFAULT_SLICER).strip().lower()
    if key not in SLICERS:
        raise ValueError(f"Unknown SLICER '{key}'. Supported: {', '.join(SLICERS)}")
    return SLICERS[key]


def _version_key(name: str) -> tuple[int, ...]:
    return tuple(int(p) for p in name.split("."))


def resolve_config_dir(slicer: Slicer | None = None) -> Path:
    """Folder that contains user/ and system/. SLICER_CONFIG_DIR overrides auto-detection."""
    forced = os.environ.get("SLICER_CONFIG_DIR")
    if forced:
        return Path(forced)

    slicer = slicer or get_slicer()
    root = _app_data_dir().joinpath(*slicer.app_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"{slicer.display_name} data folder not found: {root}")
    if not slicer.versioned:
        return root

    versions = [
        d.name for d in root.iterdir()
        if d.is_dir() and re.fullmatch(r"\d+(\.\d+)*", d.name) and (d / "user").is_dir()
    ]
    if not versions:
        raise FileNotFoundError(f"No {slicer.display_name} version folder with a 'user' directory in {root}")
    return root / max(versions, key=_version_key)
