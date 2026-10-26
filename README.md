# creality-print-mcp

[Português](README.pt-BR.md)

An [MCP](https://modelcontextprotocol.io) server that lets AI assistants (Claude, Gemini/Antigravity, Cursor…) **read, audit and edit your Creality Print presets** and **inspect, scale and rotate 3D models**.

Creality Print is a fork of OrcaSlicer, which is a fork of Bambu Studio, and all three use the same preset format. **OrcaSlicer and Bambu Studio work too.**

> "Why are my supports fusing to the part?" → the assistant audits your process preset, shows that `support_top_z_distance` is inherited from the vendor preset and is too small for your layer height, and fixes it with a backup.

## Features

| Tool | What it does |
|---|---|
| `list_profiles` | Lists your process, filament and machine presets, each with the preset it inherits from |
| `get_profile` | Returns a preset's **effective** settings, following the full `inherits` chain to the vendor preset (or only your overrides) |
| `audit_profile` | Flags common causes of failed prints: crossing infill hit by the nozzle, supports fusing to or scarring the part, wall bulges, rough supported surfaces. Says whether each value is yours or inherited |
| `set_profile_parameter` | Changes one setting, with an automatic backup. Keeps list fields as lists, refuses unknown keys (typos) and identity keys |
| `list_backups` / `restore_backup` | Undo any edit |
| `get_model_dimensions` | Size (X/Y/Z mm), volume, watertightness and face count of `.stl`, `.obj`, `.3mf` |
| `scale_model` | Uniform scaling by percent, factor or target height, into a new file |
| `rotate_model` | Rotation around X/Y/Z to improve bed contact and reduce supports, into a new file |

### Why inheritance matters

Your saved presets only store **what you changed**. Everything else comes from the vendor preset through `inherits`. A tool that reads only the user file sees about 10 of the roughly 270 settings, and has to guess the rest. This server resolves the chain the same way the slicer does, including vendor-scoped lookup when several vendors share a base preset name.

## Requirements

- Python 3.10+ and [uv](https://docs.astral.sh/uv/) (recommended)
- Creality Print 6/7, OrcaSlicer or Bambu Studio installed and opened at least once
- Windows, macOS or Linux. The default data folders are auto-detected; development and real-data testing so far was on **Windows + Creality Print 7.3**

## Installation

### Claude Code

```bash
claude mcp add --scope user creality-print -- uvx --from git+https://github.com/MadCrow69/creality-print-mcp creality-print-mcp
```

> **Windows PowerShell:** PowerShell swallows the bare `--` before passing the arguments to `claude`, which then fails with `unknown option`. Run it through `cmd` instead:
> `cmd --% /c claude mcp add --scope user creality-print -- uvx --from git+https://github.com/MadCrow69/creality-print-mcp creality-print-mcp`

### Claude Desktop, Antigravity, Cursor and other JSON-configured clients

```json
{
  "mcpServers": {
    "creality-print": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/MadCrow69/creality-print-mcp", "creality-print-mcp"]
    }
  }
}
```

### OrcaSlicer or Bambu Studio

Add an environment variable to the entry above:

```json
"env": { "SLICER": "orca" }
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `SLICER` | `creality` | `creality`, `orca` or `bambu` |
| `SLICER_CONFIG_DIR` | auto | Folder that contains `user/` and `system/`. Use it for portable installs or to pin a Creality Print version (e.g. `…\Creality Print\7.3`) |
| `CREALITY_PRINT_MCP_BACKUP_DIR` | `~/.creality-print-mcp/backups/<slicer>` | Where preset backups go |

Auto-detected data folders:

| Slicer | Windows | macOS | Linux |
|---|---|---|---|
| Creality Print | `%APPDATA%\Creality\Creality Print\<newest version>` | `~/Library/Application Support/Creality/Creality Print/<version>` | `~/.config/Creality/Creality Print/<version>` |
| OrcaSlicer | `%APPDATA%\OrcaSlicer` | `~/Library/Application Support/OrcaSlicer` | `~/.config/OrcaSlicer` |
| Bambu Studio | `%APPDATA%\BambuStudio` | `~/Library/Application Support/BambuStudio` | `~/.config/BambuStudio` |

## Safety

- Every preset edit is preceded by a timestamped backup and written atomically.
- Model tools always write a **new** file and refuse to overwrite the source.
- Preset names are validated, so no path traversal outside the presets folder.
- **Close the slicer before editing presets** (or restart it afterwards). An open slicer may overwrite the file when it saves its own state.
- Cloud-synced presets: the server does not touch the `.info` sync metadata. If cloud sync brings back an older version, use `restore_backup` or re-apply the change.

## Development

```bash
git clone https://github.com/MadCrow69/creality-print-mcp
cd creality-print-mcp
uv sync
uv run pytest
uv run ruff check .
```

Tests run against synthetic preset trees and never touch your real slicer data.

## Roadmap

- Slicing from the CLI (G-code + time and filament estimates). Creality Print 7 does not expose the OrcaSlicer CLI; OrcaSlicer does.
- More audit rules (first layer, retraction, cooling per filament)
- Auto-orientation suggestions for minimal supports
- Publish to PyPI and the MCP Registry

Contributions are welcome. Open an issue first for larger changes.

## License

[MIT](LICENSE)

Not affiliated with or endorsed by Creality, the OrcaSlicer project or Bambu Lab. Product names are trademarks of their respective owners.
