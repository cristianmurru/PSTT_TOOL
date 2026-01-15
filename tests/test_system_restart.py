"""
Test suite per app.api.system - verifica comportamento restart e service management.
Questi test verificano le non-regressioni per il fix del loop di restart.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import subprocess


@pytest.fixture
def mock_service_exists():
    """Mock per simulare servizio Windows esistente."""
    with patch("subprocess.run") as mock_run:
        # Simula Get-Service che trova il servizio
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "True"
        mock_run.return_value = mock_result
        yield mock_run


@pytest.fixture
def mock_service_not_exists():
    """Mock per simulare servizio Windows non esistente."""
    with patch("subprocess.run") as mock_run:
        # Simula Get-Service che NON trova il servizio
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "False"
        mock_run.return_value = mock_result
        yield mock_run


@pytest.fixture
def mock_popen():
    """Mock per subprocess.Popen (evita esecuzione reale PowerShell)."""
    with patch("subprocess.Popen") as mock:
        yield mock


class TestRestartAsService:
    """Test per _restart_as_service() - verifica detection e restart logica."""
    
    def test_restart_as_service_when_service_exists(self, mock_service_exists, mock_popen):
        """Verifica che _restart_as_service restituisca True quando servizio esiste."""
        from app.api.system import _restart_as_service
        
        result = _restart_as_service()
        
        assert result is True
        # Verifica che Popen sia stato chiamato con PowerShell
        assert mock_popen.called
        call_args = mock_popen.call_args[0][0]
        assert "powershell" in call_args[0].lower()
        assert "Stop-Service" in call_args[-1]  # Verifica script PowerShell
        
    def test_restart_as_service_when_service_not_exists(self, mock_service_not_exists, mock_popen):
        """Verifica che _restart_as_service restituisca False quando servizio non esiste."""
        from app.api.system import _restart_as_service
        
        result = _restart_as_service()
        
        assert result is False
        # Popen NON deve essere chiamato se servizio non esiste
        assert not mock_popen.called


class TestRestartEndpoint:
    """Test per endpoint POST /api/system/restart - verifica branching service vs terminal."""
    
    def test_restart_endpoint_service_mode_does_not_call_exit(self, mock_service_exists, mock_popen):
        """
        CRITICAL TEST: Verifica che in modalità service NON venga chiamato _exit_process.
        Questo previene il loop di restart in produzione.
        """
        from app.main import app
        
        client = TestClient(app)
        
        # Mock _exit_process per verificare che NON venga chiamato
        with patch("app.api.system._exit_process") as mock_exit:
            with patch("app.api.system._schedule_terminal_restart") as mock_terminal:
                response = client.post("/api/system/restart")
        
        # Verifica risposta API
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["mode"] == "service"
        
        # VERIFICA CRITICA: _exit_process NON deve essere chiamato in service mode
        assert not mock_exit.called, "_exit_process() called in service mode - this causes restart loop!"
        
        # Terminal restart NON deve essere schedulato in service mode
        assert not mock_terminal.called
    
    def test_restart_endpoint_terminal_mode_calls_exit(self, mock_service_not_exists):
        """Verifica che in modalità terminal vengano chiamati _schedule_terminal_restart e _exit_process."""
        from app.main import app
        
        client = TestClient(app)
        
        # Mock delle funzioni di restart terminale
        with patch("app.api.system._exit_process") as mock_exit:
            with patch("app.api.system._schedule_terminal_restart") as mock_terminal:
                response = client.post("/api/system/restart")
        
        # Verifica risposta API
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["mode"] == "terminal"
        
        # In terminal mode DEVE essere chiamato _schedule_terminal_restart
        assert mock_terminal.called
        mock_terminal.assert_called_once_with(2)
        
        # In terminal mode DEVE essere chiamato _exit_process
        assert mock_exit.called
        mock_exit.assert_called_once_with(1)


class TestServiceStatusEndpoint:
    """Test per endpoint GET /api/system/service/status."""
    
    def test_service_status_when_exists(self):
        """Verifica risposta service/status quando servizio esiste."""
        from app.main import app
        
        client = TestClient(app)
        
        # Mock Get-Service con output JSON valido
        mock_json = '{"Name":"PSTT_Tool","DisplayName":"PSTT Tool","Status":"Running"}'
        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = mock_json
            mock_run.return_value = mock_result
            
            response = client.get("/api/system/service/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is True
        assert data["Name"] == "PSTT_Tool"
        assert data["Status"] == "Running"
    
    def test_service_status_when_not_exists(self):
        """Verifica risposta service/status quando servizio non esiste."""
        from app.main import app
        
        client = TestClient(app)
        
        # Mock Get-Service che non trova servizio
        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_run.return_value = mock_result
            
            response = client.get("/api/system/service/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False


class TestResolveServiceName:
    """Test per _resolve_service_name() - verifica risoluzione nomi servizio."""
    
    def test_resolve_service_name_with_env_override(self):
        """Verifica che variabile ambiente PSTT_SERVICE_NAME abbia precedenza."""
        from app.api.system import _resolve_service_name
        
        with patch.dict("os.environ", {"PSTT_SERVICE_NAME": "CustomServiceName"}):
            result = _resolve_service_name()
        
        assert result == "CustomServiceName"
    
    def test_resolve_service_name_default_underscore(self, mock_service_exists):
        """Verifica risoluzione nome default PSTT_Tool (con underscore)."""
        from app.api.system import _resolve_service_name
        
        with patch.dict("os.environ", {}, clear=True):
            result = _resolve_service_name()
        
        # Dovrebbe restituire il primo candidato trovato
        assert result in ["PSTT_Tool", "PSTT Tool"]


class TestExitProcess:
    """Test per _exit_process() - verifica shutdown graceful."""
    
    def test_exit_process_schedules_timer(self):
        """Verifica che _exit_process crei un Timer per uscita ritardata."""
        from app.api.system import _exit_process
        
        with patch("threading.Timer") as mock_timer:
            mock_timer_instance = Mock()
            mock_timer.return_value = mock_timer_instance
            
            _exit_process(delay_sec=3)
            
            # Verifica che Timer sia stato creato con delay corretto
            mock_timer.assert_called_once()
            args = mock_timer.call_args
            assert args[0][0] == 3  # delay_sec
            
            # Verifica che start() sia stato chiamato
            mock_timer_instance.start.assert_called_once()
            
            # Verifica che daemon sia True
            assert mock_timer_instance.daemon is True


class TestScheduleTerminalRestart:
    """Test per _schedule_terminal_restart() - verifica restart batch mode."""
    
    def test_schedule_terminal_restart_launches_popen(self):
        """Verifica che _schedule_terminal_restart avvii PowerShell con start_pstt.bat."""
        from app.api.system import _schedule_terminal_restart
        
        with patch("subprocess.Popen") as mock_popen:
            _schedule_terminal_restart(delay_sec=5)
            
            # Verifica che Popen sia stato chiamato
            assert mock_popen.called
            call_args = mock_popen.call_args
            
            # Verifica comando PowerShell
            assert call_args[0][0][0] == "powershell"
            assert "-NoProfile" in call_args[0][0]
            assert "Start-Sleep -Seconds 5" in call_args[0][0][-1]
            assert "start_pstt.bat" in call_args[0][0][-1]


class TestIntegrationRestartFlow:
    """Test di integrazione per flusso completo restart."""
    
    def test_restart_flow_service_mode_end_to_end(self, mock_service_exists, mock_popen):
        """
        Test end-to-end: verifica flusso completo restart da UI in service mode.
        Simula: UI click → API call → Native Windows service restart → NO exit process.
        """
        from app.main import app
        
        client = TestClient(app)
        
        with patch("app.api.system._exit_process") as mock_exit:
            # Chiamata API restart (simula click UI)
            response = client.post("/api/system/restart")
            
            # Verifica successo
            assert response.status_code == 200
            assert response.json()["mode"] == "service"
            
            # Verifica che PowerShell restart sia stato invocato
            assert mock_popen.called
            popen_cmd = mock_popen.call_args[0][0]
            assert "powershell" in popen_cmd[0].lower()
            assert "Stop-Service" in popen_cmd[-1]
            
            # VERIFICA CRITICA: NO exit process in service mode
            assert not mock_exit.called
    
    def test_restart_flow_terminal_mode_end_to_end(self, mock_service_not_exists):
        """
        Test end-to-end: verifica flusso completo restart da terminale.
        Simula: Terminal → API call → Schedule batch → Exit process.
        """
        from app.main import app
        
        client = TestClient(app)
        
        with patch("app.api.system._exit_process") as mock_exit:
            with patch("app.api.system._schedule_terminal_restart") as mock_terminal:
                # Chiamata API restart (terminale)
                response = client.post("/api/system/restart")
                
                # Verifica successo
                assert response.status_code == 200
                assert response.json()["mode"] == "terminal"
                
                # Verifica terminal restart schedulato
                assert mock_terminal.called
                
                # Verifica exit process chiamato
                assert mock_exit.called


class TestNSSMConfiguration:
    """Test per verificare configurazione NSSM corretta (via install_service.ps1)."""
    
    def test_install_service_script_uses_exit_not_restart(self):
        """
        Verifica che install_service.ps1 configuri AppExit Default Exit.
        Questo previene loop di restart su exit code 0.
        """
        from pathlib import Path
        
        script_path = Path(__file__).resolve().parents[1] / "install_service.ps1"
        assert script_path.exists(), "install_service.ps1 not found"
        
        content = script_path.read_text(encoding="utf-8")
        
        # Verifica che NON usi più "AppExit Default Restart"
        assert "AppExit Default Restart" not in content, \
            "install_service.ps1 should NOT use 'AppExit Default Restart' - causes restart loop!"
        
        # Verifica che usi "AppExit Default Exit"
        assert "AppExit Default Exit" in content, \
            "install_service.ps1 should use 'AppExit Default Exit' to prevent restart on exit 0"


# Test di regressione specifici per il bug fix
class TestRegressionRestartLoop:
    """Test di regressione per verificare che il loop di restart sia risolto."""
    
    def test_no_exit_process_in_service_mode_regression(self, mock_service_exists, mock_popen):
        """
        REGRESSION TEST: Verifica che il bug del loop infinito sia risolto.
        
        Bug originale:
        1. UI chiama /api/system/restart
        2. API avvia NSSM restart in background
        3. API chiama os._exit(0)
        4. NSSM vede exit e con AppExit Default Restart lo riavvia
        5. Loop infinito
        
        Fix:
        - API NON chiama _exit_process() in service mode
        - NSSM usa AppExit Default Exit (no restart su exit 0)
        """
        from app.main import app
        
        client = TestClient(app)
        
        # Contatore per simulare loop detection
        exit_process_calls = []
        
        def mock_exit_tracker(delay_sec):
            exit_process_calls.append(delay_sec)
        
        with patch("app.api.system._exit_process", side_effect=mock_exit_tracker):
            # Chiamata API restart multipla (simula loop)
            for _ in range(3):
                response = client.post("/api/system/restart")
                assert response.status_code == 200
        
        # VERIFICA: _exit_process NON deve essere chiamato nemmeno una volta
        assert len(exit_process_calls) == 0, \
            f"_exit_process called {len(exit_process_calls)} times in service mode - restart loop detected!"
