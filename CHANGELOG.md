# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Agent skill `skills/creality-print/SKILL.md`: when to use the tools, symptom → preset/key map (including
  stringing and first-layer adhesion, which the audit does not cover), confirm-before-edit and undo flow.
- `audit_profile` flags supports that are hard to remove: concentric top interface, interface spacing
  below 0.3 mm (0 = solid) and 2 walls on tree branches.

### Fixed
- `audit_profile` no longer flags the vendor-default interface spacing (0.5 mm) as a "rough supported
  surface" and no longer recommends 0.2 mm + concentric: that interface welds the support to the part.

## [0.1.0] - 2026-10-26

### Added
- Preset tools: `list_profiles`, `get_profile` (with full `inherits` resolution), `audit_profile`,
  `set_profile_parameter` (automatic backup, list-shape preserving, typo and identity-key guards),
  `list_backups`, `restore_backup`.
- Model tools: `get_model_dimensions`, `scale_model` (percent, factor or target height), `rotate_model`.
- Support for Creality Print (auto-detects the newest version folder), OrcaSlicer and Bambu Studio via `SLICER`.
- Tool annotations (read-only / destructive) for clients that ask for confirmation.
