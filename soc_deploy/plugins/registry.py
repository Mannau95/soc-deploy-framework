"""
Registre des plugins
"""

from typing import Dict, List, Optional

from soc_deploy.plugins.base import PluginBase


class PluginRegistry:
    """Stocke et fournit les plugins disponibles"""

    def __init__(self):
        self._plugins: Dict[str, PluginBase] = {}

    def register(self, plugin: PluginBase):
        if plugin.meta.name in self._plugins:
            raise ValueError(f"Plugin déjà enregistré : {plugin.meta.name}")
        self._plugins[plugin.meta.name] = plugin

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        return self._plugins.get(name)

    def list_plugins(self) -> List[PluginBase]:
        return list(self._plugins.values())

    def list_names(self) -> List[str]:
        return list(self._plugins.keys())
