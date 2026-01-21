"""
Test per configurazione Kafka
"""
import pytest
from pydantic import ValidationError
from app.models.kafka import (
    KafkaConnectionConfig,
    KafkaProducerConfig,
    KafkaExportConfig,
    KafkaMetrics,
    BatchResult,
    KafkaHealthStatus,
    SecurityProtocol,
    CompressionType
)


class TestKafkaConnectionConfig:
    """Test per KafkaConnectionConfig"""
    
    def test_valid_connection_config(self):
        """Test configurazione connessione valida"""
        config = KafkaConnectionConfig(
            bootstrap_servers="localhost:9092",
            security_protocol=SecurityProtocol.PLAINTEXT
        )
        assert config.bootstrap_servers == "localhost:9092"
        assert config.security_protocol == SecurityProtocol.PLAINTEXT
        assert config.get_bootstrap_servers_list() == ["localhost:9092"]
    
    def test_multiple_bootstrap_servers(self):
        """Test con più bootstrap servers"""
        config = KafkaConnectionConfig(
            bootstrap_servers="host1:9092,host2:9092,host3:9092"
        )
        servers = config.get_bootstrap_servers_list()
        assert len(servers) == 3
        assert "host1:9092" in servers
        assert "host2:9092" in servers
        assert "host3:9092" in servers
    
    def test_invalid_bootstrap_servers_empty(self):
        """Test validazione bootstrap servers vuoti"""
        with pytest.raises(ValidationError):
            KafkaConnectionConfig(bootstrap_servers="")
    
    def test_invalid_bootstrap_servers_format(self):
        """Test validazione formato bootstrap servers errato"""
        with pytest.raises(ValidationError):
            KafkaConnectionConfig(bootstrap_servers="invalid-format")
    
    def test_sasl_config(self):
        """Test configurazione SASL"""
        config = KafkaConnectionConfig(
            bootstrap_servers="kafka:9092",
            security_protocol=SecurityProtocol.SASL_SSL,
            sasl_mechanism="PLAIN",
            sasl_username="user",
            sasl_password="password"
        )
        assert config.security_protocol == SecurityProtocol.SASL_SSL
        assert config.sasl_mechanism == "PLAIN"
        assert config.sasl_username == "user"


class TestKafkaProducerConfig:
    """Test per KafkaProducerConfig"""
    
    def test_default_producer_config(self):
        """Test configurazione producer con valori di default"""
        config = KafkaProducerConfig()
        assert config.compression_type == CompressionType.SNAPPY
        assert config.batch_size == 16384
        assert config.enable_idempotence is True
        assert config.acks == "all"
    
    def test_custom_producer_config(self):
        """Test configurazione producer custom"""
        config = KafkaProducerConfig(
            compression_type=CompressionType.GZIP,
            batch_size=32768,
            linger_ms=20,
            acks="1"
        )
        assert config.compression_type == CompressionType.GZIP
        assert config.batch_size == 32768
        assert config.linger_ms == 20
        assert config.acks == "1"
    
    def test_invalid_acks(self):
        """Test validazione acks invalido"""
        with pytest.raises(ValidationError):
            KafkaProducerConfig(acks="invalid")
    
    def test_invalid_batch_size(self):
        """Test validazione batch_size negativo"""
        with pytest.raises(ValidationError):
            KafkaProducerConfig(batch_size=-1)


class TestKafkaExportConfig:
    """Test per KafkaExportConfig"""
    
    def test_valid_export_config(self):
        """Test configurazione export valida"""
        config = KafkaExportConfig(
            enabled=True,
            topic="test-topic",
            message_key_field="id",
            batch_size=100
        )
        assert config.enabled is True
        assert config.topic == "test-topic"
        assert config.message_key_field == "id"
        assert config.batch_size == 100
        assert config.include_metadata is True
    
    def test_invalid_topic_empty(self):
        """Test validazione topic vuoto"""
        with pytest.raises(ValidationError):
            KafkaExportConfig(
                topic="",
                message_key_field="id"
            )
    
    def test_invalid_topic_with_spaces(self):
        """Test validazione topic con spazi"""
        with pytest.raises(ValidationError):
            KafkaExportConfig(
                topic="invalid topic",
                message_key_field="id"
            )
    
    def test_batch_size_bounds(self):
        """Test validazione limiti batch_size"""
        # Valido
        config = KafkaExportConfig(
            topic="test",
            message_key_field="id",
            batch_size=1
        )
        assert config.batch_size == 1
        
        # Valido
        config = KafkaExportConfig(
            topic="test",
            message_key_field="id",
            batch_size=10000
        )
        assert config.batch_size == 10000
        
        # Invalido (troppo piccolo)
        with pytest.raises(ValidationError):
            KafkaExportConfig(
                topic="test",
                message_key_field="id",
                batch_size=0
            )
        
        # Invalido (troppo grande)
        with pytest.raises(ValidationError):
            KafkaExportConfig(
                topic="test",
                message_key_field="id",
                batch_size=20000
            )


