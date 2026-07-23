from typing import Any, Dict


class ZeekValidator:
    async def validate(self, ctx) -> Dict[str, Any]:
        # Vérifier que zeek tourne (via zeekctl status)
        result = await ctx.executor.execute("zeekctl status", timeout=10)
        success = "running" in result.stdout
        return {"success": success, "details": result.stdout}

    async def health_check(self, ctx) -> Dict[str, Any]:
        result = await ctx.executor.execute("zeekctl check", timeout=10)
        return {
            "status": "ok" if result.returncode == 0 else "error",
            "details": result.stdout,
        }
