"""
Classe de base pour tous les plugins SOC
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class PluginMetadata:
    """Métadonnées d'un plugin"""

    name: str
    version: str
    description: str
    author: str = "SOC Deploy Community"
    min_system_requirements: Dict[str, Any] = field(default_factory=dict)
    supported_distros: List[str] = field(
        default_factory=lambda: ["ubuntu", "debian", "centos", "rhel", "rocky", "almalinux"]
    )
    tags: List[str] = field(default_factory=list)


class PluginBase(ABC):
    """Interface que chaque outil SOC doit implémenter"""

    # Métadonnées – à définir dans chaque plugin
    meta: PluginMetadata

    @abstractmethod
    async def check_prerequisites(self, ctx) -> Dict[str, Any]:
        """Vérifier les prérequis spécifiques à l'outil"""
        ...

    @abstractmethod
    async def get_deployment_options(self, ctx) -> Dict[str, Any]:
        """Retourne les options de déploiement disponibles (single/multi/cluster, docker, etc.)"""
        ...

    @abstractmethod
    async def install(self, ctx, options: Dict[str, Any]) -> Dict[str, Any]:
        """Installe l'outil avec les options choisies"""
        ...

    @abstractmethod
    async def configure(self, ctx, config: Dict[str, Any]) -> Dict[str, Any]:
        """Configure l'outil après installation"""
        ...

    @abstractmethod
    async def validate(self, ctx) -> Dict[str, Any]:
        """Valide l'installation et la configuration"""
        ...

    @abstractmethod
    async def backup(self, ctx) -> Dict[str, Any]:
        """Sauvegarde des configurations et données"""
        ...

    @abstractmethod
    async def restore(self, ctx, backup_data: Dict[str, Any]) -> Dict[str, Any]:
        """Restauration depuis une sauvegarde"""
        ...

    @abstractmethod
    async def rollback(self, ctx) -> Dict[str, Any]:
        """Annule l'installation en cas d'échec"""
        ...

    @abstractmethod
    async def uninstall(self, ctx) -> Dict[str, Any]:
        """Désinstallation propre"""
        ...

    @abstractmethod
    async def update(self, ctx) -> Dict[str, Any]:
        """Mise à jour de l'outil"""
        ...

    @abstractmethod
    async def health_check(self, ctx) -> Dict[str, Any]:
        """Vérification de l'état de santé"""
        ...
