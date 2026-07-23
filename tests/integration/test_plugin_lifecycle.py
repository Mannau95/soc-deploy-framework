import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_wazuh_install_simulation(engine, ctx):
    """
    Test d'intégration : déploiement simulé du plugin Wazuh
    On mock les appels système pour ne rien modifier.
    """
    # Simuler le plugin wazuh
    plugin = ctx.plugin_registry.get_plugin("wazuh")
    assert plugin is not None

    # Mock des méthodes qui interagissent avec le système
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

        # Lancer l'installation
        report = await engine.install_single_tool(
            "wazuh",
            {"architecture": "all-in-one", "installation_method": "packages"},
            interactive=False,
        )

        assert report.status == "success"
        mock_install.assert_called_once()
        mock_configure.assert_called_once()
        mock_validate.assert_called_once()


@pytest.mark.asyncio
async def test_rollback_on_failure(engine, ctx):
    """Si l'installation échoue, le rollback doit être appelé"""
    plugin = ctx.plugin_registry.get_plugin("suricata")
    with (
        patch.object(
            plugin.installer, "install", new_callable=AsyncMock
        ) as mock_install,
        patch.object(plugin, "rollback", new_callable=AsyncMock) as mock_rollback,
        patch.object(
            plugin.validator, "validate", new_callable=AsyncMock
        ) as mock_validate,
    ):
        mock_install.return_value = {"success": False, "error": "Test failure"}
        mock_rollback.return_value = {"success": True}
        mock_validate.return_value = {"success": True}  # on n'arrive pas jusque là

        report = await engine.install_single_tool("suricata", {}, interactive=False)
        assert report.status == "failed"
        mock_rollback.assert_called_once()
