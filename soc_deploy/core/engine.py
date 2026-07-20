"""
Orchestrateur principal du framework
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from soc_deploy.core.context import ExecutionContext
from soc_deploy.core.state import StateManager, ToolStatus
from soc_deploy.core.exceptions import (
    SOCDeployError,
    PrerequisitesError,
    InstallationError,
    ConfigurationError,
    ValidationError,
)
from soc_deploy.deployment.planner import DeploymentPlanner
from soc_deploy.deployment.dependency import DependencyResolver
from soc_deploy.models.report import DeploymentReport, ToolReport


class Orchestrator:
    """
    Orchestrateur principal.
    Coordonne les déploiements, les rollbacks, et la reprise.
    """

    def __init__(self, ctx: ExecutionContext, state_manager: StateManager):
        self.ctx = ctx
        self.state = state_manager
        self.log = ctx.get_logger("engine")

        # Services internes
        self.planner = DeploymentPlanner(DependencyResolver())
        # Les services sont accessibles via ctx

    async def deploy_soc(
        self,
        tools: List[str],
        profile: Optional[str] = None,
        interactive: bool = True,
    ) -> DeploymentReport:
        """
        Déploie un ensemble d'outils SOC.

        Args:
            tools: Liste des noms d'outils à déployer
            profile: Profil de configuration prédéfini
            interactive: Mode interactif (questions à l'utilisateur)

        Returns:
            DeploymentReport
        """
        self.ctx.interactive = interactive
        self.ctx.clear_errors()

        # 1. Vérifications préliminaires
        self.log.info("Vérification des prérequis système...")
        checks = self.ctx.system_checker.run_all_checks()
        critical_failures = [c for c in checks if c.status.name == "ERROR"]
        if critical_failures:
            self.log.error("Prérequis système non satisfaits")
            if interactive:
                # Afficher le rapport et demander continuation
                pass
            else:
                raise PrerequisitesError(
                    f"Échec des prérequis: {len(critical_failures)} erreurs"
                )

        # 2. Planifier le déploiement
        self.log.info("Planification du déploiement...")
        plan = self.planner.create_plan(tools, profile)
        if plan.conflicts:
            self.log.warning(f"Conflits détectés: {plan.conflicts}")
            # Gérer les conflits...

        # 3. Créer l'enregistrement du déploiement
        deployment_id = await self.state.create_deployment(
            name=f"SOC-{'-'.join(tools[:3])}", profile=profile
        )
        await self.state.start_deployment(deployment_id)

        # 4. Ajouter les outils dans l'ordre
        for i, tool_name in enumerate(plan.order):
            await self.state.add_tool_to_deployment(
                deployment_id, tool_name, order=i + 1
            )

        self.ctx.set_step(deployment_id, "", "PLAN", 0, len(plan.order))

        # 5. Exécuter le déploiement outil par outil
        tool_reports = []
        for idx, tool_name in enumerate(plan.order, start=1):
            self.ctx.set_step(deployment_id, tool_name, "DEPLOY", idx, len(plan.order))
            self.log.info(
                f"\n{'=' * 50}\nDéploiement de {tool_name} ({idx}/{len(plan.order)})\n{'=' * 50}"
            )

            try:
                tool_report = await self._deploy_single_tool(
                    deployment_id, tool_name, plan.configs.get(tool_name, {})
                )
                tool_reports.append(tool_report)

                if tool_report.status == "failed":
                    # Décision : arrêter ou continuer ?
                    if interactive:
                        # demander à l'utilisateur
                        pass
                    else:
                        # En mode non-interactif, on arrête par défaut
                        self.log.error(f"Échec de {tool_name}, arrêt du déploiement")
                        break
            except Exception as e:
                self.log.exception(f"Erreur inattendue pour {tool_name}: {e}")
                tool_reports.append(
                    ToolReport(
                        tool_name=tool_name,
                        status="failed",
                        error=str(e),
                    )
                )
                break

            # Checkpoint global
            await self.state.save_checkpoint(
                deployment_id, tool_name, "POST_DEPLOY", {"tool_status": "completed"}
            )

            # Si interactif, proposer pause/continuer
            if interactive and idx < len(plan.order):
                # afficher menu pause/continuer
                pass

        # 6. Finalisation
        all_success = all(r.status == "success" for r in tool_reports)
        if all_success:
            await self.state.complete_deployment(deployment_id)
        else:
            await self.state.fail_deployment(deployment_id)

        return DeploymentReport(
            deployment_id=deployment_id,
            status="success" if all_success else "partial_failure",
            tools=tool_reports,
        )

    async def _deploy_single_tool(
        self,
        deployment_id: str,
        tool_name: str,
        user_config: Dict[str, Any],
    ) -> ToolReport:
        """
        Déploie un seul outil en suivant le cycle : prereq -> backup -> install -> configure -> validate
        """
        plugin = self.ctx.plugin_registry.get_plugin(tool_name)
        if not plugin:
            raise SOCDeployError(f"Plugin introuvable pour {tool_name}")

        await self.state.set_tool_status(
            deployment_id, tool_name, ToolStatus.IN_PROGRESS
        )

        try:
            # 1. Prérequis
            await self.state.save_checkpoint(
                deployment_id, tool_name, "PREREQ_CHECK", {}
            )
            prereq_result = await plugin.check_prerequisites(self.ctx)
            if not prereq_result.get("success", False):
                raise PrerequisitesError(
                    f"Prérequis {tool_name} non satisfaits: {prereq_result}"
                )

            # 2. Backup (avant toute modification)
            await self.state.save_checkpoint(deployment_id, tool_name, "BACKUP", {})
            backup_result = await plugin.backup(self.ctx)
            if backup_result:
                # Enregistrer la sauvegarde
                await self.state.save_checkpoint(
                    deployment_id, tool_name, "BACKUP_DONE", {"backup": backup_result}
                )

            # 3. Installation
            await self.state.save_checkpoint(deployment_id, tool_name, "INSTALL", {})
            install_result = await plugin.install(self.ctx, user_config)
            if not install_result.get("success", False):
                # Tentative de rollback automatique
                self.log.warning(
                    f"Installation de {tool_name} échouée, tentative de rollback"
                )
                await plugin.rollback(self.ctx)
                raise InstallationError(f"Installation échouée: {install_result}")

            # 4. Configuration
            await self.state.save_checkpoint(deployment_id, tool_name, "CONFIGURE", {})
            config_result = await plugin.configure(self.ctx, user_config)
            if not config_result.get("success", False):
                raise ConfigurationError(f"Configuration échouée: {config_result}")

            # 5. Validation
            await self.state.save_checkpoint(deployment_id, tool_name, "VALIDATE", {})
            validation_result = await plugin.validate(self.ctx)
            if not validation_result.get("success", False):
                self.log.error(
                    f"Validation échouée pour {tool_name}: {validation_result}"
                )
                # Optionnel : rollback ?
                raise ValidationError(f"Validation échouée: {validation_result}")

            # Succès
            await self.state.set_tool_status(
                deployment_id, tool_name, ToolStatus.COMPLETED, config=user_config
            )
            return ToolReport(tool_name=tool_name, status="success")

        except SOCDeployError as e:
            self.log.error(f"Échec déploiement {tool_name}: {e}")
            await self.state.set_tool_status(
                deployment_id, tool_name, ToolStatus.FAILED
            )
            return ToolReport(tool_name=tool_name, status="failed", error=str(e))
        except Exception as e:
            self.log.exception(f"Erreur inconnue: {e}")
            await self.state.set_tool_status(
                deployment_id, tool_name, ToolStatus.FAILED
            )
            return ToolReport(tool_name=tool_name, status="failed", error=str(e))

    async def resume_deployment(self, deployment_id: str) -> DeploymentReport:
        """
        Reprend un déploiement interrompu.
        """
        resume_info = await self.state.get_resume_info(deployment_id)
        if not resume_info:
            self.log.info("Aucun déploiement à reprendre (déjà terminé)")
            return DeploymentReport(
                deployment_id=deployment_id, status="already_completed", tools=[]
            )

        tool_name = resume_info["tool_name"]
        step = resume_info["step"]
        state_data = resume_info["state_data"]

        self.log.info(
            f"Reprise du déploiement {deployment_id} pour {tool_name} à l'étape {step}"
        )

        # Récupérer la liste complète des outils
        tools = await self.state.get_deployment_tools(deployment_id)
        remaining_tools = [
            t["tool_name"]
            for t in tools
            if t["status"] not in (ToolStatus.COMPLETED.value, ToolStatus.SKIPPED.value)
        ]

        # Si l'outil en cours est déjà dans la liste, on le déploie en premier
        # (gestion simplifiée : on reprend à partir de l'outil spécifié)
        tool_reports = []
        start_idx = next(
            (i for i, t in enumerate(remaining_tools) if t == tool_name), 0
        )

        for tool_name in remaining_tools[start_idx:]:
            try:
                report = await self._deploy_single_tool(
                    deployment_id, tool_name, state_data.get("config", {})
                )
                tool_reports.append(report)
                if report.status == "failed":
                    break
            except Exception as e:
                tool_reports.append(
                    ToolReport(tool_name=tool_name, status="failed", error=str(e))
                )
                break

        all_success = all(r.status == "success" for r in tool_reports)
        if all_success and len(tool_reports) == len(remaining_tools[start_idx:]):
            await self.state.complete_deployment(deployment_id)
        else:
            await self.state.fail_deployment(deployment_id)

        return DeploymentReport(
            deployment_id=deployment_id,
            status="success" if all_success else "partial_failure",
            tools=tool_reports,
        )

    async def install_single_tool(
        self, tool_name: str, config: Optional[Dict] = None, interactive: bool = True
    ) -> ToolReport:
        """
        Installe un seul outil hors déploiement global.
        """
        deployment_id = await self.state.create_deployment(f"single-{tool_name}")
        await self.state.start_deployment(deployment_id)
        await self.state.add_tool_to_deployment(deployment_id, tool_name)

        report = await self._deploy_single_tool(deployment_id, tool_name, config or {})
        (
            await self.state.complete_deployment(deployment_id)
            if report.status == "success"
            else await self.state.fail_deployment(deployment_id)
        )
        return report

    async def rollback_tool(self, deployment_id: str, tool_name: str) -> bool:
        """
        Effectue un rollback pour un outil spécifique dans un déploiement.
        """
        plugin = self.ctx.plugin_registry.get_plugin(tool_name)
        if not plugin:
            return False
        self.log.info(f"Rollback de {tool_name} dans le déploiement {deployment_id}")
        result = await plugin.rollback(self.ctx)
        return result.get("success", False)
