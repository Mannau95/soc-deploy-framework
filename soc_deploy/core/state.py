"""
Gestionnaire d'état pour le suivi et la reprise des déploiements
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any, Dict, List, Optional

from soc_deploy.database.manager import DatabaseManager
from soc_deploy.utils.logger import LoggerManager


class DeploymentStatus(str, Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ToolStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class StateManager:
    """
    Gère l'état des déploiements via la base de données.
    Fournit des méthodes pour créer, suivre et reprendre un déploiement.
    """

    def __init__(self, db: DatabaseManager, logger: LoggerManager):
        self.db = db
        self.logger = logger.get_logger("state")

    # --- Gestion du déploiement ---

    async def create_deployment(self, name: str, profile: Optional[str] = None) -> str:
        """Crée un nouveau déploiement et retourne son ID"""
        import uuid

        deployment_id = str(uuid.uuid4())[:8]
        success = await self.db.create_deployment(deployment_id, name, profile)
        if not success:
            raise RuntimeError("Impossible de créer le déploiement")
        self.logger.info(f"Déploiement créé : {deployment_id} ({name})")
        return deployment_id

    async def start_deployment(self, deployment_id: str) -> bool:
        """Passe le déploiement en cours"""
        return await self.db.update_deployment_status(
            deployment_id, DeploymentStatus.IN_PROGRESS.value
        )

    async def pause_deployment(self, deployment_id: str) -> bool:
        """Met en pause le déploiement"""
        self.logger.info(f"Déploiement {deployment_id} mis en pause")
        return await self.db.update_deployment_status(deployment_id, DeploymentStatus.PAUSED.value)

    async def complete_deployment(self, deployment_id: str) -> bool:
        """Marque le déploiement comme terminé"""
        await self.db.complete_deployment(deployment_id)
        return await self.db.update_deployment_status(
            deployment_id, DeploymentStatus.COMPLETED.value
        )

    async def fail_deployment(self, deployment_id: str) -> bool:
        """Marque le déploiement comme échoué"""
        self.logger.error(f"Déploiement {deployment_id} échoué")
        return await self.db.update_deployment_status(deployment_id, DeploymentStatus.FAILED.value)

    async def get_deployment_status(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Récupère le statut complet d'un déploiement"""
        dep = await self.db.get_deployment(deployment_id)
        if dep:
            dep["tools"] = await self.db.get_deployment_tools(deployment_id)
        return dep

    async def list_active_deployments(self) -> List[Dict[str, Any]]:
        """Liste les déploiements non terminés"""
        active = []
        for status in [
            DeploymentStatus.PLANNED,
            DeploymentStatus.IN_PROGRESS,
            DeploymentStatus.PAUSED,
        ]:
            deps = await self.db.list_deployments(status.value)
            active.extend(deps)
        return active

    # --- Gestion des outils dans un déploiement ---

    async def add_tool_to_deployment(
        self,
        deployment_id: str,
        tool_name: str,
        version: Optional[str] = None,
        order: int = 0,
    ) -> bool:
        return await self.db.add_deployment_tool(deployment_id, tool_name, version, order)

    async def set_tool_status(
        self,
        deployment_id: str,
        tool_name: str,
        status: ToolStatus,
        config: Optional[Dict] = None,
    ) -> bool:
        config_json = json.dumps(config) if config else None
        return await self.db.update_tool_status(deployment_id, tool_name, status.value, config_json)

    async def get_tool_status(self, deployment_id: str, tool_name: str) -> Optional[Dict[str, Any]]:
        tools = await self.db.get_deployment_tools(deployment_id)
        for tool in tools:
            if tool["tool_name"] == tool_name:
                return tool
        return None

    async def get_deployment_tools(self, deployment_id: str) -> List[Dict[str, Any]]:
        return await self.db.get_deployment_tools(deployment_id)

    # --- Checkpoints (reprise) ---

    async def save_checkpoint(
        self,
        deployment_id: str,
        tool_name: str,
        step: str,
        state_data: Dict[str, Any],
    ) -> Optional[str]:
        """Sauvegarde un point de reprise"""
        self.logger.debug(f"Checkpoint sauvegardé : {deployment_id}/{tool_name}/{step}")
        return await self.db.save_checkpoint(deployment_id, tool_name, step, state_data)

    async def get_last_checkpoint(
        self, deployment_id: str, tool_name: str, step: str
    ) -> Optional[Dict[str, Any]]:
        """Récupère le dernier checkpoint pour reprendre"""
        return await self.db.get_last_checkpoint(deployment_id, tool_name, step)

    async def get_resume_info(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """
        Analyse l'état d'un déploiement pour déterminer où reprendre.
        Retourne un dict avec 'tool_name', 'step', 'state_data' ou None si terminé.
        """
        dep = await self.db.get_deployment(deployment_id)
        if not dep or dep["status"] not in (
            DeploymentStatus.PAUSED.value,
            DeploymentStatus.IN_PROGRESS.value,
            DeploymentStatus.FAILED.value,
        ):
            return None

        tools = await self.db.get_deployment_tools(deployment_id)
        # Chercher le premier outil non terminé
        for tool in tools:
            if tool["status"] in (
                ToolStatus.PENDING.value,
                ToolStatus.IN_PROGRESS.value,
                ToolStatus.FAILED.value,
            ):
                # Récupérer le dernier checkpoint pour cet outil
                steps = ["PREREQ_CHECK", "BACKUP", "INSTALL", "CONFIGURE", "VALIDATE"]
                for step in reversed(steps):
                    checkpoint = await self.db.get_last_checkpoint(
                        deployment_id, tool["tool_name"], step
                    )
                    if checkpoint:
                        return {
                            "tool_name": tool["tool_name"],
                            "step": step,
                            "state_data": checkpoint["state_data"],
                            "checkpoint_id": checkpoint["id"],
                        }
                # Aucun checkpoint, on commence du début de l'outil
                return {
                    "tool_name": tool["tool_name"],
                    "step": "PREREQ_CHECK",
                    "state_data": {},
                }
        return None  # tout est terminé

    # --- Historique des logs ---

    async def log_event(
        self,
        deployment_id: str,
        level: str,
        message: str,
        tool_name: Optional[str] = None,
        details: Optional[str] = None,
    ) -> bool:
        return await self.db.log_event(deployment_id, level, message, tool_name, details)
