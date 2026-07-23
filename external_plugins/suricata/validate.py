"""
Validation de Suricata
"""

from typing import Any, Dict


class SuricataValidator:
    async def validate(self, ctx) -> Dict[str, Any]:
        # Vérifier que le service tourne
        svc = await ctx.validator.validate_service_running("suricata")
        # Vérifier que le socket de stats est accessible
        stats = await ctx.executor.execute("suricatasc -c 'uptime'")
        success = svc.status.value == "PASSED" and stats.status.value == "SUCCESS"
        return {"success": success, "service": svc.message, "stats": stats.stdout}

    async def health_check(self, ctx) -> Dict[str, Any]:
        # Vérification de l'état des règles chargées
        rules_check = await ctx.executor.execute("suricatasc -c 'iface-stat'")
        return {"status": "ok" if rules_check.status.value == "SUCCESS" else "error"}
