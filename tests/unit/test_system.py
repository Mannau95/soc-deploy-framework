"""
Tests du service de vérification système
"""
import pytest
from unittest.mock import patch, MagicMock
from soc_deploy.services.system import SystemChecker, CheckStatus


class TestSystemChecker:
    """Tests du vérificateur système"""

    @pytest.fixture
    def checker(self):
        return SystemChecker()

    def test_get_system_info(self, checker):
        """Test la récupération des informations système"""
        info = checker.get_system_info()
        assert info.arch in ["x86_64", "aarch64"]
        assert info.cpu_count > 0
        assert info.ram_gb > 0

    @patch("os.cpu_count")
    def test_check_cpu_ok(self, mock_cpu, checker):
        """Test la vérification CPU OK"""
        mock_cpu.return_value = 8
        result = checker.check_cpu()
        assert result.status == CheckStatus.OK
        assert "8 cœurs" in result.message

    @patch("os.cpu_count")
    def test_check_cpu_warning(self, mock_cpu, checker):
        """Test la vérification CPU avertissement"""
        mock_cpu.return_value = 2
        result = checker.check_cpu()
        assert result.status == CheckStatus.WARNING

    @patch("os.cpu_count")
    def test_check_cpu_error(self, mock_cpu, checker):
        """Test la vérification CPU erreur"""
        mock_cpu.return_value = 1
        result = checker.check_cpu()
        assert result.status == CheckStatus.ERROR

    @patch.object(SystemChecker, "_get_ram_gb")
    def test_check_ram_ok(self, mock_ram, checker):
        """Test la vérification RAM OK"""
        mock_ram.return_value = 32.0
        result = checker.check_ram()
        assert result.status == CheckStatus.OK

    @patch.object(SystemChecker, "_get_ram_gb")
    def test_check_ram_error(self, mock_ram, checker):
        """Test la vérification RAM erreur"""
        mock_ram.return_value = 4.0
        result = checker.check_ram()
        assert result.status == CheckStatus.ERROR

    @patch.object(SystemChecker, "_check_internet")
    def test_check_internet_ok(self, mock_internet, checker):
        """Test la vérification Internet OK"""
        mock_internet.return_value = True
        result = checker.check_internet()
        assert result.status == CheckStatus.OK

    @patch.object(SystemChecker, "_check_internet")
    def test_check_internet_error(self, mock_internet, checker):
        """Test la vérification Internet erreur"""
        mock_internet.return_value = False
        result = checker.check_internet()
        assert result.status == CheckStatus.ERROR

    def test_run_all_checks(self, checker):
        """Test l'exécution de toutes les vérifications"""
        checks = checker.run_all_checks()
        assert len(checks) >= 10
        # Vérifier que toutes les vérifications essentielles sont présentes
        check_names = [c.name for c in checks]
        assert "Distribution" in check_names
        assert "Architecture" in check_names
        assert "CPU" in check_names
        assert "Mémoire RAM" in check_names

    def test_format_report(self, checker):
        """Test le formatage du rapport"""
        checks = [
            checker.check_cpu(),
            checker.check_ram(),
        ]
        report = checker.format_report(checks)
        assert "RAPPORT DE VÉRIFICATION SYSTÈME" in report
        assert "Résumé" in report