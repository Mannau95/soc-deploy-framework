"""
Validation de Cortex
"""

from typing import Any, Dict


class CortexValidator:
    async def validate(self, ctx) -> Dict[str, Any]:
        # Vérifier que le service tourne
        svc = await ctx.validator.validate_service_running("cortex")
        # Vérifier l'API (par défaut sur le port 9001)
        http = await ctx.validator.validate_http_endpoint(
            "http://localhost:9001", expected_status=200
        )
        success = svc.status.value == "PASSED" and http.status.value == "PASSED"
        return {"success": success, "service": svc.message, "http": http.message}

    async def health_check(self, ctx) -> Dict[str, Any]:
        # Vérification basique de l'état du service
        result = await ctx.executor.execute("systemctl is-active cortex")
        status = "ok" if result.stdout.strip() == "active" else "error"
        return {"status": status, "details": result.stdout}
