"""
Validation de OpenVAS / Greenbone
"""

from typing import Any, Dict


class OpenVASValidator:
    async def validate(self, ctx) -> Dict[str, Any]:
        # Vérifier les services principaux : gvmd, ospd-openvas, gsad
        services = ["gvmd", "ospd-openvas", "gsad"]
        results = {}
        success = True
        for svc in services:
            res = await ctx.validator.validate_service_running(svc)
            results[svc] = res.message
            if res.status.value != "PASSED":
                success = False
        # Vérifier l'interface web (port 9392)
        http = await ctx.validator.validate_http_endpoint(
            "https://localhost:9392", expected_status=200, verify_ssl=False
        )
        if http.status.value != "PASSED":
            success = False
        return {"success": success, "services": results, "web_interface": http.message}

    async def health_check(self, ctx) -> Dict[str, Any]:
        # Vérifier la synchronisation des flux NVT
        result = await ctx.executor.execute(
            "gvm-cli --gmp-username admin --gmp-password admin socket --pretty --xml '<get_feeds/>'"
        )
        return {
            "status": "ok" if result.returncode == 0 else "error",
            "details": result.stdout[:200],
        }
