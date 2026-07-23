from pathlib import Path


class TheHiveConfigurator:
    async def configure(self, ctx, config):
        template_dir = Path(__file__).parent / "templates"
        conf = ctx.file_manager.render_template(
            "application.conf.j2",
            {
                "cortex_url": config.get("cortex_url", "http://localhost:9001"),
                "admin_password": config.get("admin_password", "admin"),
            },
            template_dir,
        )
        ctx.file_manager.write_file("/etc/thehive/application.conf", conf)
        await ctx.executor.execute("systemctl restart thehive", sudo=True)
        return {"success": True}
