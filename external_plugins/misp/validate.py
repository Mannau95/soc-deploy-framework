from typing import Any, Dict


class MispValidator:
    async def validate(self, ctx) -> Dict[str, Any]:
        svc = await ctx.validator.validate_service_running("apache2")
        http = await ctx.validator.validate_http_endpoint(
            "http://localhost", expected_status=200
        )
        success = svc.status.value == "PASSED" and http.status.value == "PASSED"
        return {"success": success, "service": svc.message, "http": http.message}

    async def health_check(self, ctx) -> Dict[str, Any]:
        return {"status": "ok"}
