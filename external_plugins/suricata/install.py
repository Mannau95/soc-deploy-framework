"""
Installation de Suricata (paquets ou sources simplifié)
"""

from typing import Any, Dict


class SuricataInstaller:
    async def check_prerequisites(self, ctx) -> Dict[str, Any]:
        issues = []
        # Vérifier la présence de libpcap, libnetfilter-queue (pour IPS)
        if not await ctx.executor.check_command_exists("suricata"):
            issues.append("Suricata n'est pas installé (sera installé)")
        return {"success": len(issues) == 0, "issues": issues}

    async def install(self, ctx, options: Dict[str, Any]) -> Dict[str, Any]:
        # Détection de la distribution pour l'installation
        pm = ctx.package_manager
        await pm.update_repositories()
        # Suricata est généralement dans les dépôts officiels Ubuntu/Debian
        result = await pm.install_packages(["suricata"], update_first=False)
        if not result.success:
            return {"success": False, "error": result.errors}
        # Activer et démarrer le service
        await ctx.executor.execute("systemctl enable suricata", sudo=True)
        await ctx.executor.execute("systemctl start suricata", sudo=True)
        return {"success": True}

    async def uninstall(self, ctx) -> Dict[str, Any]:
        await ctx.executor.execute("systemctl stop suricata", sudo=True)
        await ctx.package_manager.remove_packages(["suricata"], purge=True)
        return {"success": True}

    async def update(self, ctx) -> Dict[str, Any]:
        await ctx.package_manager.update_repositories()
        result = await ctx.package_manager.install_packages(
            ["suricata"], update_first=False
        )
        return {"success": result.success}
