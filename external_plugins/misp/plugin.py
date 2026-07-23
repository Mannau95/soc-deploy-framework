from soc_deploy.plugins.base import PluginBase, PluginMetadata
from .install import MispInstaller
from .configure import MispConfigurator
from .validate import MispValidator
from .backup_restore import MispBackupRestore


class MispPlugin(PluginBase):
    meta = PluginMetadata(
        name="misp",
        version="2.4.180",
        description="MISP – Plateforme de partage d'indicateurs de menace",
        min_system_requirements={"cpu": 2, "ram_gb": 4, "disk_gb": 20},
        tags=["threat-intel", "sharing"],
    )

    def __init__(self):
        self.installer = MispInstaller()
        self.configurator = MispConfigurator()
        self.validator = MispValidator()
        self.backup_restore = MispBackupRestore()

    async def check_prerequisites(self, ctx):
        return await self.installer.check_prerequisites(ctx)

    async def get_deployment_options(self, ctx):
        return {
            "base_url": {
                "type": "text",
                "message": "URL de base (ex: https://misp.example.com)",
                "default": "http://localhost",
            },
            "email": {
                "type": "text",
                "message": "Email administrateur",
                "default": "admin@localhost.local",
            },
            "admin_password": {
                "type": "password",
                "message": "Mot de passe admin MISP",
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
