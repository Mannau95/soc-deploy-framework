"""
Tests de l'orchestrateur principal
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from soc_deploy.core.context import ExecutionContext
from soc_deploy.core.engine import Orchestrator
from soc_deploy.core.state import StateManager
from soc_deploy.plugins.base import PluginBase


class MockPlugin(PluginBase):
    name = "mock"
    version = "1.0"
    description = "Mock"
    dependencies = []
    required_plugins = []

    async def check_prerequisites(self, ctx):
        return {"success": True}

    async def get_deployment_options(self, ctx):
        return {}

    async def install(self, ctx, options):
        return {"success": True}

    async def configure(self, ctx, config):
        return {"success": True}

    async def validate(self, ctx):
        return {"success": True}

    async def update(self, ctx):
        return {"success": True}

    async def backup(self, ctx):
        return {"id": "bkp1"}

    async def restore(self, ctx, backup_data):
        return {"success": True}

    async def rollback(self, ctx):
        return {"success": True}

    async def uninstall(self, ctx):
        return {"success": True}

    async def health_check(self, ctx):
        return {"status": "ok"}


@pytest.fixture
def mock_ctx():
    ctx = MagicMock(spec=ExecutionContext)
    ctx.interactive = False
    ctx.system_checker.run_all_checks.return_value = []
    ctx.plugin_registry.get_plugin.return_value = MockPlugin()
    ctx.get_logger.return_value = MagicMock()
    return ctx


@pytest.fixture
def mock_state():
    state = MagicMock(spec=StateManager)
    state.create_deployment = AsyncMock(return_value="dep123")
    state.start_deployment = AsyncMock(return_value=True)
    state.add_tool_to_deployment = AsyncMock(return_value=True)
    state.set_tool_status = AsyncMock(return_value=True)
    state.complete_deployment = AsyncMock(return_value=True)
    state.fail_deployment = AsyncMock(return_value=True)
    state.save_checkpoint = AsyncMock(return_value="ckpt1")
    return state


@pytest.mark.asyncio
async def test_deploy_soc_success(mock_ctx, mock_state):
    orchestrator = Orchestrator(mock_ctx, mock_state)
    report = await orchestrator.deploy_soc(["mock"], interactive=False)
    assert report.status == "success"
    assert len(report.tools) == 1
    assert report.tools[0].status == "success"
    mock_state.complete_deployment.assert_called_once()


@pytest.mark.asyncio
async def test_deploy_soc_failure(mock_ctx, mock_state):
    # Plugin qui échoue à l'installation
    failing_plugin = MockPlugin()
    failing_plugin.install = AsyncMock(return_value={"success": False, "error": "test"})
    mock_ctx.plugin_registry.get_plugin.return_value = failing_plugin

    orchestrator = Orchestrator(mock_ctx, mock_state)
    report = await orchestrator.deploy_soc(["mock"], interactive=False)
    assert report.status == "partial_failure"
    mock_state.fail_deployment.assert_called_once()
