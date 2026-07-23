"""
Modèles de configuration Pydantic
"""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class DeploymentMode(str, Enum):
    """Mode de déploiement"""

    SINGLE = "single"
    MULTI = "multi"
    CLUSTER = "cluster"


class SystemInfo(BaseModel):
    """Informations système"""

    distro: str
    version: str
    arch: str
    cpu_count: int
    ram_gb: float
    disk_free_gb: float
    has_internet: bool = False
    dns_ok: bool = False
    ntp_synced: bool = False
    has_sudo: bool = False
    has_systemd: bool = False
    selinux_mode: str = "disabled"
    apparmor_status: str = "unknown"
    firewall_active: bool = False
    used_ports: List[int] = Field(default_factory=list)
    virtualization: str = "none"


class FrameworkConfig(BaseModel):
    """Configuration globale du framework"""

    log_level: str = "INFO"
    log_dir: str = "/var/log/soc-deploy"
    backup_dir: str = "/var/backups/soc-deploy"
    plugin_dirs: List[str] = Field(default_factory=lambda: ["external_plugins"])
    max_parallel_installations: int = 1
    default_timeout: int = 300
