"""
Configuration de Cortex
"""

from pathlib import Path
from typing import Any, Dict


class CortexConfigurator:
    async def configure(self, ctx, config: Dict[str, Any]) -> Dict[str, Any]:
        # Générer le fichier application.conf via template Jinja2
        template_dir = Path(__file__).parent / "templates"
        admin_password = config.get("admin_password", "admin")

        cortex_conf = ctx.file_manager.render_template(
            "application.conf.j2", {"admin_password": admin_password}, template_dir
        )
        ctx.file_manager.write_file("/etc/cortex/application.conf", cortex_conf)
        # Redémarrer le service
        await ctx.executor.execute("systemctl restart cortex", sudo=True)
        return {"success": True}
