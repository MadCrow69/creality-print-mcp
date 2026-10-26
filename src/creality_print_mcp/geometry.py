"""Inspection and transformation of 3D models (.stl, .obj, .3mf)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import trimesh


class GeometryError(Exception):
    """Expected, user-facing failure (missing file, invalid output path...)."""


def load_mesh(path: str | Path) -> trimesh.Trimesh:
    if not Path(path).exists():
        raise GeometryError(f"File not found: {path}")
    loaded = trimesh.load(str(path))
    return loaded.to_geometry() if isinstance(loaded, trimesh.Scene) else loaded


def dimensions(mesh: trimesh.Trimesh) -> dict[str, float]:
    x, y, z = mesh.extents.tolist()
    return {"x": round(x, 2), "y": round(y, 2), "z": round(z, 2)}


def describe(path: str | Path) -> dict[str, Any]:
    mesh = load_mesh(path)
    return {
        "file": str(path),
        "dimensions_mm": dimensions(mesh),
        "volume_cm3": round(mesh.volume / 1000.0, 2) if mesh.is_volume else None,
        "watertight": bool(mesh.is_watertight),
        "faces": len(mesh.faces),
        "vertices": len(mesh.vertices),
    }


def _check_output(source: str | Path, output: str | Path) -> None:
    if not Path(source).exists():
        raise GeometryError(f"Source file not found: {source}")
    if Path(output).resolve() == Path(source).resolve():
        raise GeometryError("output_path must differ from the source file (the original would be overwritten).")
    if not Path(output).resolve().parent.is_dir():
        raise GeometryError(f"Output folder does not exist: {Path(output).resolve().parent}")


def scale(source: str | Path, output: str | Path, *, percent: float | None = None,
          factor: float | None = None, target_height_mm: float | None = None) -> dict[str, Any]:
    given = [v for v in (percent, factor, target_height_mm) if v is not None]
    if len(given) != 1:
        raise GeometryError("Pass exactly one of percent, factor and target_height_mm.")
    if given[0] <= 0:
        raise GeometryError("Scale/height must be greater than zero.")
    _check_output(source, output)

    mesh = load_mesh(source)
    if target_height_mm is not None:
        height = mesh.extents[2]
        if height <= 0:
            raise GeometryError("The model has zero Z height; use percent or factor.")
        applied = target_height_mm / height
    elif factor is not None:
        applied = factor
    else:
        applied = percent / 100.0

    mesh.apply_scale(applied)
    mesh.export(str(output))
    return {"output": str(output), "scale_factor": round(applied, 4), "dimensions_mm": dimensions(mesh)}


def rotate(source: str | Path, output: str | Path, *, x_deg: float = 0.0, y_deg: float = 0.0,
           z_deg: float = 0.0) -> dict[str, Any]:
    _check_output(source, output)
    mesh = load_mesh(source)
    for degrees, axis in ((x_deg, [1, 0, 0]), (y_deg, [0, 1, 0]), (z_deg, [0, 0, 1])):
        if degrees:
            mesh.apply_transform(trimesh.transformations.rotation_matrix(np.radians(degrees), axis))
    mesh.export(str(output))
    return {"output": str(output), "rotation_deg": {"x": x_deg, "y": y_deg, "z": z_deg},
            "dimensions_mm": dimensions(mesh)}
