"""
Tests du gestionnaire de paquets
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from soc_deploy.services.package import PackageManager, PackageManagerType
from soc_deploy.services.executor import CommandExecutor, CommandResult, ExecutionStatus


class TestPackageManager:
    """Tests du gestionnaire de paquets"""

    @pytest.fixture
    def mock_executor(self):
        executor = MagicMock(spec=CommandExecutor)
        executor.execute = AsyncMock()
        executor.check_command_exists = AsyncMock()
        return executor

    @pytest.fixture
    def package_manager(self, mock_executor):
        return PackageManager(mock_executor)

    @pytest.mark.asyncio
    async def test_detect_apt(self, package_manager, mock_executor):
        """Test la détection APT"""
        mock_executor.check_command_exists.return_value = True
        pm_type = await package_manager.detect_package_manager()
        assert pm_type == PackageManagerType.APT

    @pytest.mark.asyncio
    async def test_is_installed(self, package_manager, mock_executor):
        """Test la vérification d'installation"""
        package_manager._manager_type = PackageManagerType.APT
        mock_executor.execute.return_value = CommandResult(
            command="test",
            status=ExecutionStatus.SUCCESS,
            returncode=0,
            stdout="",
            stderr="",
            duration=0.1,
        )

        result = await package_manager.is_installed("curl")
        assert result

    @pytest.mark.asyncio
    async def test_install_packages(self, package_manager, mock_executor):
        """Test l'installation de paquets"""
        package_manager._manager_type = PackageManagerType.APT
        mock_executor.execute.return_value = CommandResult(
            command="test",
            status=ExecutionStatus.SUCCESS,
            returncode=0,
            stdout="",
            stderr="",
            duration=1.0,
        )
        mock_executor.execute_with_retry = AsyncMock(
            return_value=CommandResult(
                command="test",
                status=ExecutionStatus.SUCCESS,
                returncode=0,
                stdout="",
                stderr="",
                duration=1.0,
            )
        )

        result = await package_manager.install_packages(["curl", "wget"])
        assert result.success
        assert "curl" in result.installed
        assert "wget" in result.installed
