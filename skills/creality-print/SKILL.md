---
name: creality-print
description: Use when a user has a 3D printing problem or request involving Creality Print, OrcaSlicer or Bambu Studio presets or models - supports fusing to or scarring the part, supports too hard to remove or breaking the part, stringing, wall bulges, first layer not sticking, nozzle hitting infill, rough supported surfaces, changing or undoing a slicer setting, or resizing/rotating an STL, OBJ or 3MF file. Requires the creality-print MCP server.
---

# Creality Print / OrcaSlicer / Bambu Studio

## Overview

The `creality-print` MCP server reads the **effective** value of every slicer setting (user overrides merged with the inherited vendor preset) and edits user presets with an automatic backup. The audit only knows a fixed list of failure patterns, so you still diagnose: symptom → preset type → keys → evidence → proposal → edit.

If the `creality-print` tools are not available, tell the user to install the server (https://github.com/MadCrow69/creality-print-mcp) and stop.

## Print problem workflow

1. **Find the preset.** Call `list_profiles`. If more than one process or filament preset could be the one being printed, ask which. Only **user** presets can be read or edited by name. If the user prints with a system preset, they must save a copy in the slicer first.
2. **Map the symptom** using the table below. It also says which preset type holds each key.
3. **Collect evidence.** Run `audit_profile` when the symptom is one it covers. Otherwise, or in addition, call `get_profile` on the right type. **Zero findings does not mean the preset is fine**: it means none of the audited patterns matched.
4. **Propose before editing.** For each change, give the preset, key, current → new value, whether the current value is the user's or inherited, and why. Before the first edit, tell the user to close the slicer: an open slicer can overwrite the file.
5. **Edit** with `set_profile_parameter`, one key per call. Apply directly only if the user explicitly asked you to apply the changes ("fix it", "apply"). Otherwise wait for an OK.
6. **Report.** List each change with its backup file, say that `restore_backup` undoes it, and mention causes outside the preset (see table).

## Symptom map

| Symptom | Preset | Keys (check with `get_profile`) | Audited? | Also check outside the preset |
|---|---|---|---|---|
| Support fused to the part | process | `support_top_z_distance` (≈ 1 × `layer_height`) | yes | — |
| Support scars vertical walls | process | `support_object_xy_distance` | yes | — |
| Support too hard to remove, breaks the part | process | `support_interface_pattern` (rectilinear, not concentric), `support_interface_spacing` (0.5 vendor; < 0.3 ≈ solid), `support_interface_top_layers` (2), tree: `tree_support_wall_count` (0 = auto), `tree_support_branch_diameter`, `tree_support_brim_width`; then `support_top_z_distance` | yes, except diameter, brim and interface layers | PETG needs an extra layer of Z gap |
| Rough supported surface | process | `support_interface_spacing` (0.3–0.4 at most), `support_interface_top_layers` | **no** (trade-off) | Every step denser makes removal harder: never go below 0.3 mm or to concentric to fix roughness |
| Wall bulges / ripples | process | `top_bottom_infill_wall_overlap` | yes | — |
| Nozzle hits infill, noise | process | `sparse_infill_pattern` | yes | — |
| Stringing | filament, then machine | `filament_retraction_length`, `filament_retraction_speed`, `nozzle_temperature`; machine `retraction_length`, `retraction_speed` | **no** | wet filament (dry it) |
| First layer not sticking | filament + process | bed temp for **the plate in use** (`hot_plate_*`, `textured_plate_*`, `cool_plate_*`, `eng_plate_*` and their `_initial_layer` variants); process `initial_layer_speed`, `initial_layer_print_height`, `brim_type` | **no** | Z offset, bed leveling, greasy plate |

A filament value of `nil` means "use the machine value", so read the machine preset before changing retraction. If you don't know which plate type is selected, ask before editing bed temperatures.

## Undo

`list_backups(name, profile_type)` → `restore_backup(name, backup_file, profile_type)`. The restore backs up the current state first.

## 3D models

- Always `get_model_dimensions` first. A model that is not watertight may slice badly, so tell the user.
- **Fit to a bed:** factor = smallest of (bed axis / model axis) across X, Y, Z, rounded down with a few mm of margin. Then `scale_model(factor=...)`.
- `rotate_model` applies the angles you pass; it does not pick an orientation. Explain the angle you choose (e.g. largest flat face down), then call `get_model_dimensions` on the output.
- Write the output next to the source with a suffix (`part_80pct.stl`). The tools refuse to overwrite the source.

## Common mistakes

- Saying "the audit found nothing, your preset is fine" for stringing or adhesion problems.
- Editing a bed temperature key for a plate the user doesn't use.
- Passing `force=true` to get past the unknown-key guard. That guard usually catches a typo or a key from another slicer version; check the key in `get_profile` output instead.
- Editing the process preset for a filament problem, or the reverse.
- Making the support interface denser (small spacing, concentric, more layers) to improve the supported surface without warning that removal gets harder. Vendor values (rectilinear/auto, 0.5 mm, 2 layers) are the safe start.
- Changing several keys silently, with no list of what changed and how to undo it.
