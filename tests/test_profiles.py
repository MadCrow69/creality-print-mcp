import json

import pytest
from conftest import PARENT, USER_ID

from creality_print_mcp.profiles import ProfileError, to_number


def test_user_dir_prefers_logged_in_user_over_default(store):
    assert store.user_dir.name == USER_ID


def test_resolve_follows_inheritance_within_the_childs_vendor(store):
    resolved = store.resolve("My Profile")
    assert resolved.chain == ["My Profile", PARENT, "fdm_process_common"]
    effective = resolved.effective
    assert effective["layer_height"] == "0.2"  # Vendor's base, not Other's 0.3
    assert effective["outer_wall_speed"] == ["55"]  # user override wins
    assert resolved.origin("outer_wall_speed") == "user preset"
    assert resolved.origin("support_object_xy_distance") == f"inherited from '{PARENT}'"


def test_resolve_refuses_ambiguous_parent_instead_of_guessing(store):
    with pytest.raises(ProfileError, match="ambiguous"):
        store.resolve("Ambiguous")


def test_resolve_warns_when_parent_is_missing(store):
    resolved = store.resolve("Orphan")
    assert resolved.chain == ["Orphan"]
    assert "missing parent" in resolved.warnings[0]


@pytest.mark.parametrize("name", ["../x", "..\\x", "a/b", "", ".."])
def test_invalid_names_are_rejected(store, name):
    with pytest.raises(ProfileError):
        store.profile_path(name)


def test_list_profiles(store):
    listed = store.list_profiles()
    assert {"name": "My Profile", "inherits": PARENT} in listed["process"]
    assert listed["filament"] == [] and listed["machine"] == []


def test_set_parameter_keeps_list_shape_records_origin_and_backs_up(store):
    result = store.set_parameter("My Profile", "outer_wall_speed", "60")
    assert result["new_value"] == ["60"]
    assert result["previous_value"] == ["55"]
    assert result["previous_origin"] == "user preset"

    inherited = store.set_parameter("My Profile", "support_object_xy_distance", "0.55")
    assert inherited["previous_origin"] == f"inherited from '{PARENT}'"

    saved = json.loads(store.profile_path("My Profile").read_text(encoding="utf-8"))
    assert saved["outer_wall_speed"] == ["60"]
    assert saved["support_object_xy_distance"] == "0.55"
    assert saved["inherits"] == PARENT  # the rest of the user file is untouched
    assert len(store.list_backups("My Profile")) == 2


def test_set_parameter_refuses_typos_and_identity_keys(store):
    with pytest.raises(ProfileError, match="does not exist"):
        store.set_parameter("My Profile", "suport_xy", "1")
    with pytest.raises(ProfileError, match="identifies the preset"):
        store.set_parameter("My Profile", "inherits", "x")
    assert store.set_parameter("My Profile", "brand_new_key", "1", force=True)["new_value"] == "1"


def test_backups_in_the_same_second_do_not_overwrite_and_restore_works(store):
    store.set_parameter("My Profile", "outer_wall_speed", "60")
    original_backup = store.list_backups("My Profile")[-1]

    result = store.restore_backup("My Profile", original_backup)  # backs up the edited state first
    assert result["backup_of_previous_state"]
    assert len(store.list_backups("My Profile")) == 2

    saved = json.loads(store.profile_path("My Profile").read_text(encoding="utf-8"))
    assert saved["outer_wall_speed"] == ["55"]


def test_restore_rejects_backups_of_other_presets(store):
    store.set_parameter("Clean", "wall_loops", "3", force=True)
    other = store.list_backups("Clean")[0]
    with pytest.raises(ProfileError, match="does not belong"):
        store.restore_backup("My Profile", other)


@pytest.mark.parametrize("raw, expected", [("0.2", 0.2), ("18%", 18.0), (["55"], 55.0), (None, None),
                                           ("gyroid", None), ([], None)])
def test_to_number(raw, expected):
    assert to_number(raw) == expected
