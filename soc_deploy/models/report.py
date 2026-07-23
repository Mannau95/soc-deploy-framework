"""
Modèles de rapports de déploiement
"""

from typing import List, Optional

from pydantic import BaseModel


class ToolReport(BaseModel):
    """Rapport pour un outil individuel"""

    tool_name: str
    status: str  # "success", "failed", etc.
    error: Optional[str] = None


class DeploymentReport(BaseModel):
    """Rapport global d'un déploiement"""

    deployment_id: str
    status: str  # "success", "partial_failure", "already_completed"
    tools: List[ToolReport] = []
