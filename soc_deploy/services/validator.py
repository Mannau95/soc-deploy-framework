"""
Service de validation des déploiements
"""

import http.client
import socket
import ssl
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from soc_deploy.services.executor import CommandExecutor, ExecutionStatus
from soc_deploy.utils.logger import LoggerManager


class ValidationStatus(Enum):
    """Statut de validation"""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class ValidationResult:
    """Résultat d'une validation"""

    name: str
    status: ValidationStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    duration: float = 0.0


@dataclass
class ValidationSuite:
    """Suite de validations"""

    tool_name: str
    results: List[ValidationResult]
    overall_status: ValidationStatus
    total_duration: float


class ValidatorService:
    """Service de validation"""

    def __init__(self, executor: CommandExecutor, logger: LoggerManager):
        self.executor = executor
        self.logger = logger.get_logger("validator")

    async def validate_service_running(self, service_name: str) -> ValidationResult:
        """
        Vérifie qu'un service systemd est actif

        Args:
            service_name: Nom du service

        Returns:
            ValidationResult
        """
        start = time.time()
        result = await self.executor.execute(f"systemctl is-active {service_name}")
        duration = time.time() - start

        if result.status == ExecutionStatus.SUCCESS and "active" in result.stdout:
            return ValidationResult(
                name=f"Service {service_name}",
                status=ValidationStatus.PASSED,
                message=f"Service {service_name} est actif",
                duration=duration,
            )
        else:
            return ValidationResult(
                name=f"Service {service_name}",
                status=ValidationStatus.FAILED,
                message=f"Service {service_name} inactif ou inexistant",
                details={"stdout": result.stdout, "stderr": result.stderr},
                duration=duration,
            )

    async def validate_port_open(
        self, host: str, port: int, timeout: float = 5.0
    ) -> ValidationResult:
        """
        Vérifie qu'un port TCP est ouvert

        Args:
            host: Hôte
            port: Port
            timeout: Timeout en secondes

        Returns:
            ValidationResult
        """
        start = time.time()
        try:
            sock = socket.create_connection((host, port), timeout=timeout)
            sock.close()
            duration = time.time() - start
            return ValidationResult(
                name=f"Port {host}:{port}",
                status=ValidationStatus.PASSED,
                message=f"Port {port} accessible sur {host}",
                duration=duration,
            )
        except Exception as e:
            duration = time.time() - start
            return ValidationResult(
                name=f"Port {host}:{port}",
                status=ValidationStatus.FAILED,
                message=f"Port {port} inaccessible sur {host}",
                details={"error": str(e)},
                duration=duration,
            )

    async def validate_http_endpoint(
        self,
        url: str,
        expected_status: int = 200,
        timeout: float = 10.0,
        verify_ssl: bool = True,
    ) -> ValidationResult:
        """
        Vérifie qu'un endpoint HTTP répond correctement

        Args:
            url: URL à tester
            expected_status: Code HTTP attendu
            timeout: Timeout
            verify_ssl: Vérifier le certificat SSL

        Returns:
            ValidationResult
        """
        start = time.time()
        try:
            parsed = urlparse(url)
            # build SSL context according to verify_ssl
            ctx = None
            if parsed.scheme == "https":
                if verify_ssl:
                    ctx = ssl.create_default_context()
                else:
                    ctx = ssl._create_unverified_context()

            req = Request(url, method="GET")
            with urlopen(req, timeout=timeout, context=ctx) as resp:
                status_code = resp.getcode()
            duration = time.time() - start

            if status_code == expected_status:
                return ValidationResult(
                    name=f"HTTP {url}",
                    status=ValidationStatus.PASSED,
                    message=f"Endpoint répond avec {status_code}",
                    duration=duration,
                )
            else:
                return ValidationResult(
                    name=f"HTTP {url}",
                    status=ValidationStatus.WARNING,
                    message=f"Code {status_code} au lieu de {expected_status}",
                    details={"status_code": status_code},
                    duration=duration,
                )
        except ssl.SSLError as e:
            duration = time.time() - start
            return ValidationResult(
                name=f"HTTP {url}",
                status=ValidationStatus.FAILED,
                message="Erreur SSL",
                details={"error": str(e)},
                duration=duration,
            )
        except (HTTPError, URLError, http.client.HTTPException, OSError) as e:
            duration = time.time() - start
            return ValidationResult(
                name=f"HTTP {url}",
                status=ValidationStatus.FAILED,
                message="Endpoint inaccessible",
                details={"error": str(e)},
                duration=duration,
            )

    async def validate_ssl_certificate(
        self,
        hostname: str,
        port: int = 443,
        timeout: float = 5.0,
    ) -> ValidationResult:
        """
        Vérifie la validité d'un certificat SSL

        Args:
            hostname: Nom d'hôte
            port: Port
            timeout: Timeout

        Returns:
            ValidationResult
        """
        start = time.time()
        try:
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    duration = time.time() - start

                    # Vérifier la date d'expiration
                    import datetime

                    not_after = datetime.datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                    days_left = (not_after - datetime.datetime.utcnow()).days

                    if days_left > 30:
                        return ValidationResult(
                            name=f"SSL {hostname}:{port}",
                            status=ValidationStatus.PASSED,
                            message=f"Certificat valide, expire dans {days_left} jours",
                            details={"subject": dict(x[0] for x in cert["subject"])},
                            duration=duration,
                        )
                    else:
                        return ValidationResult(
                            name=f"SSL {hostname}:{port}",
                            status=ValidationStatus.WARNING,
                            message=f"Certificat expire dans {days_left} jours",
                            duration=duration,
                        )
        except Exception as e:
            duration = time.time() - start
            return ValidationResult(
                name=f"SSL {hostname}:{port}",
                status=ValidationStatus.FAILED,
                message=f"Erreur SSL: {str(e)}",
                duration=duration,
            )

    async def validate_docker_container(self, container_name: str) -> ValidationResult:
        """
        Vérifie l'état d'un conteneur Docker

        Args:
            container_name: Nom du conteneur

        Returns:
            ValidationResult
        """
        start = time.time()
        result = await self.executor.execute(
            f"docker inspect --format '{{{{.State.Status}}}}' {container_name}"
        )
        duration = time.time() - start

        if result.status != ExecutionStatus.SUCCESS:
            return ValidationResult(
                name=f"Container {container_name}",
                status=ValidationStatus.FAILED,
                message="Conteneur introuvable",
                duration=duration,
            )

        status = result.stdout.strip()
        if status == "running":
            return ValidationResult(
                name=f"Container {container_name}",
                status=ValidationStatus.PASSED,
                message="Conteneur en cours d'exécution",
                duration=duration,
            )
        else:
            return ValidationResult(
                name=f"Container {container_name}",
                status=ValidationStatus.FAILED,
                message=f"Conteneur statut: {status}",
                duration=duration,
            )

    async def validate_disk_space(self, path: str = "/", min_gb: float = 10.0) -> ValidationResult:
        """
        Vérifie l'espace disque disponible

        Args:
            path: Chemin à vérifier
            min_gb: Espace minimum en GB

        Returns:
            ValidationResult
        """
        import shutil

        start = time.time()
        usage = shutil.disk_usage(path)
        free_gb = usage.free / (1024**3)
        duration = time.time() - start

        if free_gb >= min_gb:
            return ValidationResult(
                name=f"Espace disque {path}",
                status=ValidationStatus.PASSED,
                message=f"{free_gb:.1f} GB disponibles",
                duration=duration,
            )
        else:
            return ValidationResult(
                name=f"Espace disque {path}",
                status=ValidationStatus.FAILED,
                message=f"Seulement {free_gb:.1f} GB disponibles (min {min_gb} GB)",
                duration=duration,
            )

    async def validate_memory_usage(self, max_percent: float = 90.0) -> ValidationResult:
        """
        Vérifie l'utilisation mémoire

        Args:
            max_percent: Pourcentage maximum acceptable

        Returns:
            ValidationResult
        """
        start = time.time()
        result = await self.executor.execute("free | grep Mem | awk '{print $3/$2 * 100.0}'")
        duration = time.time() - start

        if result.status != ExecutionStatus.SUCCESS:
            return ValidationResult(
                name="Utilisation mémoire",
                status=ValidationStatus.FAILED,
                message="Impossible de récupérer l'utilisation mémoire",
                duration=duration,
            )

        try:
            usage = float(result.stdout.strip())
            if usage < max_percent:
                return ValidationResult(
                    name="Utilisation mémoire",
                    status=ValidationStatus.PASSED,
                    message=f"{usage:.1f}% utilisée",
                    duration=duration,
                )
            else:
                return ValidationResult(
                    name="Utilisation mémoire",
                    status=ValidationStatus.WARNING,
                    message=f"{usage:.1f}% utilisée (seuil {max_percent}%)",
                    duration=duration,
                )
        except ValueError:
            return ValidationResult(
                name="Utilisation mémoire",
                status=ValidationStatus.FAILED,
                message="Valeur invalide",
                duration=duration,
            )

    async def run_validation_suite(
        self,
        tool_name: str,
        validations: List[Callable[[], ValidationResult]],
    ) -> ValidationSuite:
        """
        Exécute une suite de validations

        Args:
            tool_name: Nom de l'outil
            validations: Liste de fonctions async retournant ValidationResult

        Returns:
            ValidationSuite
        """
        results = []
        total_start = time.time()

        for validation_fn in validations:
            try:
                result = await validation_fn()
                results.append(result)
                self.logger.info(f"Validation {result.name}: {result.status.value}")
            except Exception as e:
                self.logger.error(f"Erreur validation: {e}")
                results.append(
                    ValidationResult(
                        name="Erreur",
                        status=ValidationStatus.FAILED,
                        message=str(e),
                    )
                )

        total_duration = time.time() - total_start

        # Déterminer le statut global
        if any(r.status == ValidationStatus.FAILED for r in results):
            overall = ValidationStatus.FAILED
        elif any(r.status == ValidationStatus.WARNING for r in results):
            overall = ValidationStatus.WARNING
        else:
            overall = ValidationStatus.PASSED

        return ValidationSuite(
            tool_name=tool_name,
            results=results,
            overall_status=overall,
            total_duration=total_duration,
        )

    def format_validation_report(self, suite: ValidationSuite) -> str:
        """Formate un rapport de validation lisible"""
        lines = [
            f"\n{'=' * 60}",
            f"RAPPORT DE VALIDATION : {suite.tool_name}",
            f"Statut global : {suite.overall_status.value.upper()}",
            f"Durée totale : {suite.total_duration:.2f}s",
            f"{'=' * 60}",
        ]

        for result in suite.results:
            icon = {
                ValidationStatus.PASSED: "✅",
                ValidationStatus.FAILED: "❌",
                ValidationStatus.WARNING: "⚠️",
                ValidationStatus.SKIPPED: "⏭️",
            }.get(result.status, "❓")

            lines.append(f"{icon} {result.name}: {result.message}")

        return "\n".join(lines)
