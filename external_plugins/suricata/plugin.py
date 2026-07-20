"""
Plugin Suricata – IDS / IPS réseau
"""

from soc_deploy.plugins.base import PluginBase, PluginMetadata
from .install import SuricataInstaller
from .configure import SuricataConfigurator
from .validate import SuricataValidator
from .backup_restore import SuricataBackupRestore


class SuricataPlugin(PluginBase):
    meta = PluginMetadata(
        name="suricata",
        version="7.0.0",
        description="Suricata – IDS/IPS réseau haute performance",
        author="SOC Deploy Community",
        min_system_requirements={"cpu": 2, "ram_gb": 2, "disk_gb": 5},
        tags=["ids", "ips", "network"],
    )

    def __init__(self):
        self.installer = SuricataInstaller()
        self.configurator = SuricataConfigurator()
        self.validator = SuricataValidator()
        self.backup_restore = SuricataBackupRestore()

    async def check_prerequisites(self, ctx):
        return await self.installer.check_prerequisites(ctx)

    async def get_deployment_options(self, ctx):
        return {
            "mode": {
                "type": "choice",
                "message": "Choisissez le mode de détection",
                "choices": [
                    {"value": "ids", "label": "IDS (détection seule)"},
                    {
                        "value": "ips",
                        "label": "IPS (prévention, nécessite NFQ/AF_PACKET)",
                    },
                ],
            },
            "interface": {
                "type": "text",
                "message": "Interface réseau à surveiller (ex: eth0)",
                "default": "eth0",
            },
            "ruleset": {
                "type": "choice",
                "message": "Règles à activer",
                "choices": [
                    {
                        "value": "default",
                        "label": "Règles par défaut (Emerging Threats Open)",
                    },
                    {"value": "custom", "label": "Personnalisé (fichier local)"},
                ],
            },
            "community_id": {
                "type": "confirm",
                "message": "Activer le Community ID pour le partage d'indicateurs ?",
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
