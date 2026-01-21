"""
Test per API endpoints Kafka
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch, MagicMock, mock_open
import json
from datetime import datetime

from app.main import app
from app.models.kafka import KafkaHealthStatus, KafkaMetrics, BatchResult


@pytest.fixture
def client():
    """Fixture per TestClient FastAPI"""
    return TestClient(app)


@pytest.fixture
def mock_kafka_connections():
    """Mock connections.json con connessioni Kafka"""
    return {
        'kafka_connections': {
            'default': {
                'bootstrap_servers': 'localhost:9092',
                'security_protocol': 'PLAINTEXT'
            },
            'prod': {
                'bootstrap_servers': 'kafka1:9092,kafka2:9092',
                'security_protocol': 'SASL_SSL',
                'sasl_mechanism': 'SCRAM-SHA-512',
                'sasl_username': 'user',
                'sasl_password': 'pass'
            }
        }
    }


class TestKafkaConnectionsEndpoint:
    """Test GET /api/kafka/connections"""

    def test_list_connections_success(self, client, mock_kafka_connections):
        """Test lista connessioni Kafka"""
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_kafka_connections))):
            with patch('app.api.kafka.Path.exists', return_value=True):
                response = client.get("/api/kafka/connections")
        
        assert response.status_code == 200
        data = response.json()
        assert 'connections' in data
        assert 'total' in data
        assert data['total'] == 2
        
        # Verifica connessioni
        conn_names = [c['name'] for c in data['connections']]
        assert 'default' in conn_names
        assert 'prod' in conn_names

    def test_list_connections_no_file(self, client):
        """Test connessioni quando file non esiste"""
        with patch('app.api.kafka.Path.exists', return_value=False):
            response = client.get("/api/kafka/connections")
        
        assert response.status_code == 500
        assert 'connections.json non trovato' in response.json()['detail']

    def test_list_connections_empty(self, client):
        """Test lista connessioni vuota"""
        empty_config = {'kafka_connections': {}}
        with patch('builtins.open', mock_open(read_data=json.dumps(empty_config))):
            with patch('app.api.kafka.Path.exists', return_value=True):
                response = client.get("/api/kafka/connections")
        
        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 0
        assert len(data['connections']) == 0


class TestKafkaTestConnectionEndpoint:
    """Test POST /api/kafka/test-connection"""

    def test_test_connection_by_name(self, client, mock_kafka_connections):
        """Test connessione usando connection_name"""
        mock_health = KafkaHealthStatus(
            connected=True,
            broker_count=3,
            latency_ms=45.5,
            last_check_timestamp=datetime.utcnow()
        )
        
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_kafka_connections))):
            with patch('app.api.kafka.Path.exists', return_value=True):
                with patch('app.api.kafka.KafkaService') as MockKafkaService:
                    mock_instance = AsyncMock()
                    mock_instance.health_check = AsyncMock(return_value=mock_health)
                    MockKafkaService.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
                    MockKafkaService.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    response = client.post(
                        "/api/kafka/test-connection",
                        json={'connection_name': 'default'}
                    )
        
        assert response.status_code == 200
        data = response.json()
        assert data['connected'] is True
        assert data['broker_count'] == 3
        assert 'latency_ms' in data

    def test_test_connection_by_servers(self, client):
        """Test connessione specificando direttamente bootstrap_servers"""
        mock_health = KafkaHealthStatus(
            connected=True,
            last_check_timestamp=datetime.utcnow()
        )
        
        with patch('app.api.kafka.KafkaService') as MockKafkaService:
            mock_instance = AsyncMock()
            mock_instance.health_check = AsyncMock(return_value=mock_health)
            MockKafkaService.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            MockKafkaService.return_value.__aexit__ = AsyncMock(return_value=None)
            
            response = client.post(
                "/api/kafka/test-connection",
                json={
                    'bootstrap_servers': 'localhost:9092',
                    'security_protocol': 'PLAINTEXT'
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data['connected'] is True

    def test_test_connection_not_found(self, client, mock_kafka_connections):
        """Test connessione non esistente"""
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_kafka_connections))):
            with patch('app.api.kafka.Path.exists', return_value=True):
                response = client.post(
                    "/api/kafka/test-connection",
                    json={'connection_name': 'non_esiste'}
                )
        
        assert response.status_code == 404
        assert 'non trovata' in response.json()['detail']

    def test_test_connection_failed(self, client, mock_kafka_connections):
        """Test connessione fallita"""
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_kafka_connections))):
            with patch('app.api.kafka.Path.exists', return_value=True):
                with patch('app.api.kafka.KafkaService') as MockKafkaService:
                    # Simula errore durante health check
                    mock_instance = AsyncMock()
                    mock_instance.health_check = AsyncMock(side_effect=Exception("Connection timeout"))
                    MockKafkaService.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
                    MockKafkaService.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    response = client.post(
                        "/api/kafka/test-connection",
                        json={'connection_name': 'default'}
                    )
        
        assert response.status_code == 200  # Ritorna 200 ma con connected=False
        data = response.json()
        assert data['connected'] is False
        assert 'error' in data

    def test_test_connection_missing_params(self, client):
        """Test senza parametri richiesti"""
        response = client.post("/api/kafka/test-connection", json={})
        
        assert response.status_code == 400
        assert 'connection_name o bootstrap_servers' in response.json()['detail']


class TestKafkaPublishEndpoint:
    """Test POST /api/kafka/publish"""

    def test_publish_message_success(self, client, mock_kafka_connections):
        """Test pubblicazione messaggio singolo"""
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_kafka_connections))):
            with patch('app.api.kafka.Path.exists', return_value=True):
                with patch('app.api.kafka.KafkaService') as MockKafkaService:
                    mock_instance = AsyncMock()
                    mock_instance.send_message = AsyncMock(return_value=True)
                    MockKafkaService.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
                    MockKafkaService.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    response = client.post(
                        "/api/kafka/publish",
                        json={
                            'topic': 'test-topic',
                            'key': 'test-key',
                            'value': {'data': 'test-value'},
                            'connection_name': 'default'
                        }
                    )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['topic'] == 'test-topic'
        assert data['key'] == 'test-key'

    def test_publish_message_with_headers(self, client, mock_kafka_connections):
        """Test pubblicazione con headers"""
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_kafka_connections))):
            with patch('app.api.kafka.Path.exists', return_value=True):
                with patch('app.api.kafka.KafkaService') as MockKafkaService:
                    mock_instance = AsyncMock()
                    mock_instance.send_message = AsyncMock(return_value=True)
                    MockKafkaService.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
                    MockKafkaService.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    response = client.post(
                        "/api/kafka/publish",
                        json={
                            'topic': 'test-topic',
                            'key': 'test-key',
                            'value': {'data': 'test'},
                            'connection_name': 'default',
                            'headers': {'source': 'api-test'}
                        }
                    )
        
        assert response.status_code == 200

    def test_publish_message_failed(self, client, mock_kafka_connections):
        """Test pubblicazione fallita"""
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_kafka_connections))):
            with patch('app.api.kafka.Path.exists', return_value=True):
                with patch('app.api.kafka.KafkaService') as MockKafkaService:
                    mock_instance = AsyncMock()
                    mock_instance.send_message = AsyncMock(return_value=False)
                    MockKafkaService.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
                    MockKafkaService.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    response = client.post(
                        "/api/kafka/publish",
                        json={
                            'topic': 'test-topic',
                            'key': 'test-key',
                            'value': {'data': 'test'},
                            'connection_name': 'default'
                        }
                    )
        
        assert response.status_code == 500


class TestKafkaBatchPublishEndpoint:
    """Test POST /api/kafka/publish-batch"""

    def test_publish_batch_success(self, client, mock_kafka_connections):
        """Test pubblicazione batch"""
        mock_result = BatchResult(
            total=3,
            succeeded=3,
            failed=0,
            duration_ms=150.0
        )
        
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_kafka_connections))):
            with patch('app.api.kafka.Path.exists', return_value=True):
                with patch('app.api.kafka.KafkaService') as MockKafkaService:
                    mock_instance = AsyncMock()
                    mock_instance.send_batch_with_retry = AsyncMock(return_value=mock_result)
                    MockKafkaService.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
                    MockKafkaService.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    response = client.post(
                        "/api/kafka/publish-batch",
                        json={
                            'topic': 'test-topic',
                            'messages': [
                                {'key': 'key1', 'value': {'data': 'value1'}},
                                {'key': 'key2', 'value': {'data': 'value2'}},
                                {'key': 'key3', 'value': {'data': 'value3'}}
                            ],
                            'connection_name': 'default',
                            'batch_size': 100,
                            'max_retries': 3
                        }
                    )
        
        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 3
        assert data['succeeded'] == 3
        assert data['failed'] == 0

    def test_publish_batch_invalid_format(self, client, mock_kafka_connections):
        """Test batch con formato messaggi invalido"""
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_kafka_connections))):
            with patch('app.api.kafka.Path.exists', return_value=True):
                response = client.post(
                    "/api/kafka/publish-batch",
                    json={
                        'topic': 'test-topic',
                        'messages': [
                            {'key': 'key1'},  # Manca 'value'
                            {'value': {'data': 'value2'}}  # Manca 'key'
                        ],
                        'connection_name': 'default'
                    }
                )
        
        assert response.status_code == 400
        assert 'deve contenere' in response.json()['detail']


class TestKafkaHealthEndpoint:
    """Test GET /api/kafka/health"""

    def test_health_check_success(self, client, mock_kafka_connections):
        """Test health check connessione"""
        mock_health = KafkaHealthStatus(
            connected=True,
            broker_count=3,
            latency_ms=25.0,
            last_check_timestamp=datetime.utcnow()
        )
        
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_kafka_connections))):
            with patch('app.api.kafka.Path.exists', return_value=True):
                with patch('app.api.kafka.KafkaService') as MockKafkaService:
                    mock_instance = AsyncMock()
                    mock_instance.health_check = AsyncMock(return_value=mock_health)
                    MockKafkaService.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
                    MockKafkaService.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    response = client.get("/api/kafka/health?connection_name=default")
        
        assert response.status_code == 200
        data = response.json()
        assert data['connected'] is True
        assert data['broker_count'] == 3


class TestKafkaMetricsEndpoint:
    """Test GET /api/kafka/metrics"""

    def test_get_metrics_success(self, client, mock_kafka_connections):
        """Test recupero metriche"""
        mock_metrics = KafkaMetrics(
            messages_sent=1000,
            messages_failed=10,
            avg_latency_ms=15.5,
            success_rate=99.0,
            last_success_timestamp=datetime.utcnow()
        )
        
        with patch('builtins.open', mock_open(read_data=json.dumps(mock_kafka_connections))):
            with patch('app.api.kafka.Path.exists', return_value=True):
                with patch('app.api.kafka.KafkaService') as MockKafkaService:
                    mock_instance = AsyncMock()
                    mock_instance.get_metrics = Mock(return_value=mock_metrics)
                    MockKafkaService.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
                    MockKafkaService.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    response = client.get("/api/kafka/metrics?connection_name=default")
        
        assert response.status_code == 200
        data = response.json()
        assert data['messages_sent'] == 1000
        assert data['messages_failed'] == 10
        assert data['success_rate'] == 99.0
