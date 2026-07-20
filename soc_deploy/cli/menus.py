"""
Menus interactifs avec Rich et questionary
"""

import questionary
from rich.console import Console
from rich.panel import Panel
from soc_deploy.core.context import ExecutionContext
from soc_deploy.core.engine import Orchestrator
from soc_deploy.cli.formatters import print_report

console = Console()


class InteractiveDeployMenu:
    def __init__(self, ctx: ExecutionContext, engine: Orchestrator):
        self.ctx = ctx
        self.engine = engine

    async def run(self):
        """Menu principal interactif"""
        console.print(Panel.fit("🚀 SOC Deployment Framework", border_style="green"))
        while True:
            choice = await questionary.select(
                "Que souhaitez-vous faire ?",
                choices=[
                    "1. Déployer un SOC complet",
                    "2. Installer un outil spécifique",
                    "3. Configurer un outil",
                    "4. Sauvegarder un outil",
                    "5. Restaurer un outil",
                    "6. Valider un outil",
                    "7. Vérifier la santé du SOC",
                    "8. Désinstaller un outil",
                    "9. Quitter",
                ],
            ).ask_async()

            if choice.startswith("1"):
                await self._deploy_soc()
            elif choice.startswith("2"):
                await self._install_tool()
            elif choice.startswith("3"):
                await self._configure_tool()
            elif choice.startswith("4"):
                await self._backup_tool()
            elif choice.startswith("5"):
                await self._restore_tool()
            elif choice.startswith("6"):
                await self._validate_tool()
            elif choice.startswith("7"):
                await self._health_check()
            elif choice.startswith("8"):
                await self._uninstall_tool()
            else:
                break

    async def _deploy_soc(self):
        tools = await self._select_tools()
        if not tools:
            return
        console.print(f"Déploiement de {len(tools)} outil(s) : {', '.join(tools)}")
        confirm = await questionary.confirm("Confirmer le déploiement ?").ask_async()
        if confirm:
            report = await self.engine.deploy_soc(tools, interactive=True)
            print_report(report)

    async def run_single_install(self, tool_name: str):
        """Installation d'un seul outil avec options"""
        plugin = self.ctx.plugin_registry.get_plugin(tool_name)
        if not plugin:
            console.print(f"[red]Outil inconnu : {tool_name}[/red]")
            return
        # Récupérer les options de déploiement
        options_schema = await plugin.get_deployment_options(self.ctx)
        # Construire le questionnaire interactif
        user_options = {}
        for key, schema in options_schema.items():
            if schema["type"] == "choice":
                answer = await questionary.select(
                    schema["message"],
                    choices=[c["label"] for c in schema["choices"]],
                ).ask_async()
                # retrouver la valeur réelle
                selected = next(c for c in schema["choices"] if c["label"] == answer)
                user_options[key] = selected["value"]
            elif schema["type"] == "confirm":
                user_options[key] = await questionary.confirm(
                    schema["message"], default=schema.get("default", True)
                ).ask_async()
            elif schema["type"] == "password":
                user_options[key] = await questionary.password(
                    schema["message"]
                ).ask_async()
            else:
                user_options[key] = await questionary.text(
                    schema["message"], default=schema.get("default", "")
                ).ask_async()
        report = await self.engine.install_single_tool(
            tool_name, user_options, interactive=True
        )
        print_report(report)

    async def _select_tools(self) -> list:
        plugins = self.ctx.plugin_registry.list_plugins()
        choices = [questionary.Choice(p.meta.name, value=p.meta.name) for p in plugins]
        if not choices:
            console.print("[red]Aucun plugin disponible[/red]")
            return []
        selected = await questionary.checkbox(
            "Sélectionnez les outils à déployer :",
            choices=choices,
        ).ask_async()
        return selected

    # Autres méthodes (config, backup, etc.) pourraient être implémentées de façon similaire
    async def _configure_tool(self):
        pass  # à implémenter

    async def _backup_tool(self):
        pass

    async def _restore_tool(self):
        pass

    async def _validate_tool(self):
        pass

    async def _health_check(self):
        pass

    async def _uninstall_tool(self):
        pass
