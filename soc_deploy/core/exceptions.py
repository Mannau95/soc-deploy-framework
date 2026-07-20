"""
Exceptions personnalisées du framework
"""


class SOCDeployError(Exception):
    """Exception de base pour le framework"""

    pass


class PrerequisitesError(SOCDeployError):
    """Erreur de prérequis"""

    pass


class InstallationError(SOCDeployError):
    """Erreur d'installation"""

    pass


class ConfigurationError(SOCDeployError):
    """Erreur de configuration"""

    pass


class ValidationError(SOCDeployError):
    """Erreur de validation"""

    pass


class BackupError(SOCDeployError):
    """Erreur de sauvegarde"""

    pass


class RestoreError(SOCDeployError):
    """Erreur de restauration"""

    pass


class RollbackError(SOCDeployError):
    """Erreur de rollback"""

    pass


class StateError(SOCDeployError):
    """Erreur de gestion d'état"""

    pass


class PluginError(SOCDeployError):
    """Erreur de plugin"""

    pass


class DependencyError(SOCDeployError):
    """Erreur de dépendance"""

    pass
