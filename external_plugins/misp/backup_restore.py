from soc_deploy.services.backup import BackupTarget, BackupType


class MispBackupRestore:
    async def backup(self, ctx):
        target = BackupTarget(
            paths=["/var/www/MISP/app/Config"],
            tool_name="misp",
            backup_type=BackupType.CONFIG,
        )
        backup = await ctx.backup_manager.create_backup(target)
        return {
            "success": backup is not None,
            "backup_id": backup.id if backup else None,
        }

    async def restore(self, ctx, backup_data):
        backup_id = backup_data.get("backup_id")
        if not backup_id:
            return {"success": False, "error": "backup_id manquant"}
        backup = ctx.backup_manager.get_backup("misp", backup_id)
        if not backup:
            return {"success": False, "error": "Sauvegarde introuvable"}
        ok = await ctx.backup_manager.restore_backup(
            backup, {"Config": "/var/www/MISP/app/Config"}
        )
        return {"success": ok}
