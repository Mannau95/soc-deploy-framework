class CortexInstaller:
    async def check_prerequisites(self, ctx):
        issues = []
        if not await ctx.executor.check_command_exists("java"):
            issues.append("Java 11+ requis")
        return {"success": len(issues) == 0, "issues": issues}

    async def install(self, ctx, options):
        url = "https://github.com/TheHive-Project/Cortex/releases/download/3.1.4/cortex_3.1.4-1_all.deb"
        await ctx.executor.execute(f"curl -sSfL {url} -o /tmp/cortex.deb")
        await ctx.executor.execute("dpkg -i /tmp/cortex.deb", sudo=True)
        await ctx.package_manager.install_packages(["openjdk-11-jre-headless"])
        await ctx.executor.execute(
            "systemctl enable cortex && systemctl start cortex", sudo=True
        )
        return {"success": True}

    async def uninstall(self, ctx):
        await ctx.executor.execute("systemctl stop cortex", sudo=True)
        await ctx.package_manager.remove_packages(["cortex"], purge=True)
        return {"success": True}

    async def update(self, ctx):
        return {"success": False, "error": "Non implémenté"}
