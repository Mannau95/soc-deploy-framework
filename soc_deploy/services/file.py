"""
Service de gestion des fichiers
"""

import os
import shutil
import yaml
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, Template


class FileManager:
    """Gestionnaire de fichiers"""

    def __init__(self):
        self._jinja_env: Optional[Environment] = None

    def read_file(self, path: Union[str, Path]) -> str:
        """
        Lit un fichier texte

        Args:
            path: Chemin du fichier

        Returns:
            Contenu du fichier
        """
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def write_file(self, path: Union[str, Path], content: str, mode: str = "w") -> None:
        """
        Écrit un fichier texte

        Args:
            path: Chemin du fichier
            content: Contenu à écrire
            mode: Mode d'ouverture
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, mode, encoding="utf-8") as f:
            f.write(content)

    def read_yaml(self, path: Union[str, Path]) -> Dict[str, Any]:
        """
        Lit un fichier YAML

        Args:
            path: Chemin du fichier

        Returns:
            Dictionnaire YAML
        """
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def write_yaml(self, path: Union[str, Path], data: Dict[str, Any]) -> None:
        """
        Écrit un fichier YAML

        Args:
            path: Chemin du fichier
            data: Données à écrire
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def read_json(self, path: Union[str, Path]) -> Dict[str, Any]:
        """
        Lit un fichier JSON

        Args:
            path: Chemin du fichier

        Returns:
            Dictionnaire JSON
        """
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def write_json(
        self, path: Union[str, Path], data: Dict[str, Any], indent: int = 2
    ) -> None:
        """
        Écrit un fichier JSON

        Args:
            path: Chemin du fichier
            data: Données à écrire
            indent: Indentation
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)

    def copy_file(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        """
        Copie un fichier

        Args:
            src: Chemin source
            dst: Chemin destination
        """
        src = Path(src)
        dst = Path(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    def copy_directory(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        """
        Copie un répertoire

        Args:
            src: Chemin source
            dst: Chemin destination
        """
        shutil.copytree(src, dst, dirs_exist_ok=True)

    def move_file(self, src: Union[str, Path], dst: Union[str, Path]) -> None:
        """
        Déplace un fichier

        Args:
            src: Chemin source
            dst: Chemin destination
        """
        dst = Path(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))

    def delete_file(self, path: Union[str, Path]) -> None:
        """
        Supprime un fichier

        Args:
            path: Chemin du fichier
        """
        path = Path(path)
        if path.exists():
            path.unlink()

    def delete_directory(self, path: Union[str, Path]) -> None:
        """
        Supprime un répertoire

        Args:
            path: Chemin du répertoire
        """
        path = Path(path)
        if path.exists():
            shutil.rmtree(path)

    def ensure_directory(self, path: Union[str, Path]) -> Path:
        """
        Crée un répertoire s'il n'existe pas

        Args:
            path: Chemin du répertoire

        Returns:
            Path du répertoire
        """
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def file_exists(self, path: Union[str, Path]) -> bool:
        """
        Vérifie si un fichier existe

        Args:
            path: Chemin du fichier

        Returns:
            True si le fichier existe
        """
        return Path(path).exists()

    def set_permissions(self, path: Union[str, Path], mode: int) -> None:
        """
        Modifie les permissions d'un fichier

        Args:
            path: Chemin du fichier
            mode: Mode octal (ex: 0o755)
        """
        os.chmod(path, mode)

    def set_owner(
        self, path: Union[str, Path], user: str, group: Optional[str] = None
    ) -> None:
        """
        Modifie le propriétaire d'un fichier

        Args:
            path: Chemin du fichier
            user: Utilisateur
            group: Groupe (optionnel)
        """
        import pwd
        import grp

        uid = pwd.getpwnam(user).pw_uid
        gid = grp.getgrnam(group).gr_gid if group else -1

        if gid != -1:
            os.chown(path, uid, gid)
        else:
            os.chown(path, uid, -1)

    def render_template(
        self,
        template_path: Union[str, Path],
        context: Dict[str, Any],
        template_dir: Optional[Union[str, Path]] = None,
    ) -> str:
        """
        Rend un template Jinja2

        Args:
            template_path: Chemin du template
            context: Variables de contexte
            template_dir: Répertoire des templates

        Returns:
            Contenu rendu
        """
        if not self._jinja_env or template_dir:
            loader = FileSystemLoader(str(template_dir) if template_dir else ".")
            self._jinja_env = Environment(loader=loader)

        template = self._jinja_env.get_template(str(template_path))
        return template.render(**context)

    def render_template_string(
        self,
        template_string: str,
        context: Dict[str, Any],
    ) -> str:
        """
        Rend un template Jinja2 depuis une chaîne

        Args:
            template_string: Template en chaîne
            context: Variables de contexte

        Returns:
            Contenu rendu
        """
        template = Template(template_string)
        return template.render(**context)

    def backup_file(
        self, path: Union[str, Path], backup_dir: Union[str, Path]
    ) -> Optional[Path]:
        """
        Sauvegarde un fichier

        Args:
            path: Chemin du fichier à sauvegarder
            backup_dir: Répertoire de sauvegarde

        Returns:
            Chemin de la sauvegarde ou None
        """
        path = Path(path)
        if not path.exists():
            return None

        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{path.name}.{timestamp}.bak"
        backup_path = backup_dir / backup_name

        shutil.copy2(path, backup_path)
        return backup_path

    def restore_file(
        self, backup_path: Union[str, Path], target_path: Union[str, Path]
    ) -> bool:
        """
        Restaure un fichier depuis une sauvegarde

        Args:
            backup_path: Chemin de la sauvegarde
            target_path: Chemin de destination

        Returns:
            True si succès
        """
        backup_path = Path(backup_path)
        if not backup_path.exists():
            return False

        target_path = Path(target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(backup_path, target_path)
        return True

    def list_files(self, directory: Union[str, Path], pattern: str = "*") -> List[Path]:
        """
        Liste les fichiers dans un répertoire

        Args:
            directory: Répertoire
            pattern: Pattern glob

        Returns:
            Liste des chemins
        """
        return list(Path(directory).glob(pattern))

    def get_file_size(self, path: Union[str, Path]) -> int:
        """
        Récupère la taille d'un fichier en bytes

        Args:
            path: Chemin du fichier

        Returns:
            Taille en bytes
        """
        return Path(path).stat().st_size

    def search_replace(
        self,
        path: Union[str, Path],
        search: str,
        replace: str,
        backup: bool = True,
    ) -> bool:
        """
        Remplace du texte dans un fichier

        Args:
            path: Chemin du fichier
            search: Texte à rechercher
            replace: Texte de remplacement
            backup: Créer une sauvegarde

        Returns:
            True si des modifications ont été faites
        """
        path = Path(path)
        if not path.exists():
            return False

        content = self.read_file(path)

        if search not in content:
            return False

        if backup:
            self.backup_file(path, path.parent / "backups")

        new_content = content.replace(search, replace)
        self.write_file(path, new_content)
        return True
