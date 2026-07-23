from pathlib import Path
from typing import Any, Dict


class ZeekConfigurator:
    async def configure(self, ctx, config: Dict[str, Any]) -> Dict[str, Any]:
        # Configuration de base : interface, scripts à charger
        template_dir = Path(__file__).parent / "templates"
        node_cfg = ctx.file_manager.render_template(
            "node.cfg.j2", {"interface": config.get("interface", "eth0")}, template_dir
        )
        ctx.file_manager.write_file("/opt/zeek/etc/node.cfg", node_cfg)
        # Déploiement du fichier de configuration de l'interface
        networks_cfg = ctx.file_manager.render_template(
            "networks.cfg.j2", {}, template_dir
        )
        ctx.file_manager.write_file("/opt/zeek/etc/networks.cfg", networks_cfg)
        # Redémarrage via zeekctl
        await ctx.executor.execute("zeekctl deploy", timeout=30)
        return {"success": True}
