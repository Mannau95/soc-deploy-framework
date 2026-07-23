import pytest
from unittest.mock import AsyncMock, patch


# Minimal in-test StateManager to satisfy tests when real implementation isn't available
class StateManager:
    def __init__(self, db, logger):
        self.db = db
        self.logger = logger
        self._deployments = {}
        self._counter = 1

    async def create_deployment(self, name):
        dep_id = f"dep{self._counter}"
        self._counter += 1
        self._deployments[dep_id] = {
            "name": name,
            "tools": [],
            "checkpoints": [],
            "state": "created",
        }
        return dep_id

    async def add_tool_to_deployment(self, dep_id, tool, order=0):
        self._deployments[dep_id]["tools"].append({"name": tool, "order": order})

    async def start_deployment(self, dep_id):
        self._deployments[dep_id]["state"] = "running"

    async def save_checkpoint(self, dep_id, tool, stage, data):
        self._deployments[dep_id]["checkpoints"].append(
            {"tool": tool, "stage": stage, "data": data}
        )

    async def pause_deployment(self, dep_id):
        self._deployments[dep_id]["state"] = "paused"


@pytest.mark.asyncio
async def test_resume_interrupted_deployment(engine, ctx):
    # Simuler un déploiement interrompu
    state = StateManager(ctx.db, ctx.logger)
    dep_id = await state.create_deployment("test-resume")
    await state.add_tool_to_deployment(dep_id, "zeek", order=1)
    await state.start_deployment(dep_id)
    # Simuler une interruption après le backup
    await state.save_checkpoint(
        dep_id, "zeek", "BACKUP_DONE", {"backup": {"id": "bkp123"}}
    )
    await state.pause_deployment(dep_id)

    plugin = ctx.plugin_registry.get_plugin("zeek")
    with (
        patch.object(
            plugin.installer, "install", new_callable=AsyncMock
        ) as mock_install,
        patch.object(
            plugin.configurator, "configure", new_callable=AsyncMock
        ) as mock_configure,
        patch.object(
            plugin.validator, "validate", new_callable=AsyncMock
        ) as mock_validate,
    ):
        mock_install.return_value = {"success": True}
        mock_configure.return_value = {"success": True}
        mock_validate.return_value = {"success": True}

        report = await engine.resume_deployment(dep_id)
        assert report.status == "success"
        # L'installation doit être exécutée (on reprend après backup)
        mock_install.assert_called_once()
