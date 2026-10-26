"""Reading, inheritance resolution, editing and backup of slicer presets."""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

PROFILE_TYPES = ("process", "filament", "machine")

# Identity keys: changing them desyncs file name, preset name and inheritance.
PROTECTED_KEYS = frozenset({
    "name", "inherits", "from", "print_settings_id", "filament_settings_id", "printer_settings_id",
    "base_id", "setting_id", "version", "is_custom_defined", "instantiation",
})
MAX_INHERITANCE_DEPTH = 20
_BACKUP_NAME = re.compile(r"\d{8}-\d{6}-\d{2,}\.json")


class ProfileError(Exception):
    """Expected, user-facing failure (missing preset, invalid name, ambiguous parent...)."""


@dataclass
class ResolvedProfile:
    name: str
    path: Path
    own: dict[str, Any]
    # (preset name, data), child first.
    layers: list[tuple[str, dict[str, Any]]]
    warnings: list[str] = field(default_factory=list)

    @property
    def chain(self) -> list[str]:
        return [n for n, _ in self.layers]

    @property
    def effective(self) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for _, data in reversed(self.layers):
            merged.update(data)
        return merged

    def origin(self, key: str) -> str | None:
        for name, data in self.layers:
            if key in data:
                return "user preset" if name == self.name else f"inherited from '{name}'"
        return None


