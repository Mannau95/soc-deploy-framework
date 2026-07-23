"""
Tests du gestionnaire de base de données
"""

import tempfile
from pathlib import Path

import pytest

from soc_deploy.database.manager import DatabaseManager
from soc_deploy.utils.logger import LoggerManager


@pytest.mark.asyncio
class TestDatabaseManager:
    @pytest.fixture(autouse=True)
    async def setup(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "state.db"
        self.logger = LoggerManager(Path(self.tmp_dir.name) / "logs")
        self.db = DatabaseManager(self.db_path, self.logger)
        await self.db.initialize()
        yield
        await self.db.close()
        self.tmp_dir.cleanup()

    async def test_create_deployment(self):
        result = await self.db.create_deployment("dep1", "Test SOC", "small")
        assert result
        dep = await self.db.get_deployment("dep1")
        assert dep["name"] == "Test SOC"
        assert dep["status"] == "PLANNED"

    async def test_add_tool(self):
        await self.db.create_deployment("dep2", "Test")
        added = await self.db.add_deployment_tool("dep2", "wazuh", "4.7.0", 1)
        assert added
        tools = await self.db.get_deployment_tools("dep2")
        assert len(tools) == 1
        assert tools[0]["tool_name"] == "wazuh"

    async def test_save_checkpoint(self):
        await self.db.create_deployment("dep3", "Test")
        cid = await self.db.save_checkpoint("dep3", "wazuh", "INSTALL", {"progress": 50})
        assert cid is not None
        checkpoint = await self.db.get_last_checkpoint("dep3", "wazuh", "INSTALL")
        assert checkpoint["state_data"]["progress"] == 50

    async def test_log_event(self):
        await self.db.create_deployment("dep4", "Test")
        ok = await self.db.log_event("dep4", "INFO", "Démarrage installation", "wazuh")
        assert ok
