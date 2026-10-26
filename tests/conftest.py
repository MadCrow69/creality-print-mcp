import json
from pathlib import Path

import pytest

USER_ID = "1234567890"
PARENT = "0.20mm Standard @Vendor Printer 0.4 nozzle"


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=4), encoding="utf-8")


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Synthetic slicer data folder mimicking the Creality Print / OrcaSlicer layout."""
    root = tmp_path / "config"
    system = root / "system"
    _write(system / "Vendor" / "process" / "fdm_process_common.json",
           {"name": "fdm_process_common", "layer_height": "0.2", "support_top_z_distance": "0.1",
            "support_interface_spacing": "0.5", "outer_wall_speed": ["200"]})
    # Same base name under another vendor: must not make resolution ambiguous for Vendor presets.
    _write(system / "Other" / "process" / "fdm_process_common.json",
           {"name": "fdm_process_common", "layer_height": "0.3"})
    _write(system / "Vendor" / "process" / f"{PARENT}.json",
           {"name": PARENT, "inherits": "fdm_process_common", "sparse_infill_pattern": "grid",
            "support_object_xy_distance": "0.35"})

    user = root / "user" / USER_ID / "process"
    _write(user / "My Profile.json",
           {"name": "My Profile", "inherits": PARENT, "from": "User", "outer_wall_speed": ["55"],
            "top_bottom_infill_wall_overlap": "30%"})
    _write(user / "Clean.json",
           {"name": "Clean", "inherits": PARENT, "sparse_infill_pattern": "gyroid", "support_top_z_distance": "0.2",
            "support_object_xy_distance": "0.55", "support_interface_spacing": "0.2",
            "top_bottom_infill_wall_overlap": "15%"})
    _write(user / "Orphan.json", {"name": "Orphan", "inherits": "missing parent"})
    _write(user / "Ambiguous.json", {"name": "Ambiguous", "inherits": "fdm_process_common"})
    (root / "user" / "default" / "process").mkdir(parents=True)
    return root


@pytest.fixture
def store(config_dir: Path, tmp_path: Path):
    from creality_print_mcp.profiles import ProfileStore

    return ProfileStore(config_dir, tmp_path / "backups")