def read_json(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    os.replace(tmp, path)


def to_number(value: Any) -> float | None:
    """Parses preset values such as "0.2", "18%" or ["55"]; None when missing or not numeric."""
    if isinstance(value, list):
        value = value[0] if value else None
    if value is None:
        return None
    try:
        return float(str(value).strip().rstrip("%"))
    except ValueError:
        return None


@lru_cache(maxsize=16)
def _system_index(config_dir: str, profile_type: str) -> dict[str, tuple[str, ...]]:
    """Preset name -> files, keyed by the JSON "name" field (that is what "inherits" refers to)."""
    index: dict[str, list[str]] = {}
    system_dir = Path(config_dir) / "system"
    if not system_dir.is_dir():
        return {}
    for vendor_dir in system_dir.iterdir():
        type_dir = vendor_dir / profile_type
        if not type_dir.is_dir():
            continue
        for path in type_dir.glob("*.json"):
            try:
                name = read_json(path).get("name") or path.stem
            except (OSError, json.JSONDecodeError):
                continue
            index.setdefault(name, []).append(str(path))
    return {k: tuple(v) for k, v in index.items()}


class ProfileStore:
    def __init__(self, config_dir: Path, backup_dir: Path):
        self.config_dir = Path(config_dir)
        self.backup_dir = Path(backup_dir)

    # --- locations ---

    @property
    def user_dir(self) -> Path:
        """Prefers the logged-in user folder (numeric id) over 'default'."""
        user_root = self.config_dir / "user"
        if not user_root.is_dir():
            raise ProfileError(f"User presets folder not found: {user_root}")
        candidates = sorted(
            d for d in user_root.iterdir()
            if d.is_dir() and any((d / t).is_dir() for t in PROFILE_TYPES)
        )
        logged_in = [d for d in candidates if d.name != "default"]
        if logged_in:
            return logged_in[0]
        if candidates:
            return candidates[0]
        raise ProfileError(f"No user preset folder in {user_root}")

    def profile_path(self, name: str, profile_type: str = "process") -> Path:
        if profile_type not in PROFILE_TYPES:
            raise ProfileError(f"Invalid profile_type '{profile_type}'. Use one of: {', '.join(PROFILE_TYPES)}")
        if not name or name in (".", "..") or os.path.basename(name) != name or "/" in name:
            raise ProfileError(f"Invalid preset name: '{name}'")
        return self.user_dir / profile_type / f"{name}.json"

    # --- reading ---

    def list_profiles(self) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {}
        for profile_type in PROFILE_TYPES:
            items = []
            type_dir = self.user_dir / profile_type
            if type_dir.is_dir():
                for path in sorted(type_dir.glob("*.json")):
                    try:
                        inherits = read_json(path).get("inherits")
                    except (OSError, json.JSONDecodeError):
                        inherits = None
                    items.append({"name": path.stem, "inherits": inherits})
            result[profile_type] = items
        return result

    def _find_parent(self, name: str, profile_type: str, child_path: Path) -> Path | None:
        user_candidate = self.user_dir / profile_type / f"{name}.json"
        if user_candidate.exists():
            return user_candidate
        paths = [Path(p) for p in _system_index(str(self.config_dir), profile_type).get(name, ())]
        # The same base name exists for several vendors (e.g. fdm_process_common in Creality and Custom):
        # resolve inside the child's vendor, as the slicer does.
        same_vendor = [p for p in paths if p.parent == child_path.parent]
        if len(same_vendor) == 1:
            return same_vendor[0]
        if len(paths) > 1:
            raise ProfileError(f"Parent preset '{name}' is ambiguous (several files with that name): "
                               f"{[str(p) for p in paths]}")
        return paths[0] if paths else None

    def resolve(self, name: str, profile_type: str = "process") -> ResolvedProfile:
        """Merges the user preset with its whole "inherits" chain (user presets only store overrides)."""
        path = self.profile_path(name, profile_type)
        if not path.exists():
            raise ProfileError(f"Preset '{name}' not found in {path.parent}")

        own = read_json(path)
        resolved = ResolvedProfile(name=name, path=path, own=own, layers=[(name, own)])
        parent = own.get("inherits")
        current = path
        while parent:
            if len(resolved.layers) > MAX_INHERITANCE_DEPTH or parent in resolved.chain:
                raise ProfileError(f"Circular or too deep inheritance starting at '{name}'")
            parent_path = self._find_parent(parent, profile_type, current)
            if parent_path is None:
                resolved.warnings.append(f"Parent preset '{parent}' not found; values inherited from it are missing.")
                break
            data = read_json(parent_path)
            resolved.layers.append((parent, data))
            current = parent_path
            parent = data.get("inherits")
        return resolved

    # --- writing ---

    def _backup(self, path: Path, profile_type: str) -> Path:
        target_dir = self.backup_dir / profile_type
        target_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        seq = 0
        target = target_dir / f"{path.stem}.{stamp}-{seq:02d}.json"
        while target.exists():  # two backups in the same second must not overwrite each other
            seq += 1
            target = target_dir / f"{path.stem}.{stamp}-{seq:02d}.json"
        shutil.copy2(path, target)
        return target

    def set_parameter(self, name: str, key: str, value: str, profile_type: str = "process",
                      force: bool = False) -> dict[str, Any]:
        if key in PROTECTED_KEYS:
            raise ProfileError(f"'{key}' identifies the preset and cannot be changed here.")
        resolved = self.resolve(name, profile_type)
        effective = resolved.effective
        if key not in effective and not force:
            raise ProfileError(f"'{key}' does not exist in the preset or its parents; the slicer would ignore it. "
                               "Check the name with get_profile, or pass force=true.")

        previous = effective.get(key)
        previous_origin = resolved.origin(key)
        # Keep the field shape: list fields (per extruder, e.g. outer_wall_speed) stay lists.
        new_value: Any = [str(value)] * len(previous) if isinstance(previous, list) and previous else str(value)

        backup = self._backup(resolved.path, profile_type)
        own = dict(resolved.own)
        own[key] = new_value
        write_json_atomic(resolved.path, own)
        return {
            "profile": name,
            "profile_type": profile_type,
            "key": key,
            "previous_value": previous,
            "previous_origin": previous_origin,
            "new_value": new_value,
            "backup": str(backup),
        }

    def list_backups(self, name: str, profile_type: str = "process") -> list[str]:
        folder = self.backup_dir / profile_type
        if not folder.is_dir():
            return []
        prefix = f"{name}."
        return sorted(
            (p.name for p in folder.iterdir()
             if p.name.startswith(prefix) and _BACKUP_NAME.fullmatch(p.name[len(prefix):])),
            reverse=True,
        )

    def restore_backup(self, name: str, backup_file: str, profile_type: str = "process") -> dict[str, Any]:
        if os.path.basename(backup_file) != backup_file or backup_file not in self.list_backups(name, profile_type):
            raise ProfileError(f"Backup '{backup_file}' does not belong to preset '{name}'. Use list_backups.")
        source = self.backup_dir / profile_type / backup_file
        target = self.profile_path(name, profile_type)
        previous_backup = self._backup(target, profile_type) if target.exists() else None
        write_json_atomic(target, read_json(source))
        return {
            "profile": name,
            "restored_from": str(source),
            "backup_of_previous_state": str(previous_backup) if previous_backup else None,
        }
