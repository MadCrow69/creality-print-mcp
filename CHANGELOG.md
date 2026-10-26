# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-26

### Added
- Preset tools: `list_profiles`, `get_profile` (with full `inherits` resolution), `audit_profile`,
  `set_profile_parameter` (automatic backup, list-shape preserving, typo and identity-key guards),
  `list_backups`, `restore_backup`.
- Model tools: `get_model_dimensions`, `scale_model` (percent, factor or target height), `rotate_model`.
- Support for Creality Print (auto-detects the newest version folder), OrcaSlicer and Bambu Studio via `SLICER`.
- Tool annotations (read-only / destructive) for clients that ask for confirmation.
