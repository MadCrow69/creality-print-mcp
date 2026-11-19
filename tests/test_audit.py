from creality_print_mcp.audit import audit


def test_audit_uses_inherited_values_and_reports_origin(store):
    findings = {f["key"]: f for f in audit(store.resolve("My Profile"))}
    assert set(findings) == {
        "sparse_infill_pattern",  # grid, inherited
        "support_top_z_distance",  # 0.1 with 0.2 layers -> fuses
        "support_object_xy_distance",  # 0.35, inherited
        "top_bottom_infill_wall_overlap",  # 30%, user override
    }
    assert findings["support_top_z_distance"]["severity"] == "HIGH"
    assert findings["top_bottom_infill_wall_overlap"]["origin"] == "user preset"
    assert findings["sparse_infill_pattern"]["origin"].startswith("inherited from")


def test_vendor_default_interface_spacing_is_not_a_finding(store):
    # 0.5 mm is the vendor default; flagging it pushed presets toward dense interfaces that weld to the part.
    keys = {f["key"] for f in audit(store.resolve("My Profile"))}
    assert "support_interface_spacing" not in keys


def test_audit_flags_supports_that_are_hard_to_remove(store):
    findings = {f["key"]: f for f in audit(store.resolve("Hard To Remove"))}
    assert set(findings) == {"support_interface_pattern", "support_interface_spacing", "tree_support_wall_count"}
    assert {f["area"] for f in findings.values()} == {"Support removal"}
    assert findings["support_interface_pattern"]["origin"] == "user preset"


def test_tree_wall_count_ignored_for_normal_supports_and_solid_interface_flagged(store):
    findings = {f["key"]: f for f in audit(store.resolve("Normal Supports"))}
    assert set(findings) == {"support_interface_spacing"}  # 0 = solid interface
    assert findings["support_interface_spacing"]["current_value"] == "0"


def test_audit_clean_profile_has_no_findings(store):
    assert audit(store.resolve("Clean")) == []


def test_audit_skips_missing_values_instead_of_inventing_defaults(store):
    assert audit(store.resolve("Orphan")) == []
