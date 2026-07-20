"""
Service de sauvegarde et restauration
"""

import shutil
import tarfile
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from soc_deploy.utils.logger import LoggerManager


class BackupType(Enum):
    """Type de sauvegarde"""

    PRE_INSTALL = "pre_install"
    CONFIG = "config"
    FULL = "full"
    CUSTOM = "custom"


@dataclass
class BackupTarget:
    """Cible de sauvegarde"""

    paths: List[Path]  # Chemins à sauvegarder
    tool_name: str  # Nom de l'outil concerné
    backup_type: BackupType = BackupType.CUSTOM
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class Backup:
    """Métadonnées d'une sauvegarde"""

    id: str
    tool_name: str
    backup_type: BackupType
    created_at: datetime
    size_bytes: int = 0
    checksum: Optional[str] = None
    path: Optional[Path] = None
    metadata: Dict[str, str] = field(default_factory=dict)


class BackupManager:
    """Gestionnaire de sauvegardes"""

    def __init__(self, backup_root: Path, logger: LoggerManager):
        self.backup_root = Path(backup_root)
        self.logger = logger.get_logger("backup")
        self.backup_root.mkdir(parents=True, exist_ok=True)

    def _generate_backup_id(self, tool_name: str) -> str:
        """Génère un identifiant unique pour une sauvegarde"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{tool_name}_{timestamp}"

    def _compute_checksum(self, file_path: Path) -> str:
        """Calcule le checksum SHA256 d'un fichier"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    async def create_backup(self, target: BackupTarget) -> Optional[Backup]:
        """
        Crée une sauvegarde des fichiers/dossiers spécifiés

        Args:
            target: Cible de la sauvegarde

        Returns:
            Backup ou None en cas d'échec
        """
        self.logger.info(
            f"Création sauvegarde {target.backup_type.value} pour {target.tool_name}"
        )

        backup_id = self._generate_backup_id(target.tool_name)
        backup_dir = self.backup_root / target.tool_name
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Créer une archive tar.gz
        archive_name = f"{backup_id}.tar.gz"
        archive_path = backup_dir / archive_name

        try:
            with tarfile.open(archive_path, "w:gz") as tar:
                for path in target.paths:
                    if Path(path).exists():
                        tar.add(path, arcname=Path(path).name)
                    else:
                        self.logger.warning(f"Chemin inexistant ignoré : {path}")

            # Métadonnées
            size = archive_path.stat().st_size
            checksum = self._compute_checksum(archive_path)

            backup = Backup(
                id=backup_id,
                tool_name=target.tool_name,
                backup_type=target.backup_type,
                created_at=datetime.now(),
                size_bytes=size,
                checksum=checksum,
                path=archive_path,
                metadata=target.metadata,
            )

            # Sauvegarder les métadonnées dans un fichier JSON séparé
            self._save_backup_metadata(backup)

            self.logger.info(f"Sauvegarde créée : {backup_id} ({size} bytes)")
            return backup

        except Exception as e:
            self.logger.error(f"Échec création sauvegarde : {e}")
            # Nettoyer en cas d'erreur
            if archive_path.exists():
                archive_path.unlink()
            return None

    async def restore_backup(
        self, backup: Backup, restore_paths: Dict[str, str]
    ) -> bool:
        """
        Restaure une sauvegarde

        Args:
            backup: Sauvegarde à restaurer
            restore_paths: Mapping {nom_dans_archive: chemin_cible}

        Returns:
            True si succès
        """
        if not backup.path or not backup.path.exists():
            self.logger.error(f"Archive de sauvegarde introuvable : {backup.path}")
            return False

        self.logger.info(f"Restauration sauvegarde {backup.id}")

        try:
            with tarfile.open(backup.path, "r:gz") as tar:
                for member in tar.getmembers():
                    # Si un mapping est fourni, déterminer la cible
                    if member.name in restore_paths:
                        target_path = Path(restore_paths[member.name])
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        # Extraire vers un fichier temporaire puis déplacer
                        tar.extract(member, path=target_path.parent)
                        extracted = target_path.parent / member.name
                        if extracted != target_path:
                            shutil.move(str(extracted), str(target_path))
                    else:
                        # Extraire tel quel (dans le répertoire courant)
                        tar.extract(member, path=".")

            self.logger.info(f"Restauration terminée pour {backup.id}")
            return True

        except Exception as e:
            self.logger.error(f"Échec restauration : {e}")
            return False

    def list_backups(self, tool_name: str) -> List[Backup]:
        """
        Liste toutes les sauvegardes d'un outil

        Args:
            tool_name: Nom de l'outil

        Returns:
            Liste de Backup
        """
        tool_dir = self.backup_root / tool_name
        if not tool_dir.exists():
            return []

        backups = []
        for meta_file in tool_dir.glob("*.json"):
            backup = self._load_backup_metadata(meta_file)
            if backup:
                backups.append(backup)

        # Trier par date décroissante
        backups.sort(key=lambda b: b.created_at, reverse=True)
        return backups

    def get_backup(self, tool_name: str, backup_id: str) -> Optional[Backup]:
        """
        Récupère une sauvegarde spécifique

        Args:
            tool_name: Nom de l'outil
            backup_id: Identifiant de la sauvegarde

        Returns:
            Backup ou None
        """
        meta_path = self.backup_root / tool_name / f"{backup_id}.json"
        if not meta_path.exists():
            return None
        return self._load_backup_metadata(meta_path)

    def cleanup_old_backups(self, tool_name: str, keep: int = 5) -> int:
        """
        Supprime les anciennes sauvegardes en conservant les plus récentes

        Args:
            tool_name: Nom de l'outil
            keep: Nombre de sauvegardes à conserver

        Returns:
            Nombre de sauvegardes supprimées
        """
        backups = self.list_backups(tool_name)
        if len(backups) <= keep:
            return 0

        removed = 0
        for backup in backups[keep:]:
            if backup.path and backup.path.exists():
                backup.path.unlink()
            meta_path = self.backup_root / tool_name / f"{backup.id}.json"
            if meta_path.exists():
                meta_path.unlink()
            removed += 1

        self.logger.info(
            f"Nettoyage : {removed} anciennes sauvegardes supprimées pour {tool_name}"
        )
        return removed

    def verify_backup(self, backup: Backup) -> bool:
        """
        Vérifie l'intégrité d'une sauvegarde

        Args:
            backup: Sauvegarde à vérifier

        Returns:
            True si l'intégrité est OK
        """
        if not backup.path or not backup.path.exists():
            self.logger.error(f"Archive manquante : {backup.path}")
            return False

        if backup.checksum:
            current_checksum = self._compute_checksum(backup.path)
            if current_checksum != backup.checksum:
                self.logger.error(f"Checksum invalide pour {backup.id}")
                return False

        # Vérifier que l'archive est lisible
        try:
            with tarfile.open(backup.path, "r:gz") as tar:
                tar.getmembers()
            return True
        except Exception as e:
            self.logger.error(f"Archive corrompue : {e}")
            return False

    def _save_backup_metadata(self, backup: Backup) -> None:
        """Sauvegarde les métadonnées dans un fichier JSON"""
        import json

        meta_path = self.backup_root / backup.tool_name / f"{backup.id}.json"
        data = {
            "id": backup.id,
            "tool_name": backup.tool_name,
            "backup_type": backup.backup_type.value,
            "created_at": backup.created_at.isoformat(),
            "size_bytes": backup.size_bytes,
            "checksum": backup.checksum,
            "archive_name": backup.path.name if backup.path else None,
            "metadata": backup.metadata,
        }
        with open(meta_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load_backup_metadata(self, meta_path: Path) -> Optional[Backup]:
        """Charge les métadonnées depuis un fichier JSON"""
        import json

        try:
            with open(meta_path) as f:
                data = json.load(f)

            return Backup(
                id=data["id"],
                tool_name=data["tool_name"],
                backup_type=BackupType(data["backup_type"]),
                created_at=datetime.fromisoformat(data["created_at"]),
                size_bytes=data["size_bytes"],
                checksum=data.get("checksum"),
                path=(
                    meta_path.parent / data["archive_name"]
                    if data.get("archive_name")
                    else None
                ),
                metadata=data.get("metadata", {}),
            )
        except Exception as e:
            self.logger.warning(f"Erreur chargement métadonnées {meta_path}: {e}")
            return None
