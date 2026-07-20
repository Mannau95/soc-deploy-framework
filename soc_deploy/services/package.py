"""
Service de gestion des paquets système
"""

from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

from soc_deploy.services.executor import CommandExecutor, ExecutionStatus


class PackageManagerType(Enum):
    """Type de gestionnaire de paquets"""

    APT = "apt"
    YUM = "yum"
    DNF = "dnf"
    ZYPPER = "zypper"
    PACMAN = "pacman"
    UNKNOWN = "unknown"


@dataclass
class PackageInfo:
    """Informations sur un paquet"""

    name: str
    version: Optional[str] = None
    installed: bool = False
    repository: Optional[str] = None


@dataclass
class PackageResult:
    """Résultat d'une opération sur les paquets"""

    success: bool
    installed: List[str]
    failed: List[str]
    updated: List[str]
    removed: List[str]
    errors: List[str]


class PackageManager:
    """Gestionnaire de paquets unifié"""

    def __init__(self, executor: CommandExecutor):
        self.executor = executor
        self._manager_type: Optional[PackageManagerType] = None

    async def detect_package_manager(self) -> PackageManagerType:
        """Détecte le gestionnaire de paquets disponible"""
        if self._manager_type:
            return self._manager_type

        # Vérifier chaque gestionnaire
        checks = [
            (PackageManagerType.APT, "apt-get"),
            (PackageManagerType.YUM, "yum"),
            (PackageManagerType.DNF, "dnf"),
            (PackageManagerType.ZYPPER, "zypper"),
            (PackageManagerType.PACMAN, "pacman"),
        ]

        for pm_type, command in checks:
            if await self.executor.check_command_exists(command):
                self._manager_type = pm_type
                return pm_type

        self._manager_type = PackageManagerType.UNKNOWN
        return PackageManagerType.UNKNOWN

    async def update_repositories(self) -> bool:
        """Met à jour la liste des paquets"""
        pm_type = await self.detect_package_manager()

        update_commands = {
            PackageManagerType.APT: "apt-get update -y",
            PackageManagerType.YUM: "yum check-update",
            PackageManagerType.DNF: "dnf check-update",
            PackageManagerType.ZYPPER: "zypper refresh",
            PackageManagerType.PACMAN: "pacman -Sy",
        }

        command = update_commands.get(pm_type)
        if not command:
            return False

        result = await self.executor.execute(command, sudo=True, timeout=120)
        return result.status == ExecutionStatus.SUCCESS

    async def install_packages(
        self,
        packages: List[str],
        update_first: bool = True,
    ) -> PackageResult:
        """
        Installe une liste de paquets

        Args:
            packages: Liste des paquets à installer
            update_first: Mettre à jour les dépôts avant

        Returns:
            PackageResult
        """
        pm_type = await self.detect_package_manager()
        result = PackageResult(
            success=True,
            installed=[],
            failed=[],
            updated=[],
            removed=[],
            errors=[],
        )

        # Mettre à jour les dépôts
        if update_first:
            await self.update_repositories()

        # Installer par lots pour éviter les commandes trop longues
        batch_size = 10
        for i in range(0, len(packages), batch_size):
            batch = packages[i : i + batch_size]
            batch_result = await self._install_batch(batch, pm_type)

            result.installed.extend(batch_result.installed)
            result.failed.extend(batch_result.failed)
            result.errors.extend(batch_result.errors)

            if batch_result.failed:
                result.success = False

        return result

    async def _install_batch(
        self,
        packages: List[str],
        pm_type: PackageManagerType,
    ) -> PackageResult:
        """Installe un lot de paquets"""
        result = PackageResult(
            success=True,
            installed=[],
            failed=[],
            updated=[],
            removed=[],
            errors=[],
        )

        install_commands = {
            PackageManagerType.APT: f"apt-get install -y {' '.join(packages)}",
            PackageManagerType.YUM: f"yum install -y {' '.join(packages)}",
            PackageManagerType.DNF: f"dnf install -y {' '.join(packages)}",
            PackageManagerType.ZYPPER: f"zypper install -y {' '.join(packages)}",
            PackageManagerType.PACMAN: f"pacman -S --noconfirm {' '.join(packages)}",
        }

        command = install_commands.get(pm_type)
        if not command:
            result.success = False
            result.failed = packages
            result.errors.append(f"Gestionnaire de paquets non supporté : {pm_type}")
            return result

        exec_result = await self.executor.execute_with_retry(
            command,
            sudo=True,
            timeout=300,
            retries=2,
        )

        if exec_result.status == ExecutionStatus.SUCCESS:
            result.installed = packages
        else:
            # Essayer d'identifier les paquets qui ont échoué
            result.success = False
            result.failed = packages
            result.errors.append(exec_result.stderr)

        return result

    async def remove_packages(
        self, packages: List[str], purge: bool = False
    ) -> PackageResult:
        """
        Supprime des paquets

        Args:
            packages: Liste des paquets à supprimer
            purge: Supprimer aussi les fichiers de configuration

        Returns:
            PackageResult
        """
        pm_type = await self.detect_package_manager()
        result = PackageResult(
            success=True,
            installed=[],
            failed=[],
            updated=[],
            removed=[],
            errors=[],
        )

        remove_commands = {
            PackageManagerType.APT: f"apt-get {'purge' if purge else 'remove'} -y {' '.join(packages)}",
            PackageManagerType.YUM: f"yum remove -y {' '.join(packages)}",
            PackageManagerType.DNF: f"dnf remove -y {' '.join(packages)}",
            PackageManagerType.ZYPPER: f"zypper remove -y {' '.join(packages)}",
            PackageManagerType.PACMAN: f"pacman -R{'ns' if purge else ''} --noconfirm {' '.join(packages)}",
        }

        command = remove_commands.get(pm_type)
        if not command:
            result.success = False
            result.errors.append(f"Gestionnaire de paquets non supporté : {pm_type}")
            return result

        exec_result = await self.executor.execute(command, sudo=True, timeout=300)

        if exec_result.status == ExecutionStatus.SUCCESS:
            result.removed = packages
        else:
            result.success = False
            result.failed = packages
            result.errors.append(exec_result.stderr)

        return result

    async def is_installed(self, package: str) -> bool:
        """
        Vérifie si un paquet est installé

        Args:
            package: Nom du paquet

        Returns:
            True si le paquet est installé
        """
        pm_type = await self.detect_package_manager()

        check_commands = {
            PackageManagerType.APT: f"dpkg -l {package} 2>/dev/null | grep -q '^ii'",
            PackageManagerType.YUM: f"rpm -q {package}",
            PackageManagerType.DNF: f"rpm -q {package}",
            PackageManagerType.ZYPPER: f"rpm -q {package}",
            PackageManagerType.PACMAN: f"pacman -Q {package}",
        }

        command = check_commands.get(pm_type)
        if not command:
            return False

        result = await self.executor.execute(command)
        return result.status == ExecutionStatus.SUCCESS

    async def get_package_info(self, package: str) -> Optional[PackageInfo]:
        """
        Récupère les informations d'un paquet

        Args:
            package: Nom du paquet

        Returns:
            PackageInfo ou None
        """
        installed = await self.is_installed(package)

        info = PackageInfo(
            name=package,
            installed=installed,
        )

        # Récupérer la version si installé
        if installed:
            pm_type = await self.detect_package_manager()
            version_commands = {
                PackageManagerType.APT: f"dpkg -l {package} | grep '^ii' | awk '{{print $3}}'",
                PackageManagerType.YUM: f"rpm -q --qf '%{{VERSION}}' {package}",
                PackageManagerType.DNF: f"rpm -q --qf '%{{VERSION}}' {package}",
            }

            command = version_commands.get(pm_type)
            if command:
                result = await self.executor.execute(command)
                if result.status == ExecutionStatus.SUCCESS:
                    info.version = result.stdout.strip()

        return info

    async def install_from_url(
        self, url: str, output_path: Optional[str] = None
    ) -> bool:
        """
        Télécharge et installe un paquet depuis une URL

        Args:
            url: URL du paquet
            output_path: Chemin de sortie (optionnel)

        Returns:
            True si succès
        """
        import tempfile
        import os

        if not output_path:
            # Créer un fichier temporaire
            fd, output_path = tempfile.mkstemp(suffix=".deb")
            os.close(fd)

        # Télécharger le paquet
        download_result = await self.executor.execute(
            f"wget -O {output_path} {url}",
            timeout=300,
        )

        if download_result.status != ExecutionStatus.SUCCESS:
            return False

        # Installer le paquet
        pm_type = await self.detect_package_manager()

        if pm_type == PackageManagerType.APT:
            install_cmd = f"dpkg -i {output_path}"
        elif pm_type in [PackageManagerType.YUM, PackageManagerType.DNF]:
            install_cmd = f"rpm -i {output_path}"
        else:
            return False

        install_result = await self.executor.execute(install_cmd, sudo=True)
        return install_result.status == ExecutionStatus.SUCCESS
