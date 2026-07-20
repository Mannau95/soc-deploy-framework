"""
Planificateur de déploiement
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from .dependency import DependencyResolver


@dataclass
class DeploymentPlan:
    order: List[str]  # ordre d'installation
    configs: Dict[str, Dict[str, Any]]  # configuration par outil
    conflicts: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class DeploymentPlanner:
    def __init__(self, dependency_resolver: DependencyResolver):
        self.resolver = dependency_resolver

    def create_plan(
        self, tools: List[str], profile: Optional[str] = None
    ) -> DeploymentPlan:
        # Résoudre l'ordre via le résolveur de dépendances
        order = self.resolver.suggest_install_order(tools)
        # Les configurations seraient chargées depuis un profil
        configs = {t: {} for t in tools}
        return DeploymentPlan(order=order, configs=configs)
