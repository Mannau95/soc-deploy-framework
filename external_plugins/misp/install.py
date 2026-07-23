from typing import Any, Dict


class MispInstaller:
    async def check_prerequisites(self, ctx) -> Dict[str, Any]:
        issues = []
        if not await ctx.executor.check_command_exists("git"):
            issues.append("git requis")
        return {"success": len(issues) == 0, "issues": issues}

    async def install(self, ctx, options: Dict[str, Any]) -> Dict[str, Any]:
        # Utilisation du script d'installation officiel MISP (simplifié)
        # Note: l'installation réelle est complexe, ici on utilise un script automatisé
        script_url = (
            "https://raw.githubusercontent.com/MISP/MISP/2.4/INSTALL/INSTALL.sh"
        )
        script_path = "/tmp/install_misp.sh"
        await ctx.executor.execute(f"curl -sSfL {script_url} -o {script_path}")
        await ctx.executor.execute(f"bash {script_path} -A", timeout=1800, sudo=True)
        # Post-install : configuration de base via le playbook ou commandes cake
        return {"success": True}

    async def uninstall(self, ctx) -> Dict[str, Any]:
        # Pas de désinstallation simple, on nettoie les services et les fichiers
        await ctx.executor.execute("systemctl stop misp-workers 2>/dev/null", sudo=True)
        await ctx.executor.execute("rm -rf /var/www/MISP", sudo=True)
        return {"success": True}

    async def update(self, ctx) -> Dict[str, Any]:
        # Mise à jour via git pull
        await ctx.executor.execute(
            "cd /var/www/MISP && git pull origin 2.4", timeout=120
        )
        return {"success": True}
