"""MCP server exposing slicer presets and 3D model tools."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from . import __version__, geometry
from .audit import audit
from .profiles import ProfileError, ProfileStore
from .slicers import get_slicer, resolve_config_dir

ProfileType = Literal["process", "filament", "machine"]

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)
WRITES_PRESET = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=True,
                                open_world_hint=False)
WRITES_NEW_FILE = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True,
                                  open_world_hint=False)

RELOAD_NOTE = ("If the slicer is open, restart it to load the change. Cloud sync metadata (.info) "
               "is not updated by this server.")

mcp = MCPServer(
    "creality-print-mcp",
    version=__version__,
    instructions=(
        "Reads, audits and edits Creality Print / OrcaSlicer / Bambu Studio presets, and inspects, scales "
        "and rotates 3D models. User presets only store overrides; get_profile and audit_profile resolve "
        "the full 'inherits' chain so the values shown are the effective ones. Every edit creates a backup "
        "that restore_backup can bring back."
    ),
)


def _store() -> ProfileStore:
    backup_dir = os.environ.get("CREALITY_PRINT_MCP_BACKUP_DIR")
    slicer = get_slicer()
    default_backup = Path.home() / ".creality-print-mcp" / "backups" / slicer.key
    try:
        return ProfileStore(resolve_config_dir(slicer), Path(backup_dir) if backup_dir else default_backup)
    except (FileNotFoundError, ValueError) as e:
        raise ToolError(str(e)) from e


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except (ProfileError, geometry.GeometryError, FileNotFoundError, ValueError) as e:
        raise ToolError(str(e)) from e


# --- presets ---

@mcp.tool(annotations=READ_ONLY)
def list_profiles() -> dict[str, Any]:
    """List the user's slicer presets (process, filament and machine), each with the preset it inherits from."""
    store = _store()
    return {
        "slicer": get_slicer().display_name,
        "config_dir": str(store.config_dir),
        "user_id": _run(lambda: store.user_dir.name),
        **_run(store.list_profiles),
    }


@mcp.tool(annotations=READ_ONLY)
def get_profile(name: str, profile_type: ProfileType = "process", resolve_inheritance: bool = True) -> dict[str, Any]:
    """Get a preset's settings.
    With resolve_inheritance=true (default) returns the EFFECTIVE values, merging the 'inherits' chain up to
    the vendor preset; with false returns only what the user overrode."""
    store = _store()
    resolved = _run(store.resolve, name, profile_type)
    if not resolve_inheritance:
        return {"profile": name, "settings": resolved.own}
    return {
        "profile": name,
        "inheritance_chain": resolved.chain,
        "user_overrides": sorted(resolved.own),
        "warnings": resolved.warnings,
        "settings": resolved.effective,
    }


@mcp.tool(annotations=READ_ONLY)
def audit_profile(name: str) -> dict[str, Any]:
    """Audit a process preset's EFFECTIVE values (inheritance resolved) for common causes of failures:
    nozzle hitting crossing infill, supports fusing to or scarring the part, wall bulges, rough supported surfaces."""
    resolved = _run(_store().resolve, name, "process")
    findings = audit(resolved)
    return {
        "profile": name,
        "inheritance_chain": resolved.chain,
        "warnings": resolved.warnings,
        "finding_count": len(findings),
        "findings": findings,
    }


@mcp.tool(annotations=WRITES_PRESET)
def set_profile_parameter(name: str, key: str, value: str, profile_type: ProfileType = "process",
                          force: bool = False) -> dict[str, Any]:
    """Set one setting in a user preset. A backup is taken first (see list_backups / restore_backup).
    List-shaped fields (e.g. outer_wall_speed) stay lists. Keys that exist neither in the preset nor in its
    parents are refused as probable typos unless force=true. Identity keys (name, inherits...) are refused."""
    result = _run(_store().set_parameter, name, key, value, profile_type, force)
    return {**result, "note": RELOAD_NOTE}


@mcp.tool(annotations=READ_ONLY)
def list_backups(name: str, profile_type: ProfileType = "process") -> dict[str, Any]:
    """List backups of a preset taken by set_profile_parameter / restore_backup, newest first."""
    store = _store()
    return {"profile": name, "backup_dir": str(store.backup_dir / profile_type),
            "backups": store.list_backups(name, profile_type)}


@mcp.tool(annotations=WRITES_PRESET)
def restore_backup(name: str, backup_file: str, profile_type: ProfileType = "process") -> dict[str, Any]:
    """Restore a preset from a backup file name returned by list_backups. The current state is backed up first."""
    result = _run(_store().restore_backup, name, backup_file, profile_type)
    return {**result, "note": RELOAD_NOTE}


# --- 3D models ---

@mcp.tool(annotations=READ_ONLY)
def get_model_dimensions(file_path: str) -> dict[str, Any]:
    """Load a 3D model (.stl, .obj, .3mf) and return its size in mm (X, Y, Z), volume, watertightness and face count."""
    return _run(geometry.describe, file_path)


@mcp.tool(annotations=WRITES_NEW_FILE)
def scale_model(file_path: str, output_path: str, percent: float | None = None, factor: float | None = None,
                target_height_mm: float | None = None) -> dict[str, Any]:
    """Scale a 3D model uniformly into a new file. Pass exactly one of:
    percent (80 = 80%), factor (0.8 = 80%) or target_height_mm (desired Z height)."""
    return _run(geometry.scale, file_path, output_path, percent=percent, factor=factor,
                target_height_mm=target_height_mm)


@mcp.tool(annotations=WRITES_NEW_FILE)
def rotate_model(file_path: str, output_path: str, x_deg: float = 0.0, y_deg: float = 0.0,
                 z_deg: float = 0.0) -> dict[str, Any]:
    """Rotate a 3D model into a new file, in degrees around X, then Y, then Z, to improve bed contact
    and reduce overhangs/supports."""
    return _run(geometry.rotate, file_path, output_path, x_deg=x_deg, y_deg=y_deg, z_deg=z_deg)


def main() -> None:
    mcp.run()
