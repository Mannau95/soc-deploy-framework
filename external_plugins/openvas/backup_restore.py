"""
Sauvegarde et restauration de OpenVAS
"""

from soc_deploy.services.backup import BackupTarget, BackupType


class OpenVASBackupRestore:
    async def backup(self, ctx):
        # Sauvegarder les configurations et la base PostgreSQL de GVM
        target = BackupTarget(
            paths=["/etc/gvm", "/var/lib/gvm"],
            tool_name="openvas",
            backup_type=BackupType.FULL,
        )
        backup = await ctx.backup_manager.create_backup(target)
        if backup:
            # Optionnel : exporter aussi la base de données
            await ctx.executor.execute(
                "sudo -u postgres pg_dump gvmd > /tmp/gvmd_backup.sql", timeout=60
            )
        return {
            "success": backup is not None,
            "backup_id": backup.id if backup else None,
        }

    async def restore(self, ctx, backup_data):
        backup_id = backup_data.get("backup_id")
        if not backup_id:
            return {"success": False, "error": "backup_id manquant"}
        backup = ctx.backup_manager.get_backup("openvas", backup_id)
        if not backup:
            return {"success": False, "error": "Sauvegarde introuvable"}
        # Restaurer les fichiers de configuration
        restore_paths = {"gvm": "/etc/gvm", "lib": "/var/lib/gvm"}
        ok = await ctx.backup_manager.restore_backup(backup, restore_paths)
        if ok:
            # Restaurer la base de données si le dump existe
            await ctx.executor.execute(
                "sudo -u postgres psql gvmd < /tmp/gvmd_backup.sql", timeout=60
            )
            await ctx.executor.execute(
                "systemctl restart gvmd ospd-openvas gsad", sudo=True
            )
        return {"success": ok}
