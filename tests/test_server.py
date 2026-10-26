"""End-to-end: start the server over stdio, as an MCP client would."""

import json
import os
import sys

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

EXPECTED_TOOLS = {
    "list_profiles", "get_profile", "audit_profile", "set_profile_parameter", "list_backups", "restore_backup",
    "get_model_dimensions", "scale_model", "rotate_model",
}


def _text(result) -> str:
    return result.content[0].text


def test_stdio_end_to_end(config_dir, tmp_path):
    env = {**os.environ, "SLICER_CONFIG_DIR": str(config_dir),
           "CREALITY_PRINT_MCP_BACKUP_DIR": str(tmp_path / "backups")}
    params = StdioServerParameters(command=sys.executable, args=["-m", "creality_print_mcp"], env=env)

    async def run():
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()

            tools = {t.name: t for t in (await session.list_tools()).tools}
            assert set(tools) == EXPECTED_TOOLS
            assert tools["audit_profile"].annotations.read_only_hint is True
            assert tools["set_profile_parameter"].annotations.destructive_hint is True

            audit = json.loads(_text(await session.call_tool("audit_profile", {"name": "My Profile"})))
            assert audit["finding_count"] == 5

            edit = json.loads(_text(await session.call_tool(
                "set_profile_parameter", {"name": "My Profile", "key": "outer_wall_speed", "value": "60"})))
            assert edit["new_value"] == ["60"]

            failure = await session.call_tool("get_profile", {"name": "../etc"})
            assert failure.is_error is True
            assert "Invalid preset name" in _text(failure)

    anyio.run(run)
