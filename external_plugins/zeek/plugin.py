"""
Plugin Zeek – Analyse réseau et logs
"""

from soc_deploy.plugins.base import PluginBase, PluginMetadata
from .install import ZeekInstaller
from .configure import ZeekConfigurator
from .validate import ZeekValidator
from .backup_restore import ZeekBackupRestore


class ZeekPlugin(PluginBase):
    meta = PluginMetadata(
        name="zeek",
        version="6.0.0",
        description="Zeek (anciennement Bro) – Analyse réseau et logging",
        author="SOC Deploy Community",
        min_system_requirements={"cpu": 2, "ram_gb": 2, "disk_gb": 5},
        tags=["network", "logging", "nsm"],
    )

    def __init__(self):
        self.installer = ZeekInstaller()
        self.configurator = ZeekConfigurator()
        self.validator = ZeekValidator()
        self.backup_restore = ZeekBackupRestore()

    async def check_prerequisites(self, ctx):
        return await self.installer.check_prerequisites(ctx)

    async def get_deployment_options(self, ctx):
        return {
            "interface": {
                "type": "text",
                "message": "Interface à écouter",
                "default": "eth0",
            },
            "cluster": {
                "type": "confirm",
                "message": "Déployer en mode cluster (Zeek cluster) ?",
                "default": False,
            },
        }

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
