import questionary
from rich.console import Console
from rich.panel import Panel

from soc_deploy.cli.formatters import print_report
from soc_deploy.core.context import ExecutionContext
from soc_deploy.core.engine import Orchestrator
from soc_deploy.core.state import StateManager

console = Console()


class InteractiveDeployMenu:
    def __init__(self, ctx: ExecutionContext, engine: Orchestrator):
        self.ctx = ctx
        self.engine = engine
        self.state = StateManager(ctx.db, ctx.logger)

    async def run(self):
        console.print(Panel.fit("🚀 SOC Deployment Framework", border_style="green"))
        # Mapping des préfixes de choix vers les méthodes
        choice_map = {
            "1": self._deploy_soc,
            "2": self._install_tool,
            "3": self._configure_tool,
            "4": self._backup_tool,
            "5": self._restore_tool,
            "6": self._validate_tool,
            "7": self._health_check,
            "8": self._uninstall_tool,
            "9": self._resume_deployment,
        }
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
                    "9. Reprendre un déploiement suspendu",
                    "10. Quitter",
                ],
            ).ask_async()

            # Extraire le numéro (avant le point ou l'espace)
            key = choice.split(".")[0] if "." in choice else choice.split()[0]
            if key == "10":
                break
            action = choice_map.get(key)
            if action:
                await action()
            else:
                break

    # Les autres méthodes restent strictement identiques
    async def _deploy_soc(self):
        tools = await self._select_tools()
        if not tools:
            return
        console.print(f"Déploiement de {len(tools)} outil(s) : {', '.join(tools)}")
        confirm = await questionary.confirm("Confirmer le déploiement ?").ask_async()
        if confirm:
            report = await self.engine.deploy_soc(tools, interactive=True)
            print_report(report)

    async def _install_tool(self):
        plugins = self.ctx.plugin_registry.list_plugins()
        choices = [p.meta.name for p in plugins]
        if not choices:
            console.print("[red]Aucun plugin disponible[/red]")
            return
        tool = await questionary.select(
            "Choisissez un outil à installer :", choices=choices
        ).ask_async()
        if tool:
            await self.run_single_install(tool)

    async def run_single_install(self, tool_name: str):
        plugin = self.ctx.plugin_registry.get_plugin(tool_name)
        if not plugin:
            console.print(f"[red]Outil inconnu : {tool_name}[/red]")
            return
        options_schema = await plugin.get_deployment_options(self.ctx)
        user_options = {}
        for key, schema in options_schema.items():
            if schema["type"] == "choice":
                answer = await questionary.select(
                    schema["message"],
                    choices=[c["label"] for c in schema["choices"]],
                ).ask_async()
                selected = next(c for c in schema["choices"] if c["label"] == answer)
                user_options[key] = selected["value"]
            elif schema["type"] == "confirm":
                user_options[key] = await questionary.confirm(
                    schema["message"], default=schema.get("default", True)
                ).ask_async()
            elif schema["type"] == "password":
                user_options[key] = await questionary.password(schema["message"]).ask_async()
            else:
                user_options[key] = await questionary.text(
                    schema["message"], default=schema.get("default", "")
                ).ask_async()
        report = await self.engine.install_single_tool(tool_name, user_options, interactive=True)
        print_report(report)

    async def _select_tools(self) -> list:
        plugins = self.ctx.plugin_registry.list_plugins()
        choices = [questionary.Choice(p.meta.name, value=p.meta.name) for p in plugins]
        if not choices:
            console.print("[red]Aucun plugin disponible[/red]")
            return []
        selected = await questionary.checkbox(
            "Sélectionnez les outils à déployer :", choices=choices
        ).ask_async()
        return selected

    async def _configure_tool(self):
        tool = await self._pick_installed_tool()
        if not tool:
            return
        plugin = self.ctx.plugin_registry.get_plugin(tool)
        config = {}  # pour simplifier, on pourrait poser des questions dynamiques
        result = await plugin.configure(self.ctx, config)
        if result.get("success"):
            console.print(f"[green]{tool} configuré avec succès[/green]")
        else:
            console.print(f"[red]Échec configuration : {result.get('error')}[/red]")

    async def _backup_tool(self):
        tool = await self._pick_installed_tool()
        if not tool:
            return
        plugin = self.ctx.plugin_registry.get_plugin(tool)
        result = await plugin.backup(self.ctx)
        if result.get("success"):
            console.print(f"[green]Sauvegarde créée : {result.get('backup_id')}[/green]")
        else:
            console.print("[red]Échec sauvegarde[/red]")

    async def _restore_tool(self):
        tool = await self._pick_installed_tool()
        if not tool:
            return
        plugin = self.ctx.plugin_registry.get_plugin(tool)
        backups = self.ctx.backup_manager.list_backups(tool)
        if not backups:
            console.print("[yellow]Aucune sauvegarde disponible[/yellow]")
            return
        choices = [f"{b.id} ({b.created_at})" for b in backups]
        choice = await questionary.select(
            "Choisissez une sauvegarde :", choices=choices
        ).ask_async()
        backup_id = choice.split()[0]
        result = await plugin.restore(self.ctx, {"backup_id": backup_id})
        if result.get("success"):
            console.print("[green]Restauration réussie[/green]")
        else:
            console.print(f"[red]Échec : {result.get('error')}[/red]")

    async def _validate_tool(self):
        tool = await self._pick_installed_tool()
        if not tool:
            return
        plugin = self.ctx.plugin_registry.get_plugin(tool)
        result = await plugin.validate(self.ctx)
        if result.get("success"):
            console.print(f"[green]Validation réussie pour {tool}[/green]")
        else:
            console.print(f"[red]Échec validation : {result.get('error', '')}[/red]")

    async def _health_check(self):
        console.print("Vérification de santé de tous les outils...")
        for plugin in self.ctx.plugin_registry.list_plugins():
            try:
                hc = await plugin.health_check(self.ctx)
                console.print(f"{plugin.meta.name}: {hc.get('status', 'inconnu')}")
            except Exception as e:
                console.print(f"{plugin.meta.name}: erreur - {e}")

    async def _uninstall_tool(self):
        tool = await self._pick_installed_tool()
        if not tool:
            return
        plugin = self.ctx.plugin_registry.get_plugin(tool)
        confirm = await questionary.confirm(
            f"Êtes-vous sûr de vouloir désinstaller {tool} ?"
        ).ask_async()
        if confirm:
            result = await plugin.uninstall(self.ctx)
            if result.get("success"):
                console.print(f"[green]{tool} désinstallé[/green]")
            else:
                console.print("[red]Échec désinstallation[/red]")

    async def _resume_deployment(self):
        deployments = await self.state.list_active_deployments()
        paused = [d for d in deployments if d["status"] == "PAUSED"]
        if not paused:
            console.print("[yellow]Aucun déploiement suspendu[/yellow]")
            return
        choices = [f"{d['id']} - {d['name']}" for d in paused]
        choice = await questionary.select(
            "Choisissez un déploiement à reprendre :", choices=choices
        ).ask_async()
        dep_id = choice.split()[0]
        report = await self.engine.resume_deployment(dep_id)
        print_report(report)

    async def _pick_installed_tool(self):
        # Récupérer la liste des outils installés depuis un déploiement actif ou dernier complété
        deployments = await self.state.list_active_deployments()
        if not deployments:
            deployments = await self.state.db.list_deployments()
        if not deployments:
            console.print("[red]Aucun déploiement trouvé[/red]")
            return None
        last = deployments[0]
        tools = await self.state.get_deployment_tools(last["id"])
        installed = [t["tool_name"] for t in tools if t["status"] == "COMPLETED"]
        if not installed:
            console.print("[yellow]Aucun outil installé trouvé[/yellow]")
            return None
        return await questionary.select("Choisissez un outil :", choices=installed).ask_async()
