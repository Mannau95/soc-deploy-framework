"""
Initialisation du contexte avec tous les services et plugins
"""

from pathlib import Path

from soc_deploy.core.context import ExecutionContext
from soc_deploy.database.manager import DatabaseManager
from soc_deploy.models.config import FrameworkConfig
from soc_deploy.plugins.loader import PluginLoader
from soc_deploy.plugins.registry import PluginRegistry
from soc_deploy.services.backup import BackupManager
from soc_deploy.services.docker import DockerManager
from soc_deploy.services.executor import CommandExecutor
from soc_deploy.services.file import FileManager
from soc_deploy.services.package import PackageManager
from soc_deploy.services.system import SystemChecker
from soc_deploy.services.validator import ValidatorService
from soc_deploy.utils.logger import LoggerManager


async def create_context(config: FrameworkConfig = None) -> ExecutionContext:
    """Crée le contexte d'exécution (asynchrone)."""
    if not config:
        config = FrameworkConfig()

    log_dir = Path(config.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = LoggerManager(log_dir, log_level=config.log_level)

    executor = CommandExecutor(logger)
    system_checker = SystemChecker()
    package_manager = PackageManager(executor)
    docker_manager = DockerManager(executor)
    file_manager = FileManager()
    backup_manager = BackupManager(Path(config.backup_dir), logger)
    validator = ValidatorService(executor, logger)

    db_path = Path(__file__).parent / "database" / "state.db"
    db = DatabaseManager(db_path, logger)

    # Initialisation asynchrone de la base de données
    await db.initialize()

    registry = PluginRegistry()
    # Charger les plugins depuis external_plugins/
    plugin_dir = Path(__file__).parent.parent / "external_plugins"
    PluginLoader.discover_and_load(plugin_dir, registry)

    system_info = system_checker.get_system_info()

    ctx = ExecutionContext(
        config=config,
        system_info=system_info,
        logger=logger,
        db=db,
        executor=executor,
        system_checker=system_checker,
        package_manager=package_manager,
        docker_manager=docker_manager,
        file_manager=file_manager,
        backup_manager=backup_manager,
        validator=validator,
        plugin_registry=registry,
    )
    return ctx