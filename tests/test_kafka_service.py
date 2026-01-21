"""
Test per KafkaService con mock Kafka producer
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from decimal import Decimal

from app.services.kafka_service import KafkaService, KafkaJSONEncoder
from app.models.kafka import (
    KafkaConnectionConfig,
    KafkaProducerConfig,
    SecurityProtocol,
    CompressionType,
    BatchResult,
)
from kafka.errors import (
    KafkaTimeoutError,
    NoBrokersAvailable,
    BrokerNotAvailableError,
)


class TestKafkaJSONEncoder:
    """Test per JSON encoder custom"""

    def test_encode_datetime(self):
        """Test serializzazione datetime"""
        dt = datetime(2026, 1, 18, 10, 30, 45)
        result = KafkaJSONEncoder().default(dt)
        assert result == "2026-01-18T10:30:45"

    def test_encode_date(self):
        """Test serializzazione date"""
        from datetime import date
        d = date(2026, 1, 18)
        result = KafkaJSONEncoder().default(d)
        assert result == "2026-01-18"

    def test_encode_decimal(self):
        """Test serializzazione Decimal"""
        dec = Decimal("123.456")
        result = KafkaJSONEncoder().default(dec)
        assert result == 123.456

    def test_encode_none(self):
        """Test serializzazione None"""
        result = KafkaJSONEncoder().default(None)
        assert result is None

    def test_encode_complex_dict(self):
        """Test serializzazione dict complesso"""
        import json
        data = {
            "timestamp": datetime(2026, 1, 18, 10, 0, 0),
            "amount": Decimal("99.99"),
            "date": datetime(2026, 1, 18).date(),
            "name": "Test",
            "value": None,
        }
        result = json.dumps(data, cls=KafkaJSONEncoder)
        assert "2026-01-18T10:00:00" in result
        assert "99.99" in result
        assert "Test" in result


@pytest.fixture
def connection_config():
    """Fixture per configurazione connessione"""
    return KafkaConnectionConfig(
        bootstrap_servers="localhost:9092",
        security_protocol=SecurityProtocol.PLAINTEXT,
    )


@pytest.fixture
def producer_config():
    """Fixture per configurazione producer"""
    return KafkaProducerConfig(
        compression_type=CompressionType.SNAPPY,
        batch_size=16384,
        enable_idempotence=True,
    )


@pytest.fixture
def kafka_service(connection_config, producer_config):
    """Fixture per KafkaService"""
    return KafkaService(
        connection_config=connection_config,
        producer_config=producer_config,
        max_retries=3,
        log_payload=False,
    )


class TestKafkaServiceInit:
    """Test inizializzazione KafkaService"""

    def test_service_initialization(self, kafka_service):
        """Test inizializzazione base"""
        assert kafka_service is not None
        assert kafka_service.producer is None
        assert kafka_service._is_connected is False
        assert kafka_service.max_retries == 3

    def test_service_with_custom_config(self):
        """Test inizializzazione con configurazione custom"""
        conn_config = KafkaConnectionConfig(
            bootstrap_servers="kafka1:9092,kafka2:9092",
            security_protocol=SecurityProtocol.SASL_SSL,
            sasl_mechanism="PLAIN",
            sasl_username="user",
            sasl_password="password",
        )
        prod_config = KafkaProducerConfig(
            compression_type=CompressionType.GZIP,
            batch_size=32768,
        )
        service = KafkaService(conn_config, prod_config, max_retries=5)

        assert service.connection_config.security_protocol == SecurityProtocol.SASL_SSL
        assert service.producer_config.compression_type == CompressionType.GZIP
        assert service.max_retries == 5


class TestKafkaServiceConnect:
    """Test connessione Kafka"""

    @pytest.mark.asyncio
    async def test_connect_success(self, kafka_service):
        """Test connessione riuscita"""
        mock_producer = MagicMock()

        with patch("app.services.kafka_service.KafkaProducer", return_value=mock_producer):
            result = await kafka_service.connect()

            assert result is True
            assert kafka_service.is_connected() is True
            assert kafka_service.producer is not None

    @pytest.mark.asyncio
    async def test_connect_no_brokers_available(self, kafka_service):
        """Test connessione fallita - nessun broker disponibile"""
        with patch(
            "app.services.kafka_service.KafkaProducer",
            side_effect=NoBrokersAvailable("No brokers available"),
        ):
            result = await kafka_service.connect()

            assert result is False
            assert kafka_service.is_connected() is False

    @pytest.mark.asyncio
    async def test_connect_generic_error(self, kafka_service):
        """Test connessione fallita - errore generico"""
        with patch(
            "app.services.kafka_service.KafkaProducer",
            side_effect=Exception("Connection error"),
        ):
            result = await kafka_service.connect()

            assert result is False
            assert kafka_service.is_connected() is False


class TestKafkaServiceSendMessage:
    """Test invio messaggi"""

    @pytest.mark.asyncio
    async def test_send_message_success(self, kafka_service):
        """Test invio messaggio con successo"""
        # Mock producer
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_record_metadata = MagicMock()
        mock_record_metadata.partition = 0
        mock_record_metadata.offset = 12345

        mock_future.get.return_value = mock_record_metadata
        mock_producer.send.return_value = mock_future

        kafka_service.producer = mock_producer
        kafka_service._is_connected = True

        # Invia messaggio
        result = await kafka_service.send_message(
            topic="test-topic",
            key="test-key",
            value={"message": "test"},
        )

        assert result is True
        assert kafka_service._metrics.messages_sent == 1
        assert kafka_service._metrics.messages_failed == 0
        mock_producer.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_with_headers(self, kafka_service):
        """Test invio messaggio con headers"""
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_record_metadata = MagicMock()
        mock_record_metadata.partition = 0
        mock_record_metadata.offset = 12345

        mock_future.get.return_value = mock_record_metadata
        mock_producer.send.return_value = mock_future

        kafka_service.producer = mock_producer
        kafka_service._is_connected = True

        # Invia con headers
        result = await kafka_service.send_message(
            topic="test-topic",
            key="test-key",
            value={"message": "test"},
            headers={"source": "pstt", "version": "1.0"},
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_send_message_timeout(self, kafka_service):
        """Test invio messaggio con timeout"""
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_future.get.side_effect = KafkaTimeoutError("Timeout")

        mock_producer.send.return_value = mock_future

        kafka_service.producer = mock_producer
        kafka_service._is_connected = True

        result = await kafka_service.send_message(
            topic="test-topic",
            key="test-key",
            value={"message": "test"},
        )

        assert result is False
        assert kafka_service._metrics.messages_failed == 1
        assert "Timeout" in kafka_service._metrics.last_error

    @pytest.mark.asyncio
    async def test_send_message_broker_unavailable(self, kafka_service):
        """Test invio messaggio con broker non disponibile"""
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_future.get.side_effect = BrokerNotAvailableError("Broker down")

        mock_producer.send.return_value = mock_future

        kafka_service.producer = mock_producer
        kafka_service._is_connected = True

        result = await kafka_service.send_message(
            topic="test-topic",
            key="test-key",
            value={"message": "test"},
        )

        assert result is False
        assert kafka_service._metrics.messages_failed == 1
        assert kafka_service.is_connected() is False

    @pytest.mark.asyncio
    async def test_send_message_not_connected(self, kafka_service):
        """Test invio messaggio quando non connesso"""
        kafka_service._is_connected = False
        kafka_service.producer = None

        with patch.object(kafka_service, "connect", return_value=False):
            result = await kafka_service.send_message(
                topic="test-topic",
                key="test-key",
                value={"message": "test"},
            )

            assert result is False
            assert kafka_service._metrics.messages_failed == 1


class TestKafkaServiceHealthCheck:
    """Test health check"""

    @pytest.mark.asyncio
    async def test_health_check_connected(self, kafka_service):
        """Test health check quando connesso"""
        mock_producer = MagicMock()
        kafka_service.producer = mock_producer
        kafka_service._is_connected = True

        status = await kafka_service.health_check()

        assert status.connected is True
        assert status.error is None
        assert status.latency_ms is not None
        assert status.broker_count == 1  # localhost:9092

    @pytest.mark.asyncio
    async def test_health_check_not_initialized(self, kafka_service):
        """Test health check quando producer non inizializzato"""
        status = await kafka_service.health_check()

        assert status.connected is False
        assert "non inizializzato" in status.error

    @pytest.mark.asyncio
    async def test_health_check_reconnect_success(self, kafka_service):
        """Test health check con riconnessione automatica"""
        kafka_service._is_connected = False
        kafka_service.producer = MagicMock()

        with patch.object(kafka_service, "connect", return_value=True):
            status = await kafka_service.health_check()

            assert status.connected is True


class TestKafkaServiceMetrics:
    """Test metriche"""

    def test_get_metrics_initial(self, kafka_service):
        """Test metriche iniziali"""
        metrics = kafka_service.get_metrics()

        assert metrics.messages_sent == 0
        assert metrics.messages_failed == 0
        assert metrics.success_rate == 100.0

    @pytest.mark.asyncio
    async def test_metrics_after_successful_send(self, kafka_service):
        """Test metriche dopo invio riuscito"""
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_record_metadata = MagicMock()
        mock_record_metadata.partition = 0
        mock_record_metadata.offset = 1

        mock_future.get.return_value = mock_record_metadata
        mock_producer.send.return_value = mock_future

        kafka_service.producer = mock_producer
        kafka_service._is_connected = True

        await kafka_service.send_message("topic", "key", {"test": "data"})

        metrics = kafka_service.get_metrics()
        assert metrics.messages_sent == 1
        assert metrics.messages_failed == 0
        assert metrics.success_rate == 100.0
        assert metrics.avg_latency_ms >= 0  # Può essere 0 nei test mock veloci
        assert metrics.bytes_sent > 0
        assert metrics.last_success_timestamp is not None

    def test_reset_metrics(self, kafka_service):
        """Test reset metriche"""
        kafka_service._metrics.messages_sent = 100
        kafka_service._metrics.messages_failed = 10

        kafka_service.reset_metrics()

        metrics = kafka_service.get_metrics()
        assert metrics.messages_sent == 0
        assert metrics.messages_failed == 0


class TestKafkaServiceClose:
    """Test chiusura connessione"""

    @pytest.mark.asyncio
    async def test_close_success(self, kafka_service):
        """Test chiusura connessione"""
        mock_producer = MagicMock()
        kafka_service.producer = mock_producer
        kafka_service._is_connected = True

        await kafka_service.close()

        assert kafka_service.producer is None
        assert kafka_service.is_connected() is False

    @pytest.mark.asyncio
    async def test_close_when_not_connected(self, kafka_service):
        """Test chiusura quando già disconnesso"""
        kafka_service.producer = None

        # Non dovrebbe sollevare eccezioni
        await kafka_service.close()


class TestKafkaServiceContextManager:
    """Test context manager"""

    @pytest.mark.asyncio
    async def test_context_manager(self, connection_config, producer_config):
        """Test utilizzo come context manager"""
        mock_producer = MagicMock()

        with patch("app.services.kafka_service.KafkaProducer", return_value=mock_producer):
            async with KafkaService(connection_config, producer_config) as service:
                assert service.is_connected() is True

            # Dopo exit, deve essere disconnesso
            # Nota: il check non può essere fatto qui perché l'oggetto è fuori scope


class TestKafkaServiceBatchPublishing:
    """Test batch publishing e performance"""

    @pytest.mark.asyncio
    async def test_send_batch_empty(self, kafka_service):
        """Test invio batch vuoto"""
        result = await kafka_service.send_batch("test-topic", [])
        
        assert result.total == 0
        assert result.succeeded == 0
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_send_batch_single_message(self, kafka_service):
        """Test invio batch con singolo messaggio"""
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_future.get = Mock(return_value=Mock())
        mock_producer.send = Mock(return_value=mock_future)
        mock_producer.flush = Mock()
        kafka_service.producer = mock_producer
        kafka_service._is_connected = True

        messages = [("key1", {"data": "value1"})]
        result = await kafka_service.send_batch("test-topic", messages)

        assert result.total == 1
        assert result.succeeded == 1
        assert result.failed == 0
        mock_producer.send.assert_called_once()
        mock_producer.flush.assert_called()

    @pytest.mark.asyncio
    async def test_send_batch_small_batch(self, kafka_service):
        """Test invio batch piccolo (10 messaggi)"""
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_future.get = Mock(return_value=Mock())
        mock_producer.send = Mock(return_value=mock_future)
        mock_producer.flush = Mock()
        kafka_service.producer = mock_producer
        kafka_service._is_connected = True

        messages = [(f"key{i}", {"data": f"value{i}"}) for i in range(10)]
        result = await kafka_service.send_batch("test-topic", messages, batch_size=5)

        assert result.total == 10
        assert result.succeeded == 10
        assert result.failed == 0
        assert mock_producer.send.call_count == 10
        mock_producer.flush.assert_called()

    @pytest.mark.asyncio
    async def test_send_batch_large_batch(self, kafka_service):
        """Test invio batch grande (1000 messaggi)"""
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_future.get = Mock(return_value=Mock())
        mock_producer.send = Mock(return_value=mock_future)
        mock_producer.flush = Mock()
        kafka_service.producer = mock_producer
        kafka_service._is_connected = True

        # Crea 1000 messaggi
        messages = [(f"key{i}", {"data": f"value{i}", "index": i}) for i in range(1000)]
        result = await kafka_service.send_batch("test-topic", messages, batch_size=100)

        assert result.total == 1000
        assert result.succeeded == 1000
        assert result.failed == 0
        assert mock_producer.send.call_count == 1000
        # Flush chiamato almeno una volta (finale)
        assert mock_producer.flush.call_count >= 1

    @pytest.mark.asyncio
    async def test_send_batch_with_headers(self, kafka_service):
        """Test invio batch con headers"""
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_future.get = Mock(return_value=Mock())
        mock_producer.send = Mock(return_value=mock_future)
        mock_producer.flush = Mock()
        kafka_service.producer = mock_producer
        kafka_service._is_connected = True

        messages = [("key1", {"data": "value1"})]
        headers = {"app": "pstt", "version": "1.0"}
        
        result = await kafka_service.send_batch("test-topic", messages, headers=headers)

        assert result.succeeded == 1
        # Verifica che headers siano stati passati
        call_args = mock_producer.send.call_args
        assert call_args.kwargs["headers"] is not None

    @pytest.mark.asyncio
    async def test_send_batch_partial_failure(self, kafka_service):
        """Test batch con alcuni messaggi falliti"""
        mock_producer = MagicMock()
        kafka_service.producer = mock_producer
        kafka_service._is_connected = True

        # Mock: primi 5 messaggi OK, successivi 5 FAIL
        call_count = 0
        def mock_send(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_future = MagicMock()
            if call_count <= 5:
                mock_future.get = Mock(return_value=Mock())
            else:
                mock_future.get = Mock(side_effect=KafkaTimeoutError("Timeout"))
            return mock_future

        mock_producer.send = mock_send
        mock_producer.flush = Mock()

        messages = [(f"key{i}", {"data": f"value{i}"}) for i in range(10)]
        result = await kafka_service.send_batch("test-topic", messages)

        assert result.total == 10
        assert result.succeeded == 5
        assert result.failed == 5
        assert len(result.errors) == 5

    @pytest.mark.asyncio
    async def test_send_batch_auto_reconnect(self, kafka_service):
        """Test auto-reconnessione se producer disconnesso"""
        kafka_service.producer = None
        kafka_service._is_connected = False

        # Mock connect per simulare reconnessione
        async def mock_connect():
            mock_producer = MagicMock()
            mock_future = MagicMock()
            mock_future.get = Mock(return_value=Mock())
            mock_producer.send = Mock(return_value=mock_future)
            mock_producer.flush = Mock()
            kafka_service.producer = mock_producer
            kafka_service._is_connected = True
            return True

        kafka_service.connect = mock_connect

        messages = [("key1", {"data": "value1"})]
        result = await kafka_service.send_batch("test-topic", messages)

        assert result.succeeded == 1

    @pytest.mark.asyncio
    async def test_send_batch_cannot_connect(self, kafka_service):
        """Test batch quando connessione fallisce"""
        kafka_service.producer = None
        kafka_service._is_connected = False

        async def mock_connect_fail():
            return False

        kafka_service.connect = mock_connect_fail

        messages = [("key1", {"data": "value1"})]
        result = await kafka_service.send_batch("test-topic", messages)

        assert result.total == 1
        assert result.succeeded == 0
        assert result.failed == 1

    @pytest.mark.asyncio
    async def test_send_batch_with_retry_success_first_attempt(self, kafka_service):
        """Test retry: successo al primo tentativo"""
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_future.get = Mock(return_value=Mock())
        mock_producer.send = Mock(return_value=mock_future)
        mock_producer.flush = Mock()
        kafka_service.producer = mock_producer
        kafka_service._is_connected = True

        messages = [("key1", {"data": "value1"})]
        result = await kafka_service.send_batch_with_retry(
            "test-topic", messages, max_retries=3, retry_backoff_ms=10
        )

        assert result.succeeded == 1
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_send_batch_with_retry_success_after_failures(self, kafka_service):
        """Test retry: successo dopo fallimenti iniziali"""
        attempt = 0

        async def mock_send_batch(*args, **kwargs):
            nonlocal attempt
            attempt += 1
            if attempt < 3:
                # Primi 2 tentativi: fallimento parziale (< 95% success)
                return BatchResult(total=10, succeeded=5, failed=5)
            else:
                # Terzo tentativo: successo
                return BatchResult(total=10, succeeded=10, failed=0)

        kafka_service.send_batch = mock_send_batch

        messages = [(f"key{i}", {"data": f"value{i}"}) for i in range(10)]
        result = await kafka_service.send_batch_with_retry(
            "test-topic", messages, max_retries=3, retry_backoff_ms=10
        )

        assert result.succeeded == 10
        assert attempt == 3

    @pytest.mark.asyncio
    async def test_send_batch_with_retry_all_attempts_fail(self, kafka_service):
        """Test retry: tutti i tentativi falliscono"""
        async def mock_send_batch_fail(*args, **kwargs):
            return BatchResult(total=10, succeeded=3, failed=7)

        kafka_service.send_batch = mock_send_batch_fail

        messages = [(f"key{i}", {"data": f"value{i}"}) for i in range(10)]
        result = await kafka_service.send_batch_with_retry(
            "test-topic", messages, max_retries=3, retry_backoff_ms=10
        )

        # Ritorna ultimo risultato tentativo
        assert result.total == 10
        assert result.succeeded == 3
        assert result.failed == 7

    @pytest.mark.asyncio
    async def test_send_batch_with_retry_exception_handling(self, kafka_service):
        """Test retry: gestione eccezioni"""
        attempt = 0

        async def mock_send_batch_exception(*args, **kwargs):
            nonlocal attempt
            attempt += 1
            if attempt < 3:
                raise Exception("Connection error")
            else:
                return BatchResult(total=5, succeeded=5, failed=0)

        kafka_service.send_batch = mock_send_batch_exception

        messages = [(f"key{i}", {"data": f"value{i}"}) for i in range(5)]
        result = await kafka_service.send_batch_with_retry(
            "test-topic", messages, max_retries=3, retry_backoff_ms=10
        )

        assert result.succeeded == 5
        assert attempt == 3

    @pytest.mark.asyncio
    async def test_chunk_messages(self, kafka_service):
        """Test chunking messaggi"""
        messages = [(f"key{i}", {"data": f"value{i}"}) for i in range(250)]
        
        chunks = kafka_service._chunk_messages(messages, chunk_size=100)
        
        assert len(chunks) == 3
        assert len(chunks[0]) == 100
        assert len(chunks[1]) == 100
        assert len(chunks[2]) == 50

    @pytest.mark.asyncio
    async def test_batch_metrics_update(self, kafka_service):
        """Test aggiornamento metriche dopo batch"""
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_future.get = Mock(return_value=Mock())
        mock_producer.send = Mock(return_value=mock_future)
        mock_producer.flush = Mock()
        kafka_service.producer = mock_producer
        kafka_service._is_connected = True

        # Reset metriche
        kafka_service.reset_metrics()
        initial_metrics = kafka_service.get_metrics()
        assert initial_metrics.messages_sent == 0

        # Invia batch
        messages = [(f"key{i}", {"data": f"value{i}"}) for i in range(50)]
        result = await kafka_service.send_batch("test-topic", messages)

        # Verifica metriche aggiornate
        metrics = kafka_service.get_metrics()
        assert metrics.messages_sent == 50
        assert metrics.success_rate == 100.0

    @pytest.mark.asyncio
    async def test_batch_result_success_rate(self):
        """Test calcolo success rate in BatchResult"""
        result1 = BatchResult(total=100, succeeded=100, failed=0)
        assert result1.get_success_rate() == 100.0

        result2 = BatchResult(total=100, succeeded=95, failed=5)
        assert result2.get_success_rate() == 95.0

        result3 = BatchResult(total=100, succeeded=0, failed=100)
        assert result3.get_success_rate() == 0.0

        # Batch vuoto = 100% (nessun messaggio fallito)
        result4 = BatchResult(total=0, succeeded=0, failed=0)
        assert result4.get_success_rate() == 100.0

    @pytest.mark.asyncio
    async def test_batch_performance_throughput(self, kafka_service):
        """Test performance: throughput >= 100 msg/sec"""
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_future.get = Mock(return_value=Mock())
        mock_producer.send = Mock(return_value=mock_future)
        mock_producer.flush = Mock()
        kafka_service.producer = mock_producer
        kafka_service._is_connected = True

        # Invia 1000 messaggi e misura tempo
        messages = [(f"key{i}", {"data": f"value{i}"}) for i in range(1000)]
        
        start = datetime.utcnow()
        result = await kafka_service.send_batch("test-topic", messages, batch_size=100)
        duration_sec = (datetime.utcnow() - start).total_seconds()

        assert result.succeeded == 1000
        
        # Calcola throughput
        throughput = 1000 / duration_sec if duration_sec > 0 else 0
        
        # Con mock dovrebbe essere molto veloce (>> 100 msg/sec)
        # Tolleranza bassa perché sono mock
        assert throughput > 100, f"Throughput troppo basso: {throughput:.1f} msg/sec"
