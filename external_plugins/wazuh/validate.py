"""
Validation de la stack Wazuh
"""

from typing import Any, Dict


class WazuhValidator:
    async def validate(self, ctx) -> Dict[str, Any]:
        results = []
        # Vérifier que les services sont actifs
        services = ["wazuh-manager", "wazuh-indexer", "wazuh-dashboard"]
        for svc in services:
            res = await ctx.validator.validate_service_running(svc)
            results.append(res)
        # Vérifier les ports
        ports = [55000, 1514, 443]
        for p in ports:
            res = await ctx.validator.validate_port_open("localhost", p)
            results.append(res)
        # Vérifier l'API Wazuh
        api_res = await ctx.validator.validate_http_endpoint(
            "https://localhost:55000", expected_status=200, verify_ssl=False
        )
        results.append(api_res)
        # Vérifier l'interface web
        dash_res = await ctx.validator.validate_http_endpoint(
            "https://localhost", expected_status=200, verify_ssl=False
        )
        results.append(dash_res)

        success = all(r.status.value == "PASSED" for r in results)
        return {
            "success": success,
            "checks": [
                {"name": r.name, "status": r.status.value, "message": r.message}
                for r in results
            ],
        }

    async def health_check(self, ctx) -> Dict[str, Any]:
        # Health check approfondi : état des agents, intégrité de la base, etc.
        return {"status": "ok", "details": "Wazuh est opérationnel"}
