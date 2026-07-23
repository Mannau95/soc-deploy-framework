from soc_deploy.services.backup import BackupTarget, BackupType


class TheHiveBackupRestore:
    async def backup(self, ctx):
        target = BackupTarget(
            paths=["/etc/thehive"], tool_name="thehive", backup_type=BackupType.CONFIG
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
        backup = ctx.backup_manager.get_backup("thehive", backup_id)
        if not backup:
            return {"success": False, "error": "Sauvegarde introuvable"}
        ok = await ctx.backup_manager.restore_backup(
            backup, {"thehive": "/etc/thehive"}
        )
        if ok:
            await ctx.executor.execute("systemctl restart thehive", sudo=True)
        return {"success": ok}
