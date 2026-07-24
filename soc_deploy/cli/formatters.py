from rich.console import Console
from rich.table import Table

from soc_deploy.models.report import DeploymentReport, ToolReport

console = Console()


def print_report(report):
    """Affiche un rapport de déploiement ou d'outil unique."""
    if isinstance(report, ToolReport):
        _print_tool_report(report)
    elif isinstance(report, DeploymentReport):
        _print_deployment_report(report)
    else:
        console.print("[red]Type de rapport inconnu[/red]")


def _print_tool_report(report: ToolReport):
    """Affiche le résultat de l'installation d'un seul outil."""
    if report.status == "success":
        console.print(f"[green]✅ {report.tool_name} installé avec succès[/green]")
    else:
        console.print(f"[red]❌ {report.tool_name} a échoué : {report.error}[/red]")


def _print_deployment_report(report: DeploymentReport):
    """Affiche un rapport de déploiement complet."""
    if not report.tools:
        console.print("[yellow]Aucun outil déployé[/yellow]")
        return

    table = Table(title=f"Déploiement {report.deployment_id} - Statut : {report.status}")
    table.add_column("Outil", style="cyan")
    table.add_column("Statut", style="green")
    table.add_column("Détails", style="white")

    for tool in report.tools:
        status_icon = "✅" if tool.status == "success" else "❌"
        table.add_row(tool.tool_name, status_icon, tool.error or "OK")
    console.print(table)
