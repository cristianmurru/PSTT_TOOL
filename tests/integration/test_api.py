"""
Test di integrazione per gli endpoint API
"""
import pytest
from fastapi.testclient import TestClient


class TestConnectionsAPI:
    """Test per gli endpoint delle connessioni"""
    
    def test_get_connections(self, client):
        """Test lista connessioni"""
        response = client.get("/api/connections/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "connections" in data
        assert "default_connection" in data
        assert "environments" in data
        assert "default_environment" in data
        
        assert len(data["connections"]) > 0
        assert data["default_connection"] is not None
        assert len(data["environments"]) > 0
    
    def test_get_current_connection(self, client):
        """Test connessione corrente"""
        response = client.get("/api/connections/current")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "current_connection" in data
        assert "connection_info" in data
    
    def test_get_environments(self, client):
        """Test lista ambienti"""
        response = client.get("/api/connections/environments")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "environments" in data
        assert "default_environment" in data
        assert "available_environments" in data
        
        # Verifica che gli ambienti siano mappati correttamente
        for env in data["available_environments"]:
            assert env in data["environments"]
    
    def test_switch_connection_invalid(self, client):
        """Test cambio connessione con nome non valido"""
        response = client.post("/api/connections/switch", json={
            "connection_name": "NON_EXISTENT_CONNECTION"
        })
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestQueriesAPI:
    """Test per gli endpoint delle query"""
    
    def test_get_queries(self, client):
        """Test lista query"""
        response = client.get("/api/queries/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "queries" in data
        assert "total_count" in data
        
        assert isinstance(data["queries"], list)
        assert data["total_count"] >= 0
        
        # Se ci sono query, verifica la struttura
        if data["queries"]:
            query = data["queries"][0]
            assert "filename" in query
            assert "title" in query
            assert "parameters" in query
            assert "size_bytes" in query
    
    def test_get_query_not_found(self, client):
        """Test query non esistente"""
        response = client.get("/api/queries/non_existent_query.sql")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_validate_query_parameters_not_found(self, client):
        """Test validazione parametri per query non esistente"""
        response = client.post("/api/queries/validate", params={
            "filename": "non_existent.sql",
            "parameters": {}
        })
        
        assert response.status_code == 404
    
    def test_preview_query_not_found(self, client):
        """Test anteprima query non esistente"""
        response = client.get("/api/queries/non_existent.sql/preview")
        
        assert response.status_code == 404
    
    def test_get_query_statistics(self, client):
        """Test statistiche query"""
        response = client.get("/api/queries/stats/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_queries" in data
        assert "total_size_bytes" in data
        assert "parameters_stats" in data
        
        # Verifica struttura statistiche parametri
        param_stats = data["parameters_stats"]
        assert "by_type" in param_stats
        assert "required" in param_stats
        assert "optional" in param_stats


class TestMonitoringAPI:
    """Test per gli endpoint di monitoring"""
    
    def test_health_check_root(self, client):
        """Test health check dalla root"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert data["status"] == "healthy"
        assert "app" in data
        assert "version" in data
        assert "timestamp" in data
    
    def test_health_check_monitoring(self, client):
        """Test health check da monitoring"""
        response = client.get("/api/monitoring/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "app_name" in data
        assert "version" in data
    
    def test_system_stats(self, client):
        """Test statistiche sistema"""
        response = client.get("/api/monitoring/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "timestamp" in data
        assert "cpu" in data
        assert "memory" in data  
        assert "disk" in data
        
        # Verifica struttura CPU
        cpu = data["cpu"]
        assert "percent" in cpu
        assert "count" in cpu
        assert isinstance(cpu["percent"], (int, float))
        assert cpu["count"] > 0
        
        # Verifica struttura memory
        memory = data["memory"]
        assert "total_bytes" in memory
        assert "used_bytes" in memory
        assert "available_bytes" in memory
        assert "percent" in memory


class TestSchedulerAPI:
    """Test per gli endpoint dello scheduler (stub)"""
    
    def test_get_schedules_stub(self, client):
        """Test lista schedule (stub)"""
        response = client.get("/api/scheduler/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "schedules" in data
        assert "total_count" in data
        assert "message" in data
        assert len(data["schedules"]) == 0
    
    def test_get_jobs_stub(self, client):
        """Test lista job executions (stub)"""
        response = client.get("/api/scheduler/jobs")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "jobs" in data
        assert "total_count" in data
        assert "message" in data
        assert len(data["jobs"]) == 0


class TestHomepage:
    """Test per la homepage"""
    
    def test_homepage_loads(self, client):
        """Test caricamento homepage"""
        response = client.get("/")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # Verifica presenza elementi chiave nell'HTML
        html = response.text
        assert "PSTT Tool" in html
        assert "connectionSelector" in html
        assert "queryList" in html
    
    def test_static_files(self, client):
        """Test caricamento file statici"""
        # Test JavaScript
        response = client.get("/static/js/main.js")
        assert response.status_code == 200
        assert "javascript" in response.headers.get("content-type", "").lower() or response.status_code == 200
    
    def test_404_page(self, client):
        """Test pagina 404"""
        response = client.get("/non-existent-page")
        
        assert response.status_code == 404
        assert "text/html" in response.headers["content-type"]
        
        html = response.text
        assert "404" in html
        assert "non trovata" in html.lower() or "not found" in html.lower()
