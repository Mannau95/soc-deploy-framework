"""
Gestionnaire de base de données SQLite
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

from soc_deploy.utils.logger import LoggerManager


class DatabaseManager:
    """Gestionnaire de la base de données d'état"""

    def __init__(self, db_path: Path, logger: LoggerManager):
        self.db_path = db_path
        self.logger = logger.get_logger("database")
        self._connection: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """Initialise la base de données (crée les tables)"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        schema_path = Path(__file__).parent / "schema.sql"
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema SQL introuvable: {schema_path}")

        schema = schema_path.read_text()

        async with aiosqlite.connect(str(self.db_path)) as db:
            await db.executescript(schema)
            await db.commit()

        self.logger.info(f"Base de données initialisée: {self.db_path}")

    async def get_connection(self) -> aiosqlite.Connection:
        """Retourne une connexion à la base (réutilise si possible)"""
        if self._connection is None:
            self._connection = await aiosqlite.connect(str(self.db_path))
            self._connection.row_factory = aiosqlite.Row
        return self._connection

    async def close(self) -> None:
        """Ferme la connexion"""
        if self._connection:
            await self._connection.close()
            self._connection = None

    # --- Méthodes pour les déploiements ---

    async def create_deployment(
        self, deployment_id: str, name: str, profile: Optional[str] = None
    ) -> bool:
        try:
            db = await self.get_connection()
            await db.execute(
                "INSERT INTO deployments (id, name, profile, status) VALUES (?, ?, ?, 'PLANNED')",
                (deployment_id, name, profile),
            )
            await db.commit()
            return True
        except Exception as e:
            self.logger.error(f"Erreur création déploiement: {e}")
            return False

    async def update_deployment_status(self, deployment_id: str, status: str) -> bool:
        try:
            db = await self.get_connection()
            await db.execute(
                "UPDATE deployments SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, deployment_id),
            )
            await db.commit()
            return True
        except Exception as e:
            self.logger.error(f"Erreur mise à jour statut: {e}")
            return False

    async def complete_deployment(self, deployment_id: str) -> bool:
        try:
            db = await self.get_connection()
            await db.execute(
                "UPDATE deployments SET status = 'COMPLETED', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (deployment_id,),
            )
            await db.commit()
            return True
        except Exception as e:
            self.logger.error(f"Erreur finalisation déploiement: {e}")
            return False

    async def get_deployment(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        try:
            db = await self.get_connection()
            cursor = await db.execute("SELECT * FROM deployments WHERE id = ?", (deployment_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            self.logger.error(f"Erreur récupération déploiement: {e}")
            return None

    async def list_deployments(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            db = await self.get_connection()
            if status:
                cursor = await db.execute(
                    "SELECT * FROM deployments WHERE status = ? ORDER BY created_at DESC",
                    (status,),
                )
            else:
                cursor = await db.execute("SELECT * FROM deployments ORDER BY created_at DESC")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Erreur liste déploiements: {e}")
            return []

    # --- Méthodes pour les outils d'un déploiement ---

    async def add_deployment_tool(
        self,
        deployment_id: str,
        tool_name: str,
        version: Optional[str] = None,
        install_order: int = 0,
    ) -> bool:
        try:
            db = await self.get_connection()
            await db.execute(
                """INSERT INTO deployment_tools (deployment_id, tool_name, version, install_order, status)
                   VALUES (?, ?, ?, ?, 'PENDING')""",
                (deployment_id, tool_name, version, install_order),
            )
            await db.commit()
            return True
        except Exception as e:
            self.logger.error(f"Erreur ajout outil: {e}")
            return False

    async def update_tool_status(
        self,
        deployment_id: str,
        tool_name: str,
        status: str,
        config_json: Optional[str] = None,
    ) -> bool:
        try:
            db = await self.get_connection()
            if config_json:
                await db.execute(
                    "UPDATE deployment_tools SET status = ?, config_json = ? WHERE deployment_id = ? AND tool_name = ?",
                    (status, config_json, deployment_id, tool_name),
                )
            else:
                await db.execute(
                    "UPDATE deployment_tools SET status = ? WHERE deployment_id = ? AND tool_name = ?",
                    (status, deployment_id, tool_name),
                )
            await db.commit()
            return True
        except Exception as e:
            self.logger.error(f"Erreur mise à jour outil: {e}")
            return False

    async def get_deployment_tools(self, deployment_id: str) -> List[Dict[str, Any]]:
        try:
            db = await self.get_connection()
            cursor = await db.execute(
                "SELECT * FROM deployment_tools WHERE deployment_id = ? ORDER BY install_order",
                (deployment_id,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Erreur récupération outils: {e}")
            return []

    # --- Checkpoints ---

    async def save_checkpoint(
        self,
        deployment_id: str,
        tool_name: str,
        step: str,
        state_data: Dict[str, Any],
    ) -> Optional[str]:
        checkpoint_id = f"{deployment_id}_{tool_name}_{step}_{datetime.now().timestamp()}"
        try:
            db = await self.get_connection()
            await db.execute(
                "INSERT INTO checkpoints (id, deployment_id, tool_name, step, state_data) VALUES (?, ?, ?, ?, ?)",
                (checkpoint_id, deployment_id, tool_name, step, json.dumps(state_data)),
            )
            await db.commit()
            return checkpoint_id
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde checkpoint: {e}")
            return None

    async def get_last_checkpoint(
        self, deployment_id: str, tool_name: str, step: str
    ) -> Optional[Dict[str, Any]]:
        try:
            db = await self.get_connection()
            cursor = await db.execute(
                """SELECT * FROM checkpoints
                   WHERE deployment_id = ? AND tool_name = ? AND step = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (deployment_id, tool_name, step),
            )
            row = await cursor.fetchone()
            if row:
                checkpoint = dict(row)
                checkpoint["state_data"] = json.loads(checkpoint["state_data"])
                return checkpoint
            return None
        except Exception as e:
            self.logger.error(f"Erreur récupération checkpoint: {e}")
            return None

    # --- Sauvegardes ---

    async def save_backup_record(
        self,
        backup_id: str,
        deployment_id: str,
        tool_name: str,
        backup_path: str,
        backup_type: str,
        size_bytes: int = 0,
        checksum: Optional[str] = None,
    ) -> bool:
        try:
            db = await self.get_connection()
            await db.execute(
                """INSERT INTO backups (id, deployment_id, tool_name, backup_path, backup_type, size_bytes, checksum)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    backup_id,
                    deployment_id,
                    tool_name,
                    backup_path,
                    backup_type,
                    size_bytes,
                    checksum,
                ),
            )
            await db.commit()
            return True
        except Exception as e:
            self.logger.error(f"Erreur enregistrement sauvegarde: {e}")
            return False

    async def get_backups_for_deployment(self, deployment_id: str) -> List[Dict[str, Any]]:
        try:
            db = await self.get_connection()
            cursor = await db.execute(
                "SELECT * FROM backups WHERE deployment_id = ? ORDER BY created_at DESC",
                (deployment_id,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Erreur récupération sauvegardes: {e}")
            return []

    # --- Logs ---

    async def log_event(
        self,
        deployment_id: str,
        level: str,
        message: str,
        tool_name: Optional[str] = None,
        details: Optional[str] = None,
    ) -> bool:
        try:
            db = await self.get_connection()
            await db.execute(
                "INSERT INTO execution_logs (deployment_id, tool_name, log_level, message, details) VALUES (?, ?, ?, ?, ?)",
                (deployment_id, tool_name, level, message, details),
            )
            await db.commit()
            return True
        except Exception as e:
            self.logger.error(f"Erreur log event: {e}")
            return False
