"""
Test unitari per il modulo di configurazione
"""
import pytest
from pathlib import Path
from app.core.config import (
    get_settings, 
    get_connections_config,
    get_env_vars,
    DatabaseConfig,
    ConnectionsConfig
)


class TestSettings:
    """Test per le configurazioni dell'applicazione"""
    
    def test_get_settings(self):
        """Test caricamento configurazioni di base"""
        settings = get_settings()
        
        assert settings.app_name == "PSTT Tool"
        assert settings.app_version == "1.0.0"
        assert settings.host == "127.0.0.1"
        assert settings.port == 8000
        assert isinstance(settings.base_dir, Path)
        assert settings.query_dir.name == "Query"
        assert settings.export_dir.name == "exports"
        assert settings.log_dir.name == "logs"
    
    def test_settings_paths_exist(self):
        """Test che i path di configurazione esistano"""
        settings = get_settings()
        
        # Il base_dir dovrebbe sempre esistere
        assert settings.base_dir.exists()
        
        # connections.json dovrebbe esistere
        assert settings.connections_file.exists()
        
        # Query directory dovrebbe esistere  
        assert settings.query_dir.exists()


class TestConnectionsConfig:
    """Test per la configurazione delle connessioni database"""
    
    def test_get_connections_config(self):
        """Test caricamento configurazioni connessioni"""
        config = get_connections_config()
        
        assert isinstance(config, ConnectionsConfig)
        assert config.default_environment in config.environments
        assert len(config.connections) > 0
        assert config.default_connection is not None
    
    def test_connections_structure(self):
        """Test struttura delle connessioni"""
        config = get_connections_config()
        
        for conn in config.connections:
            assert isinstance(conn, DatabaseConfig)
            assert conn.name
            assert conn.environment in config.environments
            assert conn.db_type in ["oracle", "postgresql", "sqlserver"]
            assert isinstance(conn.params, dict)
            assert "host" in conn.params
            assert "port" in conn.params
    
    def test_get_connection_by_name(self):
        """Test ricerca connessione per nome"""
        config = get_connections_config()
        
        # Test con connessione esistente
        first_conn = config.connections[0]
        found = config.get_connection_by_name(first_conn.name)
        assert found is not None
        assert found.name == first_conn.name
        
        # Test con connessione inesistente
        not_found = config.get_connection_by_name("NON_EXISTENT")
        assert not_found is None
    
    def test_get_connections_by_environment(self):
        """Test ricerca connessioni per ambiente"""
        config = get_connections_config()
        
        # Test con ambiente esistente
        env = config.environments[0]
        connections = config.get_connections_by_environment(env)
        assert len(connections) > 0
        
        for conn in connections:
            assert conn.environment == env
        
        # Test con ambiente inesistente
        empty = config.get_connections_by_environment("NON_EXISTENT")
        assert len(empty) == 0


class TestDatabaseConfig:
    """Test per la configurazione database"""
    
    def test_oracle_connection_string(self):
        """Test generazione connection string Oracle"""
        config = DatabaseConfig(
            name="test",
            environment="test", 
            db_type="oracle",
            description="Test",
            params={
                "host": "localhost",
                "port": 1521,
                "service_name": "testdb",
                "username": "testuser",
                "password": "testpass"
            }
        )
        
        env_vars = {
            "DB_USER_TEST": "testuser",
            "DB_PASS_TEST": "testpass"
        }
        
        conn_str = config.get_connection_string(env_vars)
        
        assert "oracle+oracledb://" in conn_str
        assert "testuser:testpass" in conn_str
        assert "localhost:1521" in conn_str
        assert "/testdb" in conn_str
    
    def test_postgresql_connection_string(self):
        """Test generazione connection string PostgreSQL"""
        config = DatabaseConfig(
            name="test",
            environment="test",
            db_type="postgresql", 
            description="Test",
            params={
                "host": "localhost",
                "port": 5432,
                "service_name": "testdb",
                "username": "testuser",
                "password": "testpass"
            }
        )
        
        env_vars = {}
        conn_str = config.get_connection_string(env_vars)
        
        assert "postgresql+psycopg2://" in conn_str
        assert "localhost:5432" in conn_str
        assert "/testdb" in conn_str
    
    def test_sqlserver_connection_string(self):
        """Test generazione connection string SQL Server"""
        config = DatabaseConfig(
            name="test",
            environment="test",
            db_type="sqlserver",
            description="Test", 
            params={
                "host": "localhost",
                "port": 1433,
                "service_name": "testdb",
                "username": "testuser",
                "password": "testpass"
            }
        )
        
        env_vars = {}
        conn_str = config.get_connection_string(env_vars)
        
        assert "mssql+pyodbc://" in conn_str
        assert "localhost:1433" in conn_str
        assert "/testdb" in conn_str
        assert "ODBC+Driver" in conn_str


class TestEnvVars:
    """Test per la gestione delle variabili d'ambiente"""
    
    def test_get_env_vars(self):
        """Test caricamento variabili d'ambiente"""
        env_vars = get_env_vars()
        
        assert isinstance(env_vars, dict)
        # Dovrebbe contenere almeno alcune variabili di sistema
        assert len(env_vars) > 0
