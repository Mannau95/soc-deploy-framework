from rich.console import Console
from rich.table import Table

from soc_deploy.models.report import DeploymentReport

console = Console()


def print_report(report: DeploymentReport):
    """Affiche un rapport de déploiement formaté avec Rich"""
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
