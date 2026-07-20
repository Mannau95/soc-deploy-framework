"""
Service de vérification système
"""

import os
import platform
import socket
import subprocess
import shutil
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from soc_deploy.models.config import SystemInfo


class CheckStatus(Enum):
    """Statut d'une vérification"""

    OK = "✅"
    WARNING = "⚠️"
    ERROR = "❌"
    UNKNOWN = "❓"


@dataclass
class CheckResult:
    """Résultat d'une vérification"""

    name: str
    status: CheckStatus
    message: str
    details: Optional[Dict[str, Any]] = None


class SystemChecker:
    """Vérificateur système complet"""

    def __init__(self):
        self.checks: List[CheckResult] = []

    def run_all_checks(self) -> List[CheckResult]:
        """Exécute toutes les vérifications système"""
        self.checks = []

        # Vérifications de base
        self.checks.append(self.check_distribution())
        self.checks.append(self.check_architecture())
        self.checks.append(self.check_cpu())
        self.checks.append(self.check_ram())
        self.checks.append(self.check_disk_space())

        # Vérifications réseau
        self.checks.append(self.check_internet())
        self.checks.append(self.check_dns())
        self.checks.append(self.check_ntp())

        # Vérifications système
        self.checks.append(self.check_sudo())
        self.checks.append(self.check_systemd())
        self.checks.append(self.check_virtualization())

        # Vérifications sécurité
        self.checks.append(self.check_selinux())
        self.checks.append(self.check_apparmor())
        self.checks.append(self.check_firewall())

        return self.checks

    def get_system_info(self) -> SystemInfo:
        """Récupère les informations système complètes"""
        return SystemInfo(
            distro=self._get_distro(),
            version=self._get_distro_version(),
            arch=platform.machine(),
            cpu_count=os.cpu_count() or 0,
            ram_gb=self._get_ram_gb(),
            disk_free_gb=self._get_disk_free_gb(),
            has_internet=self._check_internet(),
            dns_ok=self._check_dns(),
            ntp_synced=self._check_ntp(),
            has_sudo=self._check_sudo(),
            has_systemd=self._check_systemd(),
            selinux_mode=self._get_selinux_mode(),
            apparmor_status=self._get_apparmor_status(),
            firewall_active=self._check_firewall(),
            used_ports=self._get_used_ports(),
            virtualization=self._detect_virtualization(),
        )

    def check_distribution(self) -> CheckResult:
        """Vérifie la distribution Linux"""
        distro = self._get_distro()
        version = self._get_distro_version()

        if distro.lower() in [
            "ubuntu",
            "debian",
            "centos",
            "rhel",
            "fedora",
            "rocky",
            "almalinux",
        ]:
            return CheckResult(
                name="Distribution",
                status=CheckStatus.OK,
                message=f"Distribution supportée : {distro} {version}",
            )
        else:
            return CheckResult(
                name="Distribution",
                status=CheckStatus.WARNING,
                message=f"Distribution potentiellement non supportée : {distro} {version}",
            )

    def check_architecture(self) -> CheckResult:
        """Vérifie l'architecture CPU"""
        arch = platform.machine()
        if arch in ["x86_64", "aarch64"]:
            return CheckResult(
                name="Architecture",
                status=CheckStatus.OK,
                message=f"Architecture supportée : {arch}",
            )
        else:
            return CheckResult(
                name="Architecture",
                status=CheckStatus.ERROR,
                message=f"Architecture non supportée : {arch}",
            )

    def check_cpu(self) -> CheckResult:
        """Vérifie le nombre de CPU"""
        cpu_count = os.cpu_count() or 0
        if cpu_count >= 4:
            return CheckResult(
                name="CPU",
                status=CheckStatus.OK,
                message=f"CPU suffisant : {cpu_count} cœurs",
            )
        elif cpu_count >= 2:
            return CheckResult(
                name="CPU",
                status=CheckStatus.WARNING,
                message=f"CPU minimum : {cpu_count} cœurs (4+ recommandés)",
            )
        else:
            return CheckResult(
                name="CPU",
                status=CheckStatus.ERROR,
                message=f"CPU insuffisant : {cpu_count} cœurs (minimum 2 requis)",
            )

    def check_ram(self) -> CheckResult:
        """Vérifie la mémoire RAM"""
        ram_gb = self._get_ram_gb()
        if ram_gb >= 16:
            return CheckResult(
                name="Mémoire RAM",
                status=CheckStatus.OK,
                message=f"RAM suffisante : {ram_gb:.1f} GB",
            )
        elif ram_gb >= 8:
            return CheckResult(
                name="Mémoire RAM",
                status=CheckStatus.WARNING,
                message=f"RAM minimum : {ram_gb:.1f} GB (16+ GB recommandés)",
            )
        else:
            return CheckResult(
                name="Mémoire RAM",
                status=CheckStatus.ERROR,
                message=f"RAM insuffisante : {ram_gb:.1f} GB (minimum 8 GB requis)",
            )

    def check_disk_space(self, min_gb: float = 20.0) -> CheckResult:
        """Vérifie l'espace disque disponible"""
        free_gb = self._get_disk_free_gb()
        if free_gb >= 100:
            return CheckResult(
                name="Espace disque",
                status=CheckStatus.OK,
                message=f"Espace disque suffisant : {free_gb:.1f} GB",
            )
        elif free_gb >= min_gb:
            return CheckResult(
                name="Espace disque",
                status=CheckStatus.WARNING,
                message=f"Espace disque limité : {free_gb:.1f} GB (100+ GB recommandés)",
            )
        else:
            return CheckResult(
                name="Espace disque",
                status=CheckStatus.ERROR,
                message=f"Espace disque insuffisant : {free_gb:.1f} GB (minimum {min_gb} GB requis)",
            )

    def check_internet(self) -> CheckResult:
        """Vérifie la connexion Internet"""
        if self._check_internet():
            return CheckResult(
                name="Connexion Internet",
                status=CheckStatus.OK,
                message="Connexion Internet disponible",
            )
        else:
            return CheckResult(
                name="Connexion Internet",
                status=CheckStatus.ERROR,
                message="Pas de connexion Internet",
            )

    def check_dns(self) -> CheckResult:
        """Vérifie la résolution DNS"""
        if self._check_dns():
            return CheckResult(
                name="Résolution DNS", status=CheckStatus.OK, message="DNS fonctionnel"
            )
        else:
            return CheckResult(
                name="Résolution DNS",
                status=CheckStatus.ERROR,
                message="Échec de résolution DNS",
            )

    def check_ntp(self) -> CheckResult:
        """Vérifie la synchronisation NTP"""
        if self._check_ntp():
            return CheckResult(
                name="Synchronisation NTP",
                status=CheckStatus.OK,
                message="NTP synchronisé",
            )
        else:
            return CheckResult(
                name="Synchronisation NTP",
                status=CheckStatus.WARNING,
                message="NTP non synchronisé",
            )

    def check_sudo(self) -> CheckResult:
        """Vérifie les privilèges sudo"""
        if self._check_sudo():
            return CheckResult(
                name="Privilèges sudo",
                status=CheckStatus.OK,
                message="Accès sudo disponible",
            )
        else:
            return CheckResult(
                name="Privilèges sudo",
                status=CheckStatus.ERROR,
                message="Accès sudo requis",
            )

    def check_systemd(self) -> CheckResult:
        """Vérifie la présence de systemd"""
        if self._check_systemd():
            return CheckResult(
                name="Systemd", status=CheckStatus.OK, message="Systemd disponible"
            )
        else:
            return CheckResult(
                name="Systemd",
                status=CheckStatus.ERROR,
                message="Systemd requis mais non trouvé",
            )

    def check_virtualization(self) -> CheckResult:
        """Détecte la virtualisation"""
        virt = self._detect_virtualization()
        if virt == "none":
            return CheckResult(
                name="Virtualisation", status=CheckStatus.OK, message="Machine physique"
            )
        else:
            return CheckResult(
                name="Virtualisation",
                status=CheckStatus.WARNING,
                message=f"Machine virtualisée : {virt}",
            )

    def check_selinux(self) -> CheckResult:
        """Vérifie le statut SELinux"""
        mode = self._get_selinux_mode()
        if mode == "disabled":
            return CheckResult(
                name="SELinux", status=CheckStatus.OK, message="SELinux désactivé"
            )
        elif mode == "permissive":
            return CheckResult(
                name="SELinux",
                status=CheckStatus.WARNING,
                message="SELinux en mode permissif",
            )
        else:
            return CheckResult(
                name="SELinux",
                status=CheckStatus.WARNING,
                message=f"SELinux actif : {mode}",
            )

    def check_apparmor(self) -> CheckResult:
        """Vérifie le statut AppArmor"""
        status = self._get_apparmor_status()
        if status == "inactive":
            return CheckResult(
                name="AppArmor", status=CheckStatus.OK, message="AppArmor inactif"
            )
        else:
            return CheckResult(
                name="AppArmor",
                status=CheckStatus.WARNING,
                message=f"AppArmor actif : {status}",
            )

    def check_firewall(self) -> CheckResult:
        """Vérifie le pare-feu"""
        if self._check_firewall():
            return CheckResult(
                name="Pare-feu",
                status=CheckStatus.WARNING,
                message="Pare-feu actif - ports à ouvrir manuellement",
            )
        else:
            return CheckResult(
                name="Pare-feu", status=CheckStatus.OK, message="Pare-feu inactif"
            )

    def check_ports(self, required_ports: List[int]) -> List[CheckResult]:
        """Vérifie la disponibilité des ports"""
        results = []
        used_ports = self._get_used_ports()

        for port in required_ports:
            if port in used_ports:
                results.append(
                    CheckResult(
                        name=f"Port {port}",
                        status=CheckStatus.ERROR,
                        message=f"Port {port} déjà utilisé",
                    )
                )
            else:
                results.append(
                    CheckResult(
                        name=f"Port {port}",
                        status=CheckStatus.OK,
                        message=f"Port {port} disponible",
                    )
                )

        return results

    # Méthodes privées

    def _get_distro(self) -> str:
        """Détecte la distribution Linux"""
        try:
            # Essayer avec /etc/os-release
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release") as f:
                    for line in f:
                        if line.startswith("ID="):
                            return line.split("=")[1].strip().strip('"')
        except Exception:
            pass

        # Fallback
        return platform.system()

    def _get_distro_version(self) -> str:
        """Détecte la version de la distribution"""
        try:
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release") as f:
                    for line in f:
                        if line.startswith("VERSION_ID="):
                            return line.split("=")[1].strip().strip('"')
        except Exception:
            pass

        return platform.release()

    def _get_ram_gb(self) -> float:
        """Récupère la mémoire RAM en GB"""
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        return int(line.split()[1]) / (
                            1024 * 1024
                        )  # Convertir KB en GB
        except Exception:
            pass

        return 0.0

    def _get_disk_free_gb(self) -> float:
        """Récupère l'espace disque libre en GB"""
        try:
            stat = shutil.disk_usage("/")
            return stat.free / (1024 * 1024 * 1024)  # Convertir bytes en GB
        except Exception:
            return 0.0

    def _check_internet(self) -> bool:
        """Vérifie la connexion Internet"""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except Exception:
            return False

    def _check_dns(self) -> bool:
        """Vérifie la résolution DNS"""
        try:
            socket.gethostbyname("google.com")
            return True
        except Exception:
            return False

    def _check_ntp(self) -> bool:
        """Vérifie la synchronisation NTP"""
        try:
            result = subprocess.run(
                ["timedatectl", "status"], capture_output=True, text=True, timeout=5
            )
            return "System clock synchronized: yes" in result.stdout
        except Exception:
            return False

    def _check_sudo(self) -> bool:
        """Vérifie les privilèges sudo"""
        try:
            result = subprocess.run(
                ["sudo", "-n", "true"], capture_output=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def _check_systemd(self) -> bool:
        """Vérifie la présence de systemd"""
        try:
            result = subprocess.run(
                ["systemctl", "--version"], capture_output=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def _detect_virtualization(self) -> str:
        """Détecte la virtualisation"""
        try:
            result = subprocess.run(
                ["systemd-detect-virt"], capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def _get_selinux_mode(self) -> str:
        """Récupère le mode SELinux"""
        try:
            result = subprocess.run(
                ["getenforce"], capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip().lower()
        except Exception:
            return "unknown"

    def _get_apparmor_status(self) -> str:
        """Récupère le statut AppArmor"""
        try:
            result = subprocess.run(
                ["aa-status", "--enabled"], capture_output=True, timeout=5
            )
            return "active" if result.returncode == 0 else "inactive"
        except Exception:
            return "unknown"

    def _check_firewall(self) -> bool:
        """Vérifie si le pare-feu est actif"""
        # Vérifier ufw
        try:
            result = subprocess.run(
                ["ufw", "status"], capture_output=True, text=True, timeout=5
            )
            if "Status: active" in result.stdout:
                return True
        except Exception:
            pass

        # Vérifier firewalld
        try:
            result = subprocess.run(
                ["firewall-cmd", "--state"], capture_output=True, timeout=5
            )
            if result.returncode == 0:
                return True
        except Exception:
            pass

        return False

    def _get_used_ports(self) -> List[int]:
        """Récupère les ports utilisés"""
        ports = []
        try:
            result = subprocess.run(
                ["ss", "-tlnp"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split("\n"):
                if "LISTEN" in line:
                    parts = line.split()
                    for part in parts:
                        if ":" in part:
                            try:
                                port = int(part.split(":")[-1])
                                ports.append(port)
                            except Exception:
                                pass
        except Exception:
            pass

        return ports

    def format_report(self, checks: List[CheckResult]) -> str:
        """Formate le rapport de vérification"""
        report = []
        report.append("=" * 60)
        report.append("RAPPORT DE VÉRIFICATION SYSTÈME")
        report.append("=" * 60)

        ok_count = sum(1 for c in checks if c.status == CheckStatus.OK)
        warning_count = sum(1 for c in checks if c.status == CheckStatus.WARNING)
        error_count = sum(1 for c in checks if c.status == CheckStatus.ERROR)

        for check in checks:
            report.append(f"{check.status.value} {check.name}: {check.message}")

        report.append("")
        report.append(
            f"Résumé : {ok_count} OK, {warning_count} avertissements, {error_count} erreurs"
        )

        return "\n".join(report)
