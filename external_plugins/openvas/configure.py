"""
Configuration de OpenVAS
"""

from typing import Any, Dict


class OpenVASConfigurator:
    async def configure(self, ctx, config: Dict[str, Any]) -> Dict[str, Any]:
        # OpenVAS se configure principalement via gvmd
        # Changer le mot de passe admin par défaut
        admin_password = config.get("admin_password", "admin")
        # Utiliser gvmd pour modifier l'utilisateur admin
        await ctx.executor.execute(
            f"gvmd --user=admin --new-password={admin_password}", sudo=True, timeout=30
        )
        # Redémarrer les services pour appliquer
        await ctx.executor.execute(
            "systemctl restart gvmd ospd-openvas gsad", sudo=True
        )
        return {"success": True}
