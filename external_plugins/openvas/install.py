class OpenVASInstaller:
    async def check_prerequisites(self, ctx):
        return {"success": True, "issues": []}

    async def install(self, ctx, options):
        # Sur Ubuntu 22.04, installation via les dépôts Greenbone
        await ctx.executor.execute("add-apt-repository -y ppa:mrazavi/gvm", sudo=True)
        await ctx.package_manager.install_packages(["gvm"], update_first=True)
        # Configuration initiale
        await ctx.executor.execute("gvm-setup", timeout=600, sudo=True)
        return {"success": True}

    async def uninstall(self, ctx):
        await ctx.package_manager.remove_packages(["gvm"], purge=True)
        return {"success": True}

    async def update(self, ctx):
        return {"success": True}
