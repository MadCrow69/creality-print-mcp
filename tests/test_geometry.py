import pytest
import trimesh

from creality_print_mcp import geometry


@pytest.fixture
def box(tmp_path):
    path = tmp_path / "box.stl"
    trimesh.creation.box((10, 20, 30)).export(path)
    return path


def test_describe(box):
    info = geometry.describe(box)
    assert info["dimensions_mm"] == {"x": 10.0, "y": 20.0, "z": 30.0}
    assert info["volume_cm3"] == 6.0
    assert info["watertight"] is True


@pytest.mark.parametrize("kwargs, expected_z", [({"percent": 50}, 15.0), ({"percent": 5}, 1.5),
                                                ({"factor": 2}, 60.0), ({"target_height_mm": 15}, 15.0)])
def test_scale(box, tmp_path, kwargs, expected_z):
    result = geometry.scale(box, tmp_path / "out.stl", **kwargs)
    assert result["dimensions_mm"]["z"] == expected_z
    assert geometry.describe(tmp_path / "out.stl")["dimensions_mm"]["z"] == expected_z


@pytest.mark.parametrize("kwargs", [{}, {"percent": 50, "factor": 0.5}, {"factor": 0}, {"percent": -1}])
def test_scale_rejects_bad_arguments(box, tmp_path, kwargs):
    with pytest.raises(geometry.GeometryError):
        geometry.scale(box, tmp_path / "out.stl", **kwargs)


def test_never_overwrites_the_source(box):
    with pytest.raises(geometry.GeometryError, match="must differ"):
        geometry.scale(box, box, factor=2)
    with pytest.raises(geometry.GeometryError, match="must differ"):
        geometry.rotate(box, box, x_deg=90)


def test_rotate(box, tmp_path):
    result = geometry.rotate(box, tmp_path / "rot.stl", x_deg=90)
    assert result["dimensions_mm"] == {"x": 10.0, "y": 30.0, "z": 20.0}


def test_3mf_roundtrip(box, tmp_path):
    out = tmp_path / "box.3mf"
    geometry.scale(box, out, factor=1)
    assert geometry.describe(out)["dimensions_mm"] == {"x": 10.0, "y": 20.0, "z": 30.0}
