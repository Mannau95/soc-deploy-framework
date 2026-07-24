"""
Implémentations des commandes CLI, utilisant le moteur
"""

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from soc_deploy.cli.formatters import print_report
from soc_deploy.cli.menus import InteractiveDeployMenu
from soc_deploy.core.context import ExecutionContext
from soc_deploy.core.engine import Orchestrator
from soc_deploy.core.state import StateManager

console = Console()


async def _get_context() -> ExecutionContext:
    # Importer la factory qui construit le contexte avec tous les services
    from soc_deploy.bootstrap import create_context

    return await create_context()


async def check_command():
    ctx = await _get_context()
    console.print(Panel.fit("🔍 Vérification des prérequis système", border_style="blue"))
    checks = ctx.system_checker.run_all_checks()
    report = ctx.system_checker.format_report(checks)
    console.print(report)


async def deploy_command(profile=None):
    ctx = await _get_context()
    state = StateManager(ctx.db, ctx.logger)
    engine = Orchestrator(ctx, state)

    # Déploiement non interactif (à partir d'un profil)
    if profile:
        # Charger la liste d'outils depuis le profil
        from soc_deploy.config.profiles import load_profile

        profile_data = load_profile(profile)
        tools = profile_data.get("tools", [])
        console.print(f"Déploiement du profil '{profile}' avec {len(tools)} outils...")
        report = await engine.deploy_soc(tools, profile=profile, interactive=False)
        print_report(report)
    else:
        console.print("[red]Un profil doit être spécifié en mode non-interactif[/red]")


async def status_command():
    ctx = await _get_context()
    state = StateManager(ctx.db, ctx.logger)
    deployments = await state.list_active_deployments()
    if not deployments:
        console.print("[yellow]Aucun déploiement actif[/yellow]")
        return
    table = Table(title="Déploiements actifs")
    table.add_column("ID", style="cyan")
    table.add_column("Nom", style="green")
    table.add_column("Statut", style="yellow")
    for dep in deployments:
        table.add_row(dep["id"], dep["name"], dep["status"])
    console.print(table)


async def install_command(tool: str, interactive: bool):
    ctx = await _get_context()
    state = StateManager(ctx.db, ctx.logger)
    engine = Orchestrator(ctx, state)

    if interactive:
        menu = InteractiveDeployMenu(ctx, engine)
        await menu.run_single_install(tool)
    else:
        report = await engine.install_single_tool(tool, {}, interactive=False)
        print_report(report)


async def configure_command(tool: str):
    ctx = await _get_context()
    plugin = ctx.plugin_registry.get_plugin(tool)
    if not plugin:
        console.print(f"[red]Plugin introuvable : {tool}[/red]")
        return
    config = {}  # On pourrait demander interactivement
    result = await plugin.configure(ctx, config)
    if result.get("success"):
        console.print(f"[green]{tool} configuré avec succès[/green]")
    else:
        console.print(f"[red]Échec configuration : {result.get('error')}[/red]")


async def backup_command(tool: str):
    ctx = await _get_context()
    plugin = ctx.plugin_registry.get_plugin(tool)
    if not plugin:
        console.print(f"[red]Plugin introuvable : {tool}[/red]")
        return
    result = await plugin.backup(ctx)
    if result.get("success"):
        console.print(f"[green]Sauvegarde créée : {result.get('backup_id')}[/green]")
    else:
        console.print("[red]Échec sauvegarde[/red]")


async def restore_command(tool: str, backup_id: str):
    ctx = await _get_context()
    plugin = ctx.plugin_registry.get_plugin(tool)
    if not plugin:
        console.print(f"[red]Plugin introuvable : {tool}[/red]")
        return
    result = await plugin.restore(ctx, {"backup_id": backup_id})
    if result.get("success"):
        console.print("[green]Restauration réussie[/green]")
    else:
        console.print(f"[red]Échec restauration : {result.get('error')}[/red]")


async def validate_command(tool: Optional[str] = None):
    ctx = await _get_context()
    if tool:
        plugin = ctx.plugin_registry.get_plugin(tool)
        if not plugin:
            console.print(f"[red]Plugin {tool} introuvable[/red]")
            return
        result = await plugin.validate(ctx)
        if result.get("success"):
            console.print(f"[green]Validation réussie pour {tool}[/green]")
        else:
            console.print(f"[red]Validation échouée : {result.get('error')}[/red]")
            # Afficher les détails
    else:
        console.print("[yellow]Validation de tous les outils non implémentée[/yellow]")


async def uninstall_command(tool: str):
    ctx = await _get_context()
    plugin = ctx.plugin_registry.get_plugin(tool)
    if not plugin:
        console.print(f"[red]Plugin {tool} introuvable[/red]")
        return
    confirm = input(f"Êtes-vous sûr de vouloir désinstaller {tool} ? (oui/non) ").lower()
    if confirm != "oui":
        console.print("Annulé")
        return
    result = await plugin.uninstall(ctx)
    if result.get("success"):
        console.print(f"[green]{tool} désinstallé[/green]")
    else:
        console.print("[red]Échec désinstallation[/red]")


async def interactive_command():
    ctx = await _get_context()
    state = StateManager(ctx.db, ctx.logger)
    engine = Orchestrator(ctx, state)
    menu = InteractiveDeployMenu(ctx, engine)
    await menu.run()
