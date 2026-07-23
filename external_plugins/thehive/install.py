class TheHiveInstaller:
    async def check_prerequisites(self, ctx):
        issues = []
        if not await ctx.executor.check_command_exists("java"):
            issues.append("Java requis (openjdk-11)")
        return {"success": len(issues) == 0, "issues": issues}

    async def install(self, ctx, options):
        # Installation via paquets Debian/Ubuntu
        pkg_url = "https://github.com/TheHive-Project/TheHive/releases/download/5.2.0/thehive_5.2.0-1_all.deb"
        await ctx.executor.execute(f"curl -sSfL {pkg_url} -o /tmp/thehive.deb")
        await ctx.executor.execute("dpkg -i /tmp/thehive.deb", sudo=True)
        await ctx.package_manager.install_packages(["openjdk-11-jre-headless"])
        await ctx.executor.execute(
            "systemctl enable thehive && systemctl start thehive", sudo=True
        )
        return {"success": True}

    async def uninstall(self, ctx):
        await ctx.executor.execute("systemctl stop thehive", sudo=True)
        await ctx.package_manager.remove_packages(["thehive"], purge=True)
        return {"success": True}

    async def update(self, ctx):
        # Télécharger la dernière version et l'installer
        return {"success": False, "error": "Mise à jour non implémentée"}
