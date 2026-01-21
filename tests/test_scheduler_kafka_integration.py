"""
Test integrazione Kafka con SchedulerService
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock, mock_open
from datetime import datetime
from pathlib import Path
import json

from app.services.scheduler_service import SchedulerService
from app.models.scheduling import SchedulingItem, SharingMode
from app.models.kafka import BatchResult


@pytest.fixture
def scheduler_service():
    """Fixture per SchedulerService"""
    with patch('app.services.scheduler_service.get_settings') as mock_settings:
        mock_settings.return_value = MagicMock(
            export_dir="exports",
            scheduling=[]
        )
        service = SchedulerService()
        service.export_dir = Path("exports")
        yield service


@pytest.fixture
def kafka_sched_config():
    """Configurazione scheduling con export Kafka"""
    return {
        'query': 'TEST-001--Query.sql',
        'connection': 'test_db',
        'enabled': True,
        'scheduling_mode': 'classic',
        'days_of_week': [0, 1, 2, 3, 4],
        'hour': 8,
        'minute': 0,
        'sharing_mode': 'kafka',
        'kafka_topic': 'test-topic',
        'kafka_key_field': 'id',
        'kafka_batch_size': 100,
        'kafka_include_metadata': True,
        'kafka_connection': 'default'
    }


@pytest.fixture
def sample_query_result():
    """Risultati query di esempio"""
    return [
        {'id': '001', 'name': 'Test 1', 'value': 100},
        {'id': '002', 'name': 'Test 2', 'value': 200},
        {'id': '003', 'name': 'Test 3', 'value': 300},
    ]


class TestSchedulingItemKafkaFields:
    """Test estensione SchedulingItem con campi Kafka"""

    def test_kafka_fields_present(self, kafka_sched_config):
        """Test presenza campi Kafka in SchedulingItem"""
        item = SchedulingItem(**kafka_sched_config)
        
        assert item.sharing_mode == SharingMode.KAFKA
        assert item.kafka_topic == 'test-topic'
        assert item.kafka_key_field == 'id'
        assert item.kafka_batch_size == 100
        assert item.kafka_include_metadata is True
        assert item.kafka_connection == 'default'

    def test_kafka_fields_optional(self):
        """Test campi Kafka opzionali"""
        minimal_config = {
            'query': 'test.sql',
            'connection': 'test_db',
            'sharing_mode': 'filesystem'
        }
        item = SchedulingItem(**minimal_config)
        
        assert item.kafka_topic is None
        assert item.kafka_key_field is None
        assert item.kafka_batch_size == 100  # default
        assert item.kafka_include_metadata is True  # default

    def test_kafka_batch_size_validation(self):
        """Test validazione batch_size Kafka"""
        config = {
            'query': 'test.sql',
            'connection': 'test_db',
            'kafka_batch_size': 5000
        }
        item = SchedulingItem(**config)
        assert item.kafka_batch_size == 5000
        
        # Test bounds
        with pytest.raises(Exception):
            SchedulingItem(**{**config, 'kafka_batch_size': 0})
        
        with pytest.raises(Exception):
            SchedulingItem(**{**config, 'kafka_batch_size': 20000})

    def test_sharing_mode_kafka_enum(self):
        """Test SharingMode KAFKA enum value"""
        assert SharingMode.KAFKA == 'kafka'
        assert 'kafka' in [mode.value for mode in SharingMode]


class TestKafkaExportMethod:
    """Test metodo _execute_kafka_export"""

    @pytest.mark.asyncio
    async def test_execute_kafka_export_success(
        self, scheduler_service, kafka_sched_config, sample_query_result
    ):
        """Test export Kafka con successo"""
        # Mock connections.json
        connections_data = {
            'kafka_connections': {
                'default': {
                    'bootstrap_servers': 'localhost:9092',
                    'security_protocol': 'PLAINTEXT'
                }
            }
        }
        
        # Mock BatchResult success
        mock_batch_result = BatchResult(
            total=3,
            succeeded=3,
            failed=0,
            duration_ms=150.0
        )
        
        with patch('builtins.open', mock_open(read_data=json.dumps(connections_data))):
            with patch('app.services.scheduler_service.Path.exists', return_value=True):
                with patch('app.services.scheduler_service.KafkaService') as MockKafkaService:
                    # Mock KafkaService context manager
                    mock_kafka_instance = AsyncMock()
                    mock_kafka_instance.send_batch_with_retry = AsyncMock(return_value=mock_batch_result)
                    MockKafkaService.return_value.__aenter__ = AsyncMock(return_value=mock_kafka_instance)
                    MockKafkaService.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    # Prepara history
                    scheduler_service.execution_history.append({
                        'query': 'TEST-001--Query.sql',
                        'connection': 'test_db',
                        'timestamp': datetime.now().isoformat(),
                        'status': 'success'
                    })
                    
                    # Esegui export
                    await scheduler_service._execute_kafka_export(
                        export_id='test-001',
                        sched=kafka_sched_config,
                        result_data=sample_query_result,
                        query_filename='TEST-001--Query.sql',
                        connection_name='test_db',
                        start_time=datetime.now()
                    )
                    
                    # Verifica chiamata send_batch_with_retry
                    mock_kafka_instance.send_batch_with_retry.assert_called_once()
                    call_args = mock_kafka_instance.send_batch_with_retry.call_args
                    
                    # Verifica topic
                    assert call_args.kwargs['topic'] == 'test-topic'
                    
                    # Verifica messaggi
                    messages = call_args.kwargs['messages']
                    assert len(messages) == 3
                    assert messages[0][0] == '001'  # message key
                    assert messages[0][1]['id'] == '001'
                    assert '_metadata' in messages[0][1]
                    
                    # Verifica history aggiornata
                    assert scheduler_service.execution_history[-1]['kafka_topic'] == 'test-topic'
                    assert scheduler_service.execution_history[-1]['kafka_messages_sent'] == 3
                    assert scheduler_service.execution_history[-1]['kafka_messages_failed'] == 0
                    assert scheduler_service.execution_history[-1]['export_mode'] == 'kafka'

    @pytest.mark.asyncio
    async def test_execute_kafka_export_no_topic(
        self, scheduler_service, kafka_sched_config, sample_query_result
    ):
        """Test export Kafka senza topic specificato"""
        config_no_topic = {**kafka_sched_config, 'kafka_topic': None}
        
        with pytest.raises(ValueError, match="kafka_topic non specificato"):
            await scheduler_service._execute_kafka_export(
                export_id='test-002',
                sched=config_no_topic,
                result_data=sample_query_result,
                query_filename='TEST-002--Query.sql',
                connection_name='test_db',
                start_time=datetime.now()
            )

    @pytest.mark.asyncio
    async def test_execute_kafka_export_connection_not_found(
        self, scheduler_service, kafka_sched_config, sample_query_result
    ):
        """Test export Kafka con connessione non esistente"""
        connections_data = {
            'kafka_connections': {
                'other': {
                    'bootstrap_servers': 'localhost:9092'
                }
            }
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(connections_data))):
            with patch('app.services.scheduler_service.Path.exists', return_value=True):
                with pytest.raises(ValueError, match="Connessione Kafka 'default' non trovata"):
                    await scheduler_service._execute_kafka_export(
                        export_id='test-003',
                        sched=kafka_sched_config,
                        result_data=sample_query_result,
                        query_filename='TEST-003--Query.sql',
                        connection_name='test_db',
                        start_time=datetime.now()
                    )

    @pytest.mark.asyncio
    async def test_execute_kafka_export_partial_failure(
        self, scheduler_service, kafka_sched_config, sample_query_result
    ):
        """Test export Kafka con fallimento parziale"""
        connections_data = {
            'kafka_connections': {
                'default': {
                    'bootstrap_servers': 'localhost:9092',
                    'security_protocol': 'PLAINTEXT'
                }
            }
        }
        
        # Mock BatchResult con fallimenti (success_rate < 95%)
        mock_batch_result = BatchResult(
            total=3,
            succeeded=1,
            failed=2,
            errors=['Error 1', 'Error 2'],
            duration_ms=200.0
        )
        
        with patch('builtins.open', mock_open(read_data=json.dumps(connections_data))):
            with patch('app.services.scheduler_service.Path.exists', return_value=True):
                with patch('app.services.scheduler_service.KafkaService') as MockKafkaService:
                    mock_kafka_instance = AsyncMock()
                    mock_kafka_instance.send_batch_with_retry = AsyncMock(return_value=mock_batch_result)
                    MockKafkaService.return_value.__aenter__ = AsyncMock(return_value=mock_kafka_instance)
                    MockKafkaService.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    scheduler_service.execution_history.append({
                        'query': 'TEST-004--Query.sql',
                        'connection': 'test_db'
                    })
                    
                    with pytest.raises(Exception, match="Kafka export failed"):
                        await scheduler_service._execute_kafka_export(
                            export_id='test-004',
                            sched=kafka_sched_config,
                            result_data=sample_query_result,
                            query_filename='TEST-004--Query.sql',
                            connection_name='test_db',
                            start_time=datetime.now()
                        )

    @pytest.mark.asyncio
    async def test_execute_kafka_export_metadata_inclusion(
        self, scheduler_service, kafka_sched_config, sample_query_result
    ):
        """Test inclusione metadata nei messaggi Kafka"""
        connections_data = {
            'kafka_connections': {
                'default': {
                    'bootstrap_servers': 'localhost:9092',
                    'security_protocol': 'PLAINTEXT'
                }
            }
        }
        
        mock_batch_result = BatchResult(total=3, succeeded=3, failed=0)
        
        with patch('builtins.open', mock_open(read_data=json.dumps(connections_data))):
            with patch('app.services.scheduler_service.Path.exists', return_value=True):
                with patch('app.services.scheduler_service.KafkaService') as MockKafkaService:
                    mock_kafka_instance = AsyncMock()
                    mock_kafka_instance.send_batch_with_retry = AsyncMock(return_value=mock_batch_result)
                    MockKafkaService.return_value.__aenter__ = AsyncMock(return_value=mock_kafka_instance)
                    MockKafkaService.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    scheduler_service.execution_history.append({'query': 'TEST-005--Query.sql'})
                    
                    await scheduler_service._execute_kafka_export(
                        export_id='test-005',
                        sched=kafka_sched_config,
                        result_data=sample_query_result,
                        query_filename='TEST-005--Query.sql',
                        connection_name='test_db',
                        start_time=datetime.now()
                    )
                    
                    # Verifica metadata incluso
                    call_args = mock_kafka_instance.send_batch_with_retry.call_args
                    messages = call_args.kwargs['messages']
                    
                    for key, value in messages:
                        assert '_metadata' in value
                        assert value['_metadata']['source_query'] == 'TEST-005--Query.sql'
                        assert value['_metadata']['source_connection'] == 'test_db'
                        assert 'export_timestamp' in value['_metadata']

    @pytest.mark.asyncio
    async def test_execute_kafka_export_without_metadata(
        self, scheduler_service, kafka_sched_config, sample_query_result
    ):
        """Test export Kafka senza metadata"""
        config_no_metadata = {**kafka_sched_config, 'kafka_include_metadata': False}
        connections_data = {
            'kafka_connections': {
                'default': {
                    'bootstrap_servers': 'localhost:9092',
                    'security_protocol': 'PLAINTEXT'
                }
            }
        }
        
        mock_batch_result = BatchResult(total=3, succeeded=3, failed=0)
        
        with patch('builtins.open', mock_open(read_data=json.dumps(connections_data))):
            with patch('app.services.scheduler_service.Path.exists', return_value=True):
                with patch('app.services.scheduler_service.KafkaService') as MockKafkaService:
                    mock_kafka_instance = AsyncMock()
                    mock_kafka_instance.send_batch_with_retry = AsyncMock(return_value=mock_batch_result)
                    MockKafkaService.return_value.__aenter__ = AsyncMock(return_value=mock_kafka_instance)
                    MockKafkaService.return_value.__aexit__ = AsyncMock(return_value=None)
                    
                    scheduler_service.execution_history.append({'query': 'TEST-006--Query.sql'})
                    
                    await scheduler_service._execute_kafka_export(
                        export_id='test-006',
                        sched=config_no_metadata,
                        result_data=sample_query_result,
                        query_filename='TEST-006--Query.sql',
                        connection_name='test_db',
                        start_time=datetime.now()
                    )
                    
                    # Verifica metadata NON incluso
                    call_args = mock_kafka_instance.send_batch_with_retry.call_args
                    messages = call_args.kwargs['messages']
                    
                    for key, value in messages:
                        assert '_metadata' not in value


class TestSchedulingHistoryKafkaFields:
    """Test estensione SchedulingHistoryItem con campi Kafka"""

    def test_history_kafka_fields(self):
        """Test campi Kafka in history item"""
        from app.models.scheduling import SchedulingHistoryItem
        
        history = SchedulingHistoryItem(
            query='test.sql',
            connection='test_db',
            timestamp=datetime.now(),
            status='success',
            kafka_topic='test-topic',
            kafka_messages_sent=100,
            kafka_messages_failed=5,
            kafka_duration_sec=2.5,
            export_mode='kafka'
        )
        
        assert history.kafka_topic == 'test-topic'
        assert history.kafka_messages_sent == 100
        assert history.kafka_messages_failed == 5
        assert history.kafka_duration_sec == 2.5
        assert history.export_mode == 'kafka'

    def test_history_without_kafka_fields(self):
        """Test history item senza campi Kafka (filesystem/email)"""
        from app.models.scheduling import SchedulingHistoryItem
        
        history = SchedulingHistoryItem(
            query='test.sql',
            connection='test_db',
            timestamp=datetime.now(),
            status='success',
            export_mode='filesystem'
        )
        
        assert history.kafka_topic is None
        assert history.kafka_messages_sent is None
        assert history.kafka_messages_failed is None
        assert history.kafka_duration_sec is None
        assert history.export_mode == 'filesystem'


class TestExportModeTracking:
    """Test tracking export_mode in history"""

    def test_export_mode_kafka(self, scheduler_service):
        """Test export_mode='kafka' salvato in history"""
        # Simula entry history per Kafka
        scheduler_service.execution_history.append({
            'query': 'test.sql',
            'connection': 'test_db',
            'export_mode': 'kafka',
            'kafka_topic': 'test-topic'
        })
        
        assert scheduler_service.execution_history[-1]['export_mode'] == 'kafka'

    def test_export_mode_filesystem(self, scheduler_service):
        """Test export_mode='filesystem' salvato in history"""
        scheduler_service.execution_history.append({
            'query': 'test.sql',
            'connection': 'test_db',
            'export_mode': 'filesystem'
        })
        
        assert scheduler_service.execution_history[-1]['export_mode'] == 'filesystem'

    def test_export_mode_email(self, scheduler_service):
        """Test export_mode='email' salvato in history"""
        scheduler_service.execution_history.append({
            'query': 'test.sql',
            'connection': 'test_db',
            'export_mode': 'email'
        })
        
        assert scheduler_service.execution_history[-1]['export_mode'] == 'email'
