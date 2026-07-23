"""
Tests d'intégration : vérifications système
"""

import pytest
from soc_deploy.services.system import CheckStatus


@pytest.mark.asyncio
async def test_run_all_checks(ctx):
    """Vérifie que toutes les vérifications système s'exécutent sans erreur"""
    checks = ctx.system_checker.run_all_checks()
    assert len(checks) > 0
    # Aucune vérification ne doit lever d'exception
    for check in checks:
        assert check.status in CheckStatus


@pytest.mark.asyncio
async def test_system_info_structure(ctx):
    """Vérifie que les informations système sont bien remplies"""
    info = ctx.system_checker.get_system_info()
    assert info.distro != ""
    assert info.arch != ""
    assert info.cpu_count > 0
    assert info.ram_gb > 0


@pytest.mark.asyncio
async def test_report_formatting(ctx):
    """Le formatage du rapport ne doit pas planter"""
    checks = ctx.system_checker.run_all_checks()
    report = ctx.system_checker.format_report(checks)
    assert "RAPPORT DE VÉRIFICATION SYSTÈME" in report
    assert "Résumé" in report
