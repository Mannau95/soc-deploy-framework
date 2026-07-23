"""
Installation de Zeek (via paquets Zeek repository)
"""

from typing import Any, Dict


class ZeekInstaller:
    async def check_prerequisites(self, ctx) -> Dict[str, Any]:
        issues = []
        if not await ctx.executor.check_command_exists("zeek"):
            issues.append("Zeek n'est pas installé")
        return {"success": len(issues) == 0, "issues": issues}

    async def install(self, ctx, options: Dict[str, Any]) -> Dict[str, Any]:
        # Ajouter le dépôt officiel Zeek (Ubuntu/Debian)
        distro = ctx.system_info.distro.lower()
        if distro in ["ubuntu", "debian"]:
            await ctx.executor.execute(
                "curl -fsSL https://download.zeek.org/zeek-6.0.0/zeek-6.0.0-debian11_amd64.deb -o /tmp/zeek.deb",
                timeout=120,
            )
            await ctx.executor.execute("dpkg -i /tmp/zeek.deb", sudo=True)
        else:
            return {
                "success": False,
                "error": "Installation automatique uniquement sur Debian/Ubuntu pour le moment",
            }

        # Démarrer Zeek automatiquement avec systemd (si un service est créé)
        # Par défaut Zeek ne s'installe pas comme un service, on peut le configurer ensuite
        return {"success": True}

    async def uninstall(self, ctx) -> Dict[str, Any]:
        await ctx.package_manager.remove_packages(["zeek"], purge=True)
        return {"success": True}

    async def update(self, ctx) -> Dict[str, Any]:
        # Mise à jour par téléchargement du nouveau paquet
        return {"success": False, "error": "Mise à jour non implémentée"}
