"""
Sauvegarde et restauration des configurations et données Wazuh
"""

from typing import Any, Dict
from dataclasses import dataclass
from enum import Enum


class BackupType(Enum):
    CONFIG = "config"


@dataclass
class BackupTarget:
    paths: list
    tool_name: str
    backup_type: BackupType


class WazuhBackupRestore:
    async def backup(self, ctx) -> Dict[str, Any]:
        # Sauvegarder /var/ossec/etc, /etc/wazuh-indexer, /etc/wazuh-dashboard
        target = BackupTarget(
            paths=["/var/ossec/etc", "/etc/wazuh-indexer", "/etc/wazuh-dashboard"],
            tool_name="wazuh",
            backup_type=BackupType.CONFIG,
        )
        backup = await ctx.backup_manager.create_backup(target)
        return {
            "success": backup is not None,
            "backup_id": backup.id if backup else None,
        }

    async def restore(self, ctx, backup_data: Dict[str, Any]) -> Dict[str, Any]:
        backup_id = backup_data.get("backup_id")
        if not backup_id:
            return {"success": False, "error": "backup_id manquant"}
        backup = ctx.backup_manager.get_backup("wazuh", backup_id)
        if not backup:
            return {"success": False, "error": "Sauvegarde introuvable"}
        # Restaurer les répertoires de configuration
        restore_paths = {
            "etc": "/var/ossec/etc",
            "wazuh-indexer": "/etc/wazuh-indexer",
            "wazuh-dashboard": "/etc/wazuh-dashboard",
        }
        ok = await ctx.backup_manager.restore_backup(backup, restore_paths)
        if ok:
            # Redémarrer les services
            await ctx.executor.execute(
                "systemctl restart wazuh-manager wazuh-indexer wazuh-dashboard",
                sudo=True,
            )
        return {"success": ok}