class TestKafkaMetrics:
    """Test per KafkaMetrics"""
    
    def test_default_metrics(self):
        """Test metriche con valori di default"""
        metrics = KafkaMetrics()
        assert metrics.messages_sent == 0
        assert metrics.messages_failed == 0
        assert metrics.success_rate == 100.0
    
    def test_calculate_success_rate(self):
        """Test calcolo success rate"""
        metrics = KafkaMetrics(
            messages_sent=95,
            messages_failed=5
        )
        rate = metrics.calculate_success_rate()
        assert rate == 95.0
        
        metrics.update_success_rate()
        assert metrics.success_rate == 95.0
    
    def test_success_rate_no_messages(self):
        """Test success rate quando non ci sono messaggi"""
        metrics = KafkaMetrics()
        assert metrics.calculate_success_rate() == 100.0
    
    def test_metrics_with_latency(self):
        """Test metriche con latenze"""
        metrics = KafkaMetrics(
            messages_sent=1000,
            avg_latency_ms=50.5,
            p90_latency_ms=120.0,
            p99_latency_ms=350.0
        )
        assert metrics.avg_latency_ms == 50.5
        assert metrics.p90_latency_ms == 120.0
        assert metrics.p99_latency_ms == 350.0


class TestBatchResult:
    """Test per BatchResult"""
    
    def test_successful_batch(self):
        """Test batch completamente riuscito"""
        result = BatchResult(
            total=100,
            succeeded=100,
            failed=0,
            duration_ms=1234.5
        )
        assert result.is_successful() is True
        assert result.get_success_rate() == 100.0
    
    def test_partial_failure_batch(self):
        """Test batch con alcuni fallimenti"""
        result = BatchResult(
            total=100,
            succeeded=95,
            failed=5,
            errors=["Error 1", "Error 2"]
        )
        assert result.is_successful() is False
        assert result.get_success_rate() == 95.0
        assert len(result.errors) == 2
    
    def test_complete_failure_batch(self):
        """Test batch completamente fallito"""
        result = BatchResult(
            total=100,
            succeeded=0,
            failed=100,
            errors=["Critical error"]
        )
        assert result.is_successful() is False
        assert result.get_success_rate() == 0.0
    
    def test_empty_batch(self):
        """Test batch vuoto"""
        result = BatchResult(
            total=0,
            succeeded=0,
            failed=0
        )
        assert result.get_success_rate() == 100.0


class TestKafkaHealthStatus:
    """Test per KafkaHealthStatus"""
    
    def test_healthy_status(self):
        """Test status connesso"""
        status = KafkaHealthStatus(
            connected=True,
            broker_count=3,
            latency_ms=15.5
        )
        assert status.connected is True
        assert status.broker_count == 3
        assert status.latency_ms == 15.5
        assert status.error is None
    
    def test_unhealthy_status(self):
        """Test status disconnesso"""
        status = KafkaHealthStatus(
            connected=False,
            error="Connection refused"
        )
        assert status.connected is False
        assert status.error == "Connection refused"


class TestEnums:
    """Test per enumerazioni Kafka"""
    
    def test_security_protocol_enum(self):
        """Test SecurityProtocol enum"""
        assert SecurityProtocol.PLAINTEXT.value == "PLAINTEXT"
        assert SecurityProtocol.SSL.value == "SSL"
        assert SecurityProtocol.SASL_SSL.value == "SASL_SSL"
    
    def test_compression_type_enum(self):
        """Test CompressionType enum"""
        assert CompressionType.SNAPPY.value == "snappy"
        assert CompressionType.GZIP.value == "gzip"
        assert CompressionType.NONE.value == "none"
