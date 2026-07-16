"""
Service d'exécution de commandes système
"""
import asyncio
import subprocess
import shlex
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from soc_deploy.utils.logger import LoggerManager


class ExecutionStatus(Enum):
    """Statut d'exécution"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    INTERRUPTED = "interrupted"


@dataclass
class CommandResult:
    """Résultat d'une commande"""
    command: str
    status: ExecutionStatus
    returncode: int
    stdout: str
    stderr: str
    duration: float
    attempts: int = 1


class CommandExecutor:
    """Exécuteur de commandes avec retry et timeout"""

    def __init__(self, logger: LoggerManager):
        self.logger = logger.get_logger("executor")

    async def execute(
        self,
        command: str,
        timeout: int = 300,
        shell: bool = False,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        sudo: bool = False,
    ) -> CommandResult:
        """
        Exécute une commande système

        Args:
            command: Commande à exécuter
            timeout: Timeout en secondes
            shell: Utiliser le shell
            env: Variables d'environnement supplémentaires
            cwd: Répertoire de travail
            sudo: Exécuter avec sudo

        Returns:
            CommandResult
        """
        if sudo:
            command = f"sudo {command}"

        self.logger.info(f"Exécution : {command[:100]}...")

        import time
        start_time = time.time()

        try:
            # Préparer la commande
            if shell:
                cmd = command
            else:
                cmd = shlex.split(command)

            # Exécuter la commande
            process = await asyncio.create_subprocess_exec(
                *cmd if isinstance(cmd, list) else [cmd],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=cwd,
                shell=shell,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return CommandResult(
                    command=command,
                    status=ExecutionStatus.TIMEOUT,
                    returncode=-1,
                    stdout="",
                    stderr=f"Timeout après {timeout}s",
                    duration=time.time() - start_time,
                )

            duration = time.time() - start_time
            returncode = process.returncode

            stdout_str = stdout.decode("utf-8", errors="ignore") if stdout else ""
            stderr_str = stderr.decode("utf-8", errors="ignore") if stderr else ""

            if returncode == 0:
                status = ExecutionStatus.SUCCESS
                self.logger.info(f"Succès : {command[:50]}... (duration={duration:.2f}s)")
            else:
                status = ExecutionStatus.FAILED
                self.logger.error(f"Échec ({returncode}): {command[:50]}... {stderr_str[:200]}")

            return CommandResult(
                command=command,
                status=status,
                returncode=returncode,
                stdout=stdout_str,
                stderr=stderr_str,
                duration=duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Exception : {command[:50]}... {str(e)}")
            return CommandResult(
                command=command,
                status=ExecutionStatus.FAILED,
                returncode=-1,
                stdout="",
                stderr=str(e),
                duration=duration,
            )

    async def execute_with_retry(
        self,
        command: str,
        retries: int = 3,
        delay: int = 5,
        timeout: int = 300,
        **kwargs,
    ) -> CommandResult:
        """
        Exécute une commande avec réessai en cas d'échec

        Args:
            command: Commande à exécuter
            retries: Nombre de tentatives
            delay: Délai entre les tentatives en secondes
            timeout: Timeout par tentative
            **kwargs: Arguments supplémentaires pour execute()

        Returns:
            CommandResult
        """
        last_result = None

        for attempt in range(1, retries + 1):
            self.logger.info(f"Tentative {attempt}/{retries} : {command[:50]}...")
            result = await self.execute(command, timeout=timeout, **kwargs)
            result.attempts = attempt

            if result.status == ExecutionStatus.SUCCESS:
                return result

            last_result = result

            if attempt < retries:
                self.logger.warning(f"Tentative {attempt} échouée, nouvelle tentative dans {delay}s")
                await asyncio.sleep(delay)

        self.logger.error(f"Toutes les tentatives ont échoué après {retries} essais")
        return last_result

    async def execute_script(
        self,
        script_content: str,
        interpreter: str = "/bin/bash",
        timeout: int = 600,
    ) -> CommandResult:
        """
        Exécute un script via un interpréteur

        Args:
            script_content: Contenu du script
            interpreter: Interpréteur à utiliser
            timeout: Timeout en secondes

        Returns:
            CommandResult
        """
        import tempfile
        import os

        # Créer un fichier temporaire pour le script
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(script_content)
            script_path = f.name

        try:
            # Rendre le script exécutable
            os.chmod(script_path, 0o755)

            # Exécuter le script
            result = await self.execute(
                f"{interpreter} {script_path}",
                timeout=timeout,
            )
            return result
        finally:
            # Nettoyer le fichier temporaire
            try:
                os.unlink(script_path)
            except:
                pass

    async def check_command_exists(self, command: str) -> bool:
        """
        Vérifie si une commande existe

        Args:
            command: Nom de la commande

        Returns:
            True si la commande existe
        """
        result = await self.execute(f"which {command}")
        return result.status == ExecutionStatus.SUCCESS

    async def get_command_version(self, command: str, version_flag: str = "--version") -> Optional[str]:
        """
        Récupère la version d'une commande

        Args:
            command: Nom de la commande
            version_flag: Flag pour obtenir la version

        Returns:
            Version ou None
        """
        result = await self.execute(f"{command} {version_flag}")
        if result.status == ExecutionStatus.SUCCESS:
            return result.stdout.strip().split("\n")[0]
        return None