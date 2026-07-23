"""
Tests d'intégration : rollback automatique en cas d'échec
"""

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_rollback_on_install_failure(engine, ctx):
    """Si l'installation échoue, le rollback est appelé et le déploiement marqué comme échoué"""
    plugin = ctx.plugin_registry.get_plugin("suricata")
    assert plugin is not None

    with (
        patch.object(plugin.installer, "install", new_callable=AsyncMock) as mock_install,
        patch.object(plugin, "rollback", new_callable=AsyncMock) as mock_rollback,
    ):
        mock_install.return_value = {"success": False, "error": "Erreur simulée"}
        mock_rollback.return_value = {"success": True}

        report = await engine.install_single_tool("suricata", {}, interactive=False)
        assert report.status == "failed"
        mock_rollback.assert_called_once()

        # Vérifier dans la base que l'outil est marqué comme échoué
        deployments = await ctx.db.list_deployments()
        assert len(deployments) == 1
        tools = await ctx.db.get_deployment_tools(deployments[0]["id"])
        assert tools[0]["status"] == "FAILED"


@pytest.mark.asyncio
async def test_rollback_not_called_on_success(engine, ctx):
    """En cas de succès, le rollback ne doit pas être appelé"""
    plugin = ctx.plugin_registry.get_plugin("zeek")
    with (
        patch.object(plugin.installer, "install", new_callable=AsyncMock) as mock_install,
        patch.object(plugin, "rollback", new_callable=AsyncMock) as mock_rollback,
        patch.object(plugin.configurator, "configure", new_callable=AsyncMock) as mock_configure,
        patch.object(plugin.validator, "validate", new_callable=AsyncMock) as mock_validate,
    ):
        mock_install.return_value = {"success": True}
        mock_configure.return_value = {"success": True}
        mock_validate.return_value = {"success": True}

        report = await engine.install_single_tool("zeek", {}, interactive=False)
        assert report.status == "success"
        mock_rollback.assert_not_called()
