from soc_deploy.plugins.base import PluginBase, PluginMetadata
from .install import ShuffleInstaller
from .configure import ShuffleConfigurator
from .validate import ShuffleValidator
from .backup_restore import ShuffleBackupRestore


class ShufflePlugin(PluginBase):
    meta = PluginMetadata(
        name="shuffle",
        version="1.2.0",
        description="Shuffle – SOAR / Automatisation",
        min_system_requirements={"cpu": 2, "ram_gb": 4, "disk_gb": 10},
        tags=["soar", "automation"],
    )

    def __init__(self):
        self.installer = ShuffleInstaller()
        self.configurator = ShuffleConfigurator()
        self.validator = ShuffleValidator()
        self.backup_restore = ShuffleBackupRestore()

    async def check_prerequisites(self, ctx):
        return await self.installer.check_prerequisites(ctx)

    async def get_deployment_options(self, ctx):
        return {
            "email": {
                "type": "text",
                "message": "Email administrateur",
                "default": "admin@shuffle.local",
            },
            "admin_password": {
                "type": "password",
                "message": "Mot de passe admin",
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
