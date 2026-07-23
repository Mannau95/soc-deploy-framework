"""
Service de gestion Docker et Docker Compose
"""

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from soc_deploy.services.executor import CommandExecutor, ExecutionStatus


class ContainerStatus(Enum):
    """Statut d'un conteneur"""

    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    RESTARTING = "restarting"
    DEAD = "dead"
    NOT_FOUND = "not_found"


@dataclass
class DockerInfo:
    """Informations Docker"""

    installed: bool
    version: Optional[str] = None
    compose_installed: bool = False
    compose_version: Optional[str] = None
    daemon_running: bool = False
    swarm_active: bool = False


@dataclass
class ContainerInfo:
    """Informations sur un conteneur"""

    name: str
    id: str
    image: str
    status: ContainerStatus
    ports: List[str]
    created: str
    health: Optional[str] = None


@dataclass
class ComposeService:
    """Service Docker Compose"""

    name: str
    image: Optional[str] = None
    build: Optional[str] = None
    ports: List[str] = None
    volumes: List[str] = None
    environment: Dict[str, str] = None
    depends_on: List[str] = None
    restart: str = "unless-stopped"


class DockerManager:
    """Gestionnaire Docker"""

    def __init__(self, executor: CommandExecutor):
        self.executor = executor

    async def check_docker(self) -> DockerInfo:
        """
        Vérifie l'installation et l'état de Docker

        Returns:
            DockerInfo
        """
        info = DockerInfo(installed=False)

        # Vérifier Docker
        docker_installed = await self.executor.check_command_exists("docker")
        if not docker_installed:
            return info

        info.installed = True

        # Version Docker
        version_result = await self.executor.execute("docker --version")
        if version_result.status == ExecutionStatus.SUCCESS:
            info.version = version_result.stdout.strip()

        # Vérifier Docker Compose
        compose_installed = await self.executor.check_command_exists(
            "docker-compose"
        ) or await self.executor.check_command_exists("docker compose")
        info.compose_installed = compose_installed

        if compose_installed:
            # Essayer docker compose (plugin) d'abord
            compose_version = await self.executor.execute("docker compose version")
            if compose_version.status != ExecutionStatus.SUCCESS:
                compose_version = await self.executor.execute("docker-compose --version")
            if compose_version.status == ExecutionStatus.SUCCESS:
                info.compose_version = compose_version.stdout.strip()

        # Vérifier le daemon Docker
        daemon_result = await self.executor.execute("docker info")
        info.daemon_running = daemon_result.status == ExecutionStatus.SUCCESS

        # Vérifier Swarm
        if info.daemon_running:
            swarm_result = await self.executor.execute(
                "docker info --format '{{.Swarm.LocalNodeState}}'"
            )
            info.swarm_active = "active" in swarm_result.stdout

        return info

    async def install_docker(self) -> bool:
        """
        Installe Docker et Docker Compose

        Returns:
            True si succès
        """
        # Script d'installation officiel Docker
        script = """#!/bin/bash
set -e

# Installation Docker
curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
sh /tmp/get-docker.sh
rm /tmp/get-docker.sh

# Installation Docker Compose plugin
apt-get update -y
apt-get install -y docker-compose-plugin

# Démarrer Docker
systemctl enable docker
systemctl start docker
"""

        result = await self.executor.execute_script(script, timeout=600)

        if result.status == ExecutionStatus.SUCCESS:
            # Vérifier l'installation
            info = await self.check_docker()
            return info.installed and info.daemon_running

        return False

    async def pull_image(self, image: str, tag: str = "latest") -> bool:
        """
        Télécharge une image Docker

        Args:
            image: Nom de l'image
            tag: Tag de l'image

        Returns:
            True si succès
        """
        result = await self.executor.execute(
            f"docker pull {image}:{tag}",
            timeout=300,
        )
        return result.status == ExecutionStatus.SUCCESS

    def _format_ports(self, ports: Dict[int, int]) -> List[str]:
        """Formate les options de ports"""
        if not ports:
            return []
        return [f"-p {host}:{container}" for host, container in ports.items()]

    def _format_volumes(self, volumes: Dict[str, str]) -> List[str]:
        """Formate les options de volumes"""
        if not volumes:
            return []
        return [f"-v {host}:{container}" for host, container in volumes.items()]

    def _format_env_vars(self, environment: Dict[str, str]) -> List[str]:
        """Formate les variables d'environnement"""
        if not environment:
            return []
        return [f"-e {key}={value}" for key, value in environment.items()]

    def _build_run_command(
        self,
        image: str,
        name: Optional[str] = None,
        ports: Optional[Dict[int, int]] = None,
        volumes: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
        detach: bool = True,
        network: Optional[str] = None,
        restart: str = "unless-stopped",
    ) -> str:
        """
        Construit la commande docker run
        """
        cmd_parts = ["docker run"]

        if detach:
            cmd_parts.append("-d")

        if name:
            cmd_parts.append(f"--name {name}")

        if restart:
            cmd_parts.append(f"--restart {restart}")

        if network:
            cmd_parts.append(f"--network {network}")

        cmd_parts.extend(self._format_ports(ports or {}))
        cmd_parts.extend(self._format_volumes(volumes or {}))
        cmd_parts.extend(self._format_env_vars(environment or {}))

        cmd_parts.append(image)
        return " ".join(cmd_parts)

    async def run_container(
        self,
        image: str,
        name: Optional[str] = None,
        ports: Optional[Dict[int, int]] = None,
        volumes: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
        detach: bool = True,
        network: Optional[str] = None,
        restart: str = "unless-stopped",
    ) -> Optional[str]:
        """
        Lance un conteneur Docker

        Args:
            image: Image Docker
            name: Nom du conteneur
            ports: Mapping de ports {host: container}
            volumes: Mapping de volumes {host: container}
            environment: Variables d'environnement
            detach: Mode détaché
            network: Réseau Docker
            restart: Politique de redémarrage

        Returns:
            ID du conteneur ou None
        """
        command = self._build_run_command(
            image=image,
            name=name,
            ports=ports,
            volumes=volumes,
            environment=environment,
            detach=detach,
            network=network,
            restart=restart,
        )
        result = await self.executor.execute(command, timeout=120)
        if result.status == ExecutionStatus.SUCCESS:
            return result.stdout.strip()
        return None

    async def stop_container(self, container: str) -> bool:
        """
        Arrête un conteneur

        Args:
            container: Nom ou ID du conteneur

        Returns:
            True si succès
        """
        result = await self.executor.execute(f"docker stop {container}")
        return result.status == ExecutionStatus.SUCCESS

    async def remove_container(self, container: str, force: bool = False) -> bool:
        """
        Supprime un conteneur

        Args:
            container: Nom ou ID du conteneur
            force: Forcer la suppression

        Returns:
            True si succès
        """
        flags = "-f" if force else ""
        result = await self.executor.execute(f"docker rm {flags} {container}")
        return result.status == ExecutionStatus.SUCCESS

    async def get_container_status(self, container: str) -> ContainerStatus:
        """
        Récupère le statut d'un conteneur

        Args:
            container: Nom ou ID du conteneur

        Returns:
            ContainerStatus
        """
        result = await self.executor.execute(
            f"docker inspect --format '{{{{.State.Status}}}}' {container}"
        )

        if result.status != ExecutionStatus.SUCCESS:
            return ContainerStatus.NOT_FOUND

        status_map = {
            "running": ContainerStatus.RUNNING,
            "stopped": ContainerStatus.STOPPED,
            "paused": ContainerStatus.PAUSED,
            "restarting": ContainerStatus.RESTARTING,
            "dead": ContainerStatus.DEAD,
        }

        return status_map.get(result.stdout.strip(), ContainerStatus.NOT_FOUND)

    async def get_container_logs(
        self,
        container: str,
        tail: int = 100,
        follow: bool = False,
    ) -> str:
        """
        Récupère les logs d'un conteneur

        Args:
            container: Nom ou ID du conteneur
            tail: Nombre de lignes
            follow: Suivre les logs

        Returns:
            Logs
        """
        flags = f"--tail {tail}"
        if follow:
            flags += " -f"

        result = await self.executor.execute(
            f"docker logs {flags} {container}",
            timeout=30 if not follow else 0,
        )
        return result.stdout

    async def compose_up(
        self,
        compose_file: Path,
        project_name: Optional[str] = None,
        detach: bool = True,
        build: bool = False,
    ) -> bool:
        """
        Lance docker-compose up

        Args:
            compose_file: Chemin vers le fichier docker-compose.yml
            project_name: Nom du projet
            detach: Mode détaché
            build: Reconstruire les images

        Returns:
            True si succès
        """
        if not compose_file.exists():
            return False

        cmd_parts = ["docker compose"]

        if project_name:
            cmd_parts.append(f"-p {project_name}")

        cmd_parts.append(f"-f {compose_file}")
        cmd_parts.append("up")

        if detach:
            cmd_parts.append("-d")

        if build:
            cmd_parts.append("--build")

        command = " ".join(cmd_parts)
        result = await self.executor.execute(command, timeout=300)

        return result.status == ExecutionStatus.SUCCESS

    async def compose_down(
        self,
        compose_file: Path,
        project_name: Optional[str] = None,
        volumes: bool = False,
    ) -> bool:
        """
        Arrête docker-compose

        Args:
            compose_file: Chemin vers le fichier docker-compose.yml
            project_name: Nom du projet
            volumes: Supprimer aussi les volumes

        Returns:
            True si succès
        """
        if not compose_file.exists():
            return False

        cmd_parts = ["docker compose"]

        if project_name:
            cmd_parts.append(f"-p {project_name}")

        cmd_parts.append(f"-f {compose_file}")
        cmd_parts.append("down")

        if volumes:
            cmd_parts.append("-v")

        command = " ".join(cmd_parts)
        result = await self.executor.execute(command, timeout=120)

        return result.status == ExecutionStatus.SUCCESS

    async def compose_ps(
        self,
        compose_file: Path,
        project_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Liste les services docker-compose

        Args:
            compose_file: Chemin vers le fichier docker-compose.yml
            project_name: Nom du projet

        Returns:
            Liste des services
        """
        cmd_parts = ["docker compose"]

        if project_name:
            cmd_parts.append(f"-p {project_name}")

        cmd_parts.append(f"-f {compose_file}")
        cmd_parts.append("ps --format json")

        command = " ".join(cmd_parts)
        result = await self.executor.execute(command)

        if result.status != ExecutionStatus.SUCCESS:
            return []

        try:
            services = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    services.append(json.loads(line))
            return services
        except json.JSONDecodeError:
            return []

    async def create_network(self, name: str, driver: str = "bridge") -> bool:
        """
        Crée un réseau Docker

        Args:
            name: Nom du réseau
            driver: Driver réseau

        Returns:
            True si succès
        """
        result = await self.executor.execute(f"docker network create --driver {driver} {name}")
        return result.status == ExecutionStatus.SUCCESS

    async def create_volume(self, name: str) -> bool:
        """
        Crée un volume Docker

        Args:
            name: Nom du volume

        Returns:
            True si succès
        """
        result = await self.executor.execute(f"docker volume create {name}")
        return result.status == ExecutionStatus.SUCCESS

    def generate_compose_file(
        self,
        services: List[ComposeService],
        networks: Optional[List[str]] = None,
        volumes: Optional[List[str]] = None,
        version: str = "3.8",
    ) -> Dict[str, Any]:
        """
        Génère un fichier docker-compose.yml

        Args:
            services: Liste des services
            networks: Liste des réseaux
            volumes: Liste des volumes
            version: Version du format

        Returns:
            Dictionnaire docker-compose
        """
        compose = {
            "version": version,
            "services": {},
        }

        if networks:
            compose["networks"] = {net: {} for net in networks}

        if volumes:
            compose["volumes"] = {vol: {} for vol in volumes}

        for service in services:
            service_dict = {}

            if service.image:
                service_dict["image"] = service.image
            if service.build:
                service_dict["build"] = service.build
            if service.ports:
                service_dict["ports"] = service.ports
            if service.volumes:
                service_dict["volumes"] = service.volumes
            if service.environment:
                service_dict["environment"] = service.environment
            if service.depends_on:
                service_dict["depends_on"] = service.depends_on

            service_dict["restart"] = service.restart

            compose["services"][service.name] = service_dict

        return compose
