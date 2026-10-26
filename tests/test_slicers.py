import sys

import pytest

from creality_print_mcp import slicers


@pytest.fixture
def app_data(tmp_path, monkeypatch):
    monkeypatch.delenv("SLICER_CONFIG_DIR", raising=False)
    monkeypatch.setattr(slicers, "_app_data_dir", lambda: tmp_path)
    return tmp_path


def test_creality_picks_newest_version_with_user_folder(app_data, monkeypatch):
    monkeypatch.setenv("SLICER", "creality")
    base = app_data / "Creality" / "Creality Print"
    for version in ("6.0", "7.3", "7.10"):
        (base / version / "user").mkdir(parents=True)
    (base / "8.0").mkdir()  # no user folder yet
    assert slicers.resolve_config_dir() == base / "7.10"


def test_orca_is_not_versioned(app_data, monkeypatch):
    monkeypatch.setenv("SLICER", "orca")
    (app_data / "OrcaSlicer" / "user").mkdir(parents=True)
    assert slicers.resolve_config_dir() == app_data / "OrcaSlicer"


def test_config_dir_override(monkeypatch, tmp_path):
    monkeypatch.setenv("SLICER_CONFIG_DIR", str(tmp_path))
    assert slicers.resolve_config_dir() == tmp_path


def test_unknown_slicer(monkeypatch):
    monkeypatch.setenv("SLICER", "cura")
    with pytest.raises(ValueError, match="Unknown SLICER"):
        slicers.get_slicer()


def test_missing_install(app_data, monkeypatch):
    monkeypatch.setenv("SLICER", "bambu")
    with pytest.raises(FileNotFoundError):
        slicers.resolve_config_dir()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows default location")
def test_windows_app_data_default(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert slicers._app_data_dir() == tmp_path
