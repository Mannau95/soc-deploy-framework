"""
Point d'entrée CLI du framework
"""

import asyncio
from typing import Optional
import typer
from rich.console import Console
from soc_deploy import __version__
from soc_deploy.cli.commands import (
    check_command,
    deploy_command,
    status_command,
    install_command,
    configure_command,
    backup_command,
    restore_command,
    validate_command,
    uninstall_command,
    interactive_command,
)

app = typer.Typer(
    name="soc-deploy",
    help="SOC Deployment Framework - Orchestrateur de déploiement SOC",
    add_completion=False,
)
console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"SOC Deployment Framework v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", callback=version_callback, help="Afficher la version"
    ),
):
    pass


@app.command()
def check():
    """Vérifier les prérequis système"""
    asyncio.run(check_command())


@app.command()
def deploy(
    interactive: bool = typer.Option(True, help="Mode interactif"),
    profile: Optional[str] = typer.Option(None, help="Profil de déploiement"),
):
    """Déployer un SOC complet ou des outils individuels"""
    if interactive:
        asyncio.run(interactive_command())
    else:
        asyncio.run(deploy_command(profile))


@app.command()
def status():
    """Afficher l'état du SOC déployé"""
    asyncio.run(status_command())


@app.command()
def install(
    tool: str = typer.Argument(..., help="Nom de l'outil à installer"),
    interactive: bool = typer.Option(True, help="Mode interactif pour les options"),
):
    """Installer un outil spécifique"""
    asyncio.run(install_command(tool, interactive))


@app.command()
def configure(
    tool: str = typer.Argument(..., help="Nom de l'outil à configurer"),
):
    """Configurer un outil déjà installé"""
    asyncio.run(configure_command(tool))


@app.command()
def backup(
    tool: str = typer.Argument(..., help="Nom de l'outil à sauvegarder"),
):
    """Sauvegarder la configuration d'un outil"""
    asyncio.run(backup_command(tool))


@app.command()
def restore(
    tool: str = typer.Argument(..., help="Nom de l'outil à restaurer"),
    backup_id: str = typer.Option(..., help="Identifiant de la sauvegarde"),
):
    """Restaurer un outil depuis une sauvegarde"""
    asyncio.run(restore_command(tool, backup_id))


@app.command()
def validate(
    tool: Optional[str] = typer.Argument(None, help="Nom de l'outil (tous si vide)"),
):
    """Valider l'installation d'un ou plusieurs outils"""
    asyncio.run(validate_command(tool))


@app.command()
def uninstall(
    tool: str = typer.Argument(..., help="Nom de l'outil à désinstaller"),
):
    """Désinstaller un outil"""
    asyncio.run(uninstall_command(tool))


@app.command()
def interactive():
    """Lancer l'assistant interactif"""
    asyncio.run(interactive_command())


if __name__ == "__main__":
    app()
