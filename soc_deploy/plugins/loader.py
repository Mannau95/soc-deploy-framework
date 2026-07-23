"""
Chargeur dynamique de plugins depuis le répertoire external_plugins/
"""

import importlib
import inspect
import sys
from pathlib import Path

from soc_deploy.plugins.base import PluginBase
from soc_deploy.plugins.registry import PluginRegistry


class PluginLoader:
    @staticmethod
    def discover_and_load(plugin_dir: Path, registry: PluginRegistry):
        """
        Parcourt external_plugins/ et charge chaque dossier contenant un fichier plugin.py
        """
        plugin_dir = Path(plugin_dir)
        if not plugin_dir.exists():
            return

        # Ajouter le répertoire parent au path pour permettre les imports
        sys.path.insert(0, str(plugin_dir.parent))

        for item in plugin_dir.iterdir():
            if item.is_dir() and (item / "plugin.py").exists():
                module_name = f"external_plugins.{item.name}.plugin"
                try:
                    module = importlib.import_module(module_name)
                    # Chercher une classe concrète héritant de PluginBase
                    for _, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, PluginBase) and obj is not PluginBase:
                            plugin_instance = obj()
                            registry.register(plugin_instance)
                            print(f"Plugin chargé : {plugin_instance.meta.name}")
                            break
                except Exception as e:
                    print(f"Erreur lors du chargement du plugin {item.name}: {e}")

        # Nettoyer le path
        sys.path.pop(0)
