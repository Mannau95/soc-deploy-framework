"""
Validation de Shuffle
"""

from typing import Any, Dict


class ShuffleValidator:
    async def validate(self, ctx) -> Dict[str, Any]:
        # Vérifier que les conteneurs Docker tournent
        backend = await ctx.validator.validate_docker_container("shuffle-backend")
        frontend = await ctx.validator.validate_docker_container("shuffle-frontend")
        # Vérifier l'API backend (port 5001)
        http = await ctx.validator.validate_http_endpoint(
            "http://localhost:5001/api/v1/health", expected_status=200
        )
        success = (
            backend.status.value == "PASSED"
            and frontend.status.value == "PASSED"
            and http.status.value == "PASSED"
        )
        return {
            "success": success,
            "backend": backend.message,
            "frontend": frontend.message,
            "http": http.message,
        }

    async def health_check(self, ctx) -> Dict[str, Any]:
        # Vérifier l'état des conteneurs
        backend = await ctx.docker_manager.get_container_status("shuffle-backend")
        frontend = await ctx.docker_manager.get_container_status("shuffle-frontend")
        status = (
            "ok"
            if backend.value == "running" and frontend.value == "running"
            else "error"
        )
        return {"status": status, "backend": backend.value, "frontend": frontend.value}
