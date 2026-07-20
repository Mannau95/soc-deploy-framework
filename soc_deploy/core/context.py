"""
Contexte d'exécution partagé entre tous les composants
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

try:
    from pydantic import BaseModel
except ImportError:
    from typing import Any as BaseModel  # Fallback if pydantic not available

from soc_deploy.models.config import FrameworkConfig, SystemInfo
from soc_deploy.utils.logger import LoggerManager

if TYPE_CHECKING:
    from soc_deploy.services.executor import CommandExecutor
    from soc_deploy.services.system import SystemChecker
    from soc_deploy.services.package import PackageManager
    from soc_deploy.services.docker import DockerManager
    from soc_deploy.services.file import FileManager
    from soc_deploy.services.backup import BackupManager
    from soc_deploy.services.validator import ValidatorService
    from soc_deploy.database.manager import DatabaseManager
    from soc_deploy.plugins.registry import PluginRegistry


class DeploymentStep(BaseModel):
    """Étape courante d'un déploiement"""

    deployment_id: Optional[str] = None
    tool_name: Optional[str] = None
    action: Optional[str] = None  # PREREQ_CHECK, INSTALL, CONFIGURE, VALIDATE
    step_number: int = 0
    total_steps: int = 0


class ExecutionContext:
    """
    Contexte d'exécution injecté dans tous les composants.
    Fournit l'accès aux services, à la configuration, et à l'état.
    """

    def __init__(
        self,
        config: FrameworkConfig,
        system_info: SystemInfo,
        logger: LoggerManager,
        db: "DatabaseManager",
        executor: "CommandExecutor",
        system_checker: "SystemChecker",
        package_manager: "PackageManager",
        docker_manager: "DockerManager",
        file_manager: "FileManager",
        backup_manager: "BackupManager",
        validator: "ValidatorService",
        plugin_registry: "PluginRegistry",
    ):
        self.config = config
        self.system_info = system_info
        self.logger = logger
        self.db = db
        self.executor = executor
        self.system_checker = system_checker
        self.package_manager = package_manager
        self.docker_manager = docker_manager
        self.file_manager = file_manager
        self.backup_manager = backup_manager
        self.validator = validator
        self.plugin_registry = plugin_registry

        # État d'exécution
        self.dry_run: bool = False
        self.interactive: bool = True
        self.current_step: DeploymentStep = DeploymentStep()

        # Variables temporaires partagées
        self.variables: Dict[str, Any] = {}
        self.errors: List[str] = []

    def get_logger(self, name: str):
        """Raccourci pour obtenir un logger nommé"""
        return self.logger.get_logger(name)

    def set_step(
        self,
        deployment_id: str,
        tool_name: str,
        action: str,
        step_number: int,
        total_steps: int,
    ):
        """Met à jour l'étape courante"""
        self.current_step = DeploymentStep(
            deployment_id=deployment_id,
            tool_name=tool_name,
            action=action,
            step_number=step_number,
            total_steps=total_steps,
        )

    def clear_errors(self):
        self.errors.clear()

    def add_error(self, error: str):
        self.errors.append(error)

    def has_errors(self) -> bool:
        return len(self.errors) > 0
