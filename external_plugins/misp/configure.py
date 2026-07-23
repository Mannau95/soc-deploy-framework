from typing import Any, Dict


class MispConfigurator:
    async def configure(self, ctx, config: Dict[str, Any]) -> Dict[str, Any]:
        # Génération de la configuration avec Jinja2 (server.php, database.php, etc.)
        # Exemple simplifié : on écrit les variables d'environnement ou on utilise la commande de configuration
        base_url = config.get("base_url", "http://localhost")
        email = config.get("email", "admin@localhost.local")
        # Commande de configuration MISP
        await ctx.executor.execute(
            f"sudo -u www-data /var/www/MISP/app/Console/cake Baseurl {base_url}",
            timeout=30,
        )
        await ctx.executor.execute(
            f"sudo -u www-data /var/www/MISP/app/Console/cake AdminSetting set MISP.email {email}",
            timeout=30,
        )
        return {"success": True}
