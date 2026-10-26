"""Heuristic checks on effective process settings that commonly cause print failures."""

from __future__ import annotations

from typing import Any

from .profiles import ResolvedProfile, to_number

CROSSING_INFILL_PATTERNS = frozenset({"grid", "triangles"})
SUPPORT_TOP_Z_MAX_FACTOR = 1.2  # × layer height
SUPPORT_TOP_Z_MIN_FACTOR = 0.8  # × layer height
SUPPORT_XY_MIN_MM = 0.5
WALL_OVERLAP_MAX_PCT = 30
INTERFACE_SPACING_MAX_MM = 0.5


def audit(profile: ResolvedProfile) -> list[dict[str, Any]]:
    p = profile.effective
    findings: list[dict[str, Any]] = []

    def report(severity: str, area: str, key: str, problem: str, recommendation: str) -> None:
        findings.append({
            "severity": severity,
            "area": area,
            "key": key,
            "current_value": p.get(key),
            "origin": profile.origin(key),
            "problem": problem,
            "recommendation": recommendation,
        })

    infill = p.get("sparse_infill_pattern")
    if infill in CROSSING_INFILL_PATTERNS:
        report("HIGH", "Infill", "sparse_infill_pattern",
               f"'{infill}' crosses lines within the same layer; at high speed the nozzle hits already cooled "
               "plastic, causing noise, marks and the risk of knocking the part off the bed.",
               "Switch to 'gyroid' or 'crosshatch' (no crossing paths within a layer).")

    layer = to_number(p.get("layer_height"))
    top_z = to_number(p.get("support_top_z_distance"))
    if layer and top_z is not None:
        if top_z > layer * SUPPORT_TOP_Z_MAX_FACTOR:
            report("MEDIUM", "Supports", "support_top_z_distance",
                   f"A Z gap of {top_z}mm is too large for {layer}mm layers; overhang lines sag without support "
                   "and the underside comes out stringy.",
                   f"Set it to {layer}mm (one layer of clearance).")
        elif top_z < layer * SUPPORT_TOP_Z_MIN_FACTOR:
            report("HIGH", "Supports", "support_top_z_distance",
                   f"A Z gap of {top_z}mm with {layer}mm layers fuses the support to the part, making it very "
                   "hard to remove.",
                   f"Increase it to {layer}mm.")

    xy = to_number(p.get("support_object_xy_distance"))
    if xy is not None and xy < SUPPORT_XY_MIN_MM:
        report("MEDIUM", "Supports", "support_object_xy_distance",
               f"An XY gap of {xy}mm lets support branches touch and scar the part's vertical walls.",
               "Increase it to 0.55-0.60mm.")

    overlap = to_number(p.get("top_bottom_infill_wall_overlap"))
    if overlap is not None and overlap >= WALL_OVERLAP_MAX_PCT:
        report("MEDIUM", "Wall finish", "top_bottom_infill_wall_overlap",
               f"A {overlap:g}% overlap pushes excess plastic into the outer wall, creating bulges and ripples.",
               "Reduce it to 15-20%.")

    spacing = to_number(p.get("support_interface_spacing"))
    if spacing is not None and spacing >= INTERFACE_SPACING_MAX_MM:
        report("LOW", "Supported surface finish", "support_interface_spacing",
               f"A {spacing}mm interface spacing leaves gaps and an uneven supported surface.",
               "Reduce it to 0.2mm and use the 'concentric' interface pattern; the support peels off as one shell.")

    return findings
