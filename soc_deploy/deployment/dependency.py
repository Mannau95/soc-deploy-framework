"""
Résolveur de dépendances simple
"""

from typing import List, Dict


class DependencyResolver:
    def __init__(self):
        # Dépendances connues (simplifié)
        self._dependencies: Dict[str, List[str]] = {
            "wazuh": ["docker", "postgresql"],
            "misp": ["docker", "mariadb"],
            "thehive": ["cassandra", "elasticsearch"],
            "cortex": ["elasticsearch"],
            "shuffle": ["docker"],
            # ... à compléter dynamiquement via les plugins
        }

    def get_dependencies(self, tool: str) -> List[str]:
        return self._dependencies.get(tool, [])

    def suggest_install_order(self, tools: List[str]) -> List[str]:
        """Ordonnancement topologique basique"""
        # Collecter toutes les dépendances
        all_tools = set(tools)
        for t in tools:
            deps = self.get_dependencies(t)
            all_tools.update(deps)

        # Construction d'un ordre simple : d'abord les dépendances, puis les outils demandés
        order = []
        visited = set()

        def visit(t: str):
            if t in visited:
                return
            visited.add(t)
            for dep in self.get_dependencies(t):
                if dep in all_tools:
                    visit(dep)
            if t in all_tools:  # n'ajouter que ceux qui sont dans l'ensemble
                order.append(t)

        for tool in tools:
            visit(tool)

        return order
