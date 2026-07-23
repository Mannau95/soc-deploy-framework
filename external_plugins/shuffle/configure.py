"""
Configuration de Shuffle (via variables d'environnement Docker)
"""

from pathlib import Path
from typing import Any, Dict


class ShuffleConfigurator:
    async def configure(self, ctx, config: Dict[str, Any]) -> Dict[str, Any]:
        # Shuffle se configure principalement via variables d'environnement au moment du docker-compose
        # Ici, on pourrait régénérer le fichier docker-compose avec les nouvelles variables
        # et redéployer, mais pour simplifier on modifie les conteneurs existants (limité).
        config.get("email", "admin@shuffle.local")
        config.get("admin_password", "admin")
        # Arrêt, mise à jour des variables et redémarrage
        await ctx.executor.execute(
            "docker stop shuffle-backend shuffle-frontend", sudo=True
        )
        await ctx.executor.execute(
            "docker rm shuffle-backend shuffle-frontend", sudo=True
        )

        compose_file = Path("/tmp/shuffle-compose.yml")
        if compose_file.exists():
            await ctx.docker_manager.compose_up(compose_file, detach=True)
        else:
            # Si le compose n'existe plus, on ne peut pas appliquer la config directement
            return {
                "success": False,
                "error": "Fichier docker-compose introuvable, configuration impossible",
            }

        return {"success": True}
