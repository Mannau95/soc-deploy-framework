"""
Configuration de Suricata
"""

from pathlib import Path
from typing import Any, Dict


class SuricataConfigurator:
    async def configure(self, ctx, config: Dict[str, Any]) -> Dict[str, Any]:
        # Modifier /etc/suricata/suricata.yaml via template Jinja2
        template_dir = Path(__file__).parent / "templates"
        suricata_conf = ctx.file_manager.render_template(
            "suricata.yaml.j2",
            {
                "mode": config.get("mode", "ids"),
                "interface": config.get("interface", "eth0"),
                "community_id": config.get("community_id", False),
            },
            template_dir,
        )
        ctx.file_manager.write_file("/etc/suricata/suricata.yaml", suricata_conf)
        # Redémarrer Suricata
        await ctx.executor.execute("systemctl restart suricata", sudo=True)
        return {"success": True}
