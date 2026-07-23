from soc_deploy.plugins.base import PluginBase, PluginMetadata

from .backup_restore import TheHiveBackupRestore
from .configure import TheHiveConfigurator
from .install import TheHiveInstaller
from .validate import TheHiveValidator


class TheHivePlugin(PluginBase):
    meta = PluginMetadata(
        name="thehive",
        version="5.2.0",
        description="TheHive – Plateforme de réponse aux incidents",
        min_system_requirements={"cpu": 2, "ram_gb": 4, "disk_gb": 20},
        tags=["incident-response", "case-management"],
    )

    def __init__(self):
        self.installer = TheHiveInstaller()
        self.configurator = TheHiveConfigurator()
        self.validator = TheHiveValidator()
        self.backup_restore = TheHiveBackupRestore()

    async def check_prerequisites(self, ctx):
        return await self.installer.check_prerequisites(ctx)

    async def get_deployment_options(self, ctx):
        return {
            "cortex_url": {
                "type": "text",
                "message": "URL de Cortex (si installé)",
                "default": "http://localhost:9001",
            },
            "admin_password": {
                "type": "password",
                "message": "Mot de passe admin TheHive",
                "default": "",
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
