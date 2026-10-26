from creality_print_mcp.audit import audit


def test_audit_uses_inherited_values_and_reports_origin(store):
    findings = {f["key"]: f for f in audit(store.resolve("My Profile"))}
    assert set(findings) == {
        "sparse_infill_pattern",  # grid, inherited
        "support_top_z_distance",  # 0.1 with 0.2 layers -> fuses
        "support_object_xy_distance",  # 0.35, inherited
        "top_bottom_infill_wall_overlap",  # 30%, user override
        "support_interface_spacing",  # 0.5, inherited
    }
    assert findings["support_top_z_distance"]["severity"] == "HIGH"
    assert findings["top_bottom_infill_wall_overlap"]["origin"] == "user preset"
    assert findings["sparse_infill_pattern"]["origin"].startswith("inherited from")


def test_audit_clean_profile_has_no_findings(store):
    assert audit(store.resolve("Clean")) == []


def test_audit_skips_missing_values_instead_of_inventing_defaults(store):
    assert audit(store.resolve("Orphan")) == []
