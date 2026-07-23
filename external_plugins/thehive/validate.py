class TheHiveValidator:
    async def validate(self, ctx):
        svc = await ctx.validator.validate_service_running("thehive")
        http = await ctx.validator.validate_http_endpoint(
            "http://localhost:9000", expected_status=200
        )
        return {
            "success": svc.status.value == "PASSED" and http.status.value == "PASSED",
            "service": svc.message,
        }

    async def health_check(self, ctx):
        return {"status": "ok"}
