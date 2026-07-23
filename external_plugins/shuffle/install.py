from pathlib import Path


class ShuffleInstaller:
    async def check_prerequisites(self, ctx):
        issues = []
        if not await ctx.executor.check_command_exists("docker"):
            issues.append("Docker requis")
        return {"success": len(issues) == 0, "issues": issues}

    async def install(self, ctx, options):
        # Shuffle s'installe principalement via Docker
        await ctx.docker_manager.pull_image("ghcr.io/shuffle/shuffle-backend", "latest")
        await ctx.docker_manager.pull_image(
            "ghcr.io/shuffle/shuffle-frontend", "latest"
        )
        # Créer un fichier docker-compose
        compose = {
            "version": "3.8",
            "services": {
                "shuffle-backend": {
                    "image": "ghcr.io/shuffle/shuffle-backend:latest",
                    "ports": ["5001:5001"],
                    "environment": {
                        "SHUFFLE_APP_SDK_TIMEOUT": "300",
                    },
                },
                "shuffle-frontend": {
                    "image": "ghcr.io/shuffle/shuffle-frontend:latest",
                    "ports": ["3000:3000", "3443:3443"],
                    "environment": {
                        "BACKEND_HOSTNAME": "shuffle-backend",
                    },
                },
            },
        }

        compose_file = "/tmp/shuffle-compose.yml"
        ctx.file_manager.write_yaml(compose_file, compose)
        await ctx.docker_manager.compose_up(Path(compose_file), detach=True)
        return {"success": True}

    async def uninstall(self, ctx):
        compose_file = Path("/tmp/shuffle-compose.yml")
        await ctx.docker_manager.compose_down(compose_file)
        return {"success": True}

    async def update(self, ctx):
        return {"success": True}
