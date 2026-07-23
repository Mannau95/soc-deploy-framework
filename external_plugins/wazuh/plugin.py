"""
Plugin Wazuh – Stack complète (Indexer, Server, Dashboard, Agent)
"""

from typing import Any, Dict

from soc_deploy.plugins.base import PluginBase, PluginMetadata

from .backup_restore import WazuhBackupRestore
from .configure import WazuhConfigurator
from .install import WazuhInstaller
from .validate import WazuhValidator


class WazuhPlugin(PluginBase):
    meta = PluginMetadata(
        name="wazuh",
        version="4.7.0",
        description="Wazuh – Security Information and Event Management (SIEM) et XDR",
        author="SOC Deploy Community",
        min_system_requirements={
            "cpu": 4,
            "ram_gb": 8,
            "disk_gb": 50,
        },
        tags=["siem", "xdr", "compliance", "ids"],
    )

    def __init__(self):
        self.installer = WazuhInstaller()
        self.configurator = WazuhConfigurator()
        self.validator = WazuhValidator()
        self.backup_restore = WazuhBackupRestore()

    # ---------- Interface requise ----------
    async def check_prerequisites(self, ctx) -> Dict[str, Any]:
        return await self.installer.check_prerequisites(ctx)

    async def get_deployment_options(self, ctx) -> Dict[str, Any]:
        """Propose les différentes architectures de déploiement Wazuh"""
        return {
            "architecture": {
                "type": "choice",
                "message": "Choisissez l'architecture Wazuh",
                "choices": [
                    {
                        "value": "all-in-one",
                        "label": "Tout-en-un (Indexer + Server + Dashboard sur un seul nœud)",
                        "description": "Idéal pour les tests ou petits déploiements",
                    },
                    {
                        "value": "distributed",
                        "label": "Distribué (composants séparés)",
                        "description": "Indexer, Server et Dashboard sur des machines différentes",
                    },
                    {
                        "value": "cluster",
                        "label": "Cluster haute disponibilité",
                        "description": "Multiples Indexers et Servers pour la résilience",
                    },
                ],
            },
            "installation_method": {
                "type": "choice",
                "message": "Méthode d'installation",
                "choices": [
                    {
                        "value": "assistant",
                        "label": "Assistant officiel Wazuh (curl | bash)",
                    },
                    {"value": "packages", "label": "Paquets système (apt/rpm)"},
                    {"value": "docker", "label": "Docker / Docker Compose"},
                    {"value": "kubernetes", "label": "Kubernetes (Helm)"},
                ],
            },
            "wazuh_version": {
                "type": "string",
                "message": "Version de Wazuh (par défaut 4.7.0)",
                "default": "4.7.0",
            },
            "admin_password": {
                "type": "password",
                "message": "Mot de passe administrateur Wazuh (généré automatiquement si vide)",
                "default": "",
            },
            "ssl": {
                "type": "confirm",
                "message": "Activer SSL/TLS pour les communications ?",
                "default": True,
            },
            "expose_dashboard": {
                "type": "confirm",
                "message": "Exposer le dashboard sur l'interface réseau ?",
                "default": False,
            },
        }

    async def install(self, ctx, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Installe la stack Wazuh selon les options choisies.
        """
        return await self.installer.install(ctx, options)

    async def configure(self, ctx, config: Dict[str, Any]) -> Dict[str, Any]:
        return await self.configurator.configure(ctx, config)

    async def validate(self, ctx) -> Dict[str, Any]:
        return await self.validator.validate(ctx)

    async def backup(self, ctx) -> Dict[str, Any]:
        return await self.backup_restore.backup(ctx)

    async def restore(self, ctx, backup_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.backup_restore.restore(ctx, backup_data)

    async def rollback(self, ctx) -> Dict[str, Any]:
        # En cas d'échec, on désinstalle ce qui a été fait
        return await self.uninstall(ctx)

    async def uninstall(self, ctx) -> Dict[str, Any]:
        return await self.installer.uninstall(ctx)

    async def update(self, ctx) -> Dict[str, Any]:
        return await self.installer.update(ctx)

    async def health_check(self, ctx) -> Dict[str, Any]:
        return await self.validator.health_check(ctx)
