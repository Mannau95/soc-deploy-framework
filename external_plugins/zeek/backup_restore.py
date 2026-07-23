from soc_deploy.services.backup import BackupTarget, BackupType


class ZeekBackupRestore:
    async def backup(self, ctx):
        target = BackupTarget(
            paths=["/opt/zeek/etc", "/opt/zeek/share/zeek/site"],
            tool_name="zeek",
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
        backup = ctx.backup_manager.get_backup("zeek", backup_id)
        if not backup:
            return {"success": False, "error": "Sauvegarde introuvable"}
        restore_paths = {
            "etc": "/opt/zeek/etc",
            "site": "/opt/zeek/share/zeek/site",
        }
        ok = await ctx.backup_manager.restore_backup(backup, restore_paths)
        if ok:
            await ctx.executor.execute("zeekctl deploy", timeout=30)
        return {"success": ok}
