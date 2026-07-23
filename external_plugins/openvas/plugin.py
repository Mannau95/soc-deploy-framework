from soc_deploy.plugins.base import PluginBase, PluginMetadata

from .backup_restore import OpenVASBackupRestore
from .configure import OpenVASConfigurator
from .install import OpenVASInstaller
from .validate import OpenVASValidator


class OpenVASPlugin(PluginBase):
    meta = PluginMetadata(
        name="openvas",
        version="22.4",
        description="OpenVAS / Greenbone Vulnerability Scanner",
        min_system_requirements={"cpu": 4, "ram_gb": 8, "disk_gb": 30},
        tags=["vulnerability", "scanner"],
    )

    def __init__(self):
        self.installer = OpenVASInstaller()
        self.configurator = OpenVASConfigurator()
        self.validator = OpenVASValidator()
        self.backup_restore = OpenVASBackupRestore()

    async def check_prerequisites(self, ctx):
        return await self.installer.check_prerequisites(ctx)

    async def get_deployment_options(self, ctx):
        return {}

    async def install(self, ctx, options):
        return await self.installer.install(ctx, options)

    async def configure(self, ctx, config):
        return await self.configurator.configure(ctx, config)

    async def validate(self, ctx):
        return await self.validator.validate(ctx)

    async def backup(self, ctx):
        return await self.backup_restore.backup(ctx)

    async def restore(self, ctx, backup_data):
        return await self.backup_restore.restore(ctx, backup_data)

    async def rollback(self, ctx):
        return await self.uninstall(ctx)

    async def uninstall(self, ctx):
        return await self.installer.uninstall(ctx)

    async def update(self, ctx):
        return await self.installer.update(ctx)

    async def health_check(self, ctx):
        return await self.validator.health_check(ctx)
