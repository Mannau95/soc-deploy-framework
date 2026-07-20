"""
Tests du service d'exécution de commandes
"""

import pytest
from soc_deploy.services.executor import CommandExecutor, ExecutionStatus
from soc_deploy.utils.logger import LoggerManager


class TestCommandExecutor:
    """Tests de l'exécuteur de commandes"""

    @pytest.fixture
    def logger(self, temp_dir):
        return LoggerManager(temp_dir)

    @pytest.fixture
    def executor(self, logger):
        return CommandExecutor(logger)

    @pytest.mark.asyncio
    async def test_execute_simple_command(self, executor):
        """Test l'exécution d'une commande simple"""
        result = await executor.execute("echo 'test'")
        assert result.status == ExecutionStatus.SUCCESS
        assert result.returncode == 0
        assert "test" in result.stdout

    @pytest.mark.asyncio
    async def test_execute_failed_command(self, executor):
        """Test l'exécution d'une commande qui échoue"""
        result = await executor.execute("ls /nonexistent")
        assert result.status == ExecutionStatus.FAILED
        assert result.returncode != 0

    @pytest.mark.asyncio
    async def test_execute_timeout(self, executor):
        """Test le timeout d'exécution"""
        result = await executor.execute("sleep 10", timeout=1)
        assert result.status == ExecutionStatus.TIMEOUT

    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self, executor):
        """Test l'exécution avec retry qui réussit"""
        result = await executor.execute_with_retry("echo 'ok'", retries=3)
        assert result.status == ExecutionStatus.SUCCESS
        assert result.attempts == 1

    @pytest.mark.asyncio
    async def test_check_command_exists(self, executor):
        """Test la vérification d'existence d'une commande"""
        assert await executor.check_command_exists("echo")
        assert await executor.check_command_exists("nonexistent_command_xyz")
