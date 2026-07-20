"""
Tests du service de sauvegarde
"""

import pytest
import tempfile
from pathlib import Path
from soc_deploy.services.backup import BackupManager, BackupTarget, BackupType
from soc_deploy.utils.logger import LoggerManager


class TestBackupManager:
    @pytest.fixture
    def temp_backup_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def logger(self, temp_backup_dir):
        return LoggerManager(temp_backup_dir / "logs")

    @pytest.fixture
    def manager(self, temp_backup_dir, logger):
        return BackupManager(temp_backup_dir, logger)

    @pytest.mark.asyncio
    async def test_create_and_list_backup(self, manager, tmp_path):
        # Créer un fichier à sauvegarder
        test_file = tmp_path / "test.conf"
        test_file.write_text("config data")

        target = BackupTarget(
            paths=[test_file],
            tool_name="wazuh",
            backup_type=BackupType.CONFIG,
        )

        backup = await manager.create_backup(target)
        assert backup is not None
        assert backup.tool_name == "wazuh"
        assert backup.backup_type == BackupType.CONFIG
        assert backup.path.exists()

        # Vérifier la liste
        backups = manager.list_backups("wazuh")
        assert len(backups) == 1
        assert backups[0].id == backup.id

    @pytest.mark.asyncio
    async def test_restore_backup(self, manager, tmp_path):
        # Sauvegarde
        original = tmp_path / "original.txt"
        original.write_text("hello world")

        target = BackupTarget(
            paths=[original], tool_name="test", backup_type=BackupType.CUSTOM
        )
        backup = await manager.create_backup(target)

        # Modifier le fichier
        original.write_text("modified")

        # Restaurer
        restore_paths = {"original.txt": str(original)}
        success = await manager.restore_backup(backup, restore_paths)
        assert success
        assert original.read_text() == "hello world"

    def test_cleanup_old_backups(self, manager, tmp_path):
        # Créer plusieurs sauvegardes rapidement
        import asyncio

        async def create_multiple():
            for i in range(7):
                test_file = tmp_path / f"file{i}.txt"
                test_file.write_text(f"data{i}")
                target = BackupTarget(
                    paths=[test_file],
                    tool_name="cleanup",
                    backup_type=BackupType.CUSTOM,
                )
                await manager.create_backup(target)

        asyncio.run(create_multiple())

        backups_before = len(manager.list_backups("cleanup"))
        removed = manager.cleanup_old_backups("cleanup", keep=3)
        backups_after = len(manager.list_backups("cleanup"))

        assert backups_before == 7
        assert removed == 4
        assert backups_after == 3
