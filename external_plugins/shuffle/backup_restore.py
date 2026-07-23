"""
Sauvegarde et restauration de Shuffle (volumes Docker)
"""

from pathlib import Path


class ShuffleBackupRestore:
    async def backup(self, ctx):
        # Shuffle stocke ses données dans des volumes Docker, on sauvegarde via tar
        # Sauvegarde des volumes : shuffle_backend_data, shuffle_frontend_data
        volumes = ["shuffle_backend_data", "shuffle_frontend_data"]
        backup_dir = ctx.backup_manager.backup_root / "shuffle"
        backup_dir.mkdir(parents=True, exist_ok=True)

        import uuid

        backup_id = f"shuffle_{uuid.uuid4().hex[:8]}"
        backup_dir / f"{backup_id}.tar.gz"

        # Exporter les volumes avec docker run
        for vol in volumes:
            await ctx.executor.execute(
                f"docker run --rm -v {vol}:/volume -v {backup_dir}:/backup alpine tar czf /backup/{vol}.tar.gz -C /volume .",
                timeout=60,
            )
        # Créer une archive unique (simplifié : on liste les tar.gz)
        # On enregistre simplement les chemins
        return {"success": True, "backup_id": backup_id, "volumes": volumes}

    async def restore(self, ctx, backup_data):
        backup_id = backup_data.get("backup_id")
        if not backup_id:
            return {"success": False, "error": "backup_id manquant"}
        backup_dir = ctx.backup_manager.backup_root / "shuffle"
        volumes = ["shuffle_backend_data", "shuffle_frontend_data"]
        # Restaurer les volumes depuis les archives
        for vol in volumes:
            archive = backup_dir / f"{vol}.tar.gz"
            if archive.exists():
                await ctx.executor.execute(
                    f"docker run --rm -v {vol}:/volume -v {backup_dir}:/backup alpine tar xzf /backup/{vol}.tar.gz -C /volume",
                    timeout=60,
                )
        # Redémarrer les conteneurs
        await ctx.docker_manager.compose_up(
            Path("/tmp/shuffle-compose.yml"), detach=True
        )
        return {"success": True}
