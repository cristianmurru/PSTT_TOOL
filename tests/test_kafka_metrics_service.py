"""
Test per KafkaMetricsService
"""
import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import json

from app.services.kafka_metrics_service import (
    KafkaMetricsService,
    KafkaMetricEntry,
    KafkaMetricsSummary
)


class TestKafkaMetricsService:
    """Test per il servizio metriche Kafka"""
    
    @pytest.fixture
    def temp_metrics_file(self):
        """Fixture per file metriche temporaneo"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = Path(f.name)
        yield temp_path
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()
    
    @pytest.fixture
    def metrics_service(self, temp_metrics_file):
        """Fixture per servizio metriche"""
        return KafkaMetricsService(metrics_file=temp_metrics_file)
    
    def test_service_initialization(self, metrics_service, temp_metrics_file):
        """Test inizializzazione servizio"""
        assert temp_metrics_file.exists()
        assert metrics_service.metrics_file == temp_metrics_file
    
    def test_record_single_metric(self, metrics_service):
        """Test registrazione singola metrica"""
        metrics_service.record_metric(
            topic="test-topic",
            messages_sent=1,
            messages_failed=0,
            bytes_sent=500,
            latency_ms=45.5,
            operation_type="single",
            source="manual"
        )
        
        # Verifica metrica salvata
        metrics = metrics_service._read_metrics()
        assert len(metrics) == 1
        assert metrics[0]['topic'] == "test-topic"
        assert metrics[0]['messages_sent'] == 1
        assert metrics[0]['messages_failed'] == 0
    
    def test_record_multiple_metrics(self, metrics_service):
        """Test registrazione multiple metriche"""
        for i in range(5):
            metrics_service.record_metric(
                topic=f"topic-{i}",
                messages_sent=10,
                messages_failed=0,
                bytes_sent=1000,
                latency_ms=50.0,
                operation_type="batch"
            )
        
        metrics = metrics_service._read_metrics()
        assert len(metrics) == 5
    
    def test_get_summary_today(self, metrics_service):
        """Test summary per oggi"""
        # Aggiungi metriche di oggi
        metrics_service.record_metric(
            topic="test-topic",
            messages_sent=100,
            messages_failed=2,
            bytes_sent=50000,
            latency_ms=45.0,
            operation_type="batch"
        )
        
        summary = metrics_service.get_summary(period="today")
        
        assert summary.period == "today"
        assert summary.total_messages == 100
        assert summary.successful_messages == 100
        assert summary.failed_messages == 2
        assert summary.success_rate > 0
        assert summary.avg_latency_ms == 45.0
    
    def test_get_summary_empty(self, metrics_service):
        """Test summary con metriche vuote"""
        summary = metrics_service.get_summary(period="today")
        
        assert summary.total_messages == 0
        assert summary.success_rate == 0.0
        assert summary.avg_latency_ms == 0.0
        assert len(summary.by_topic) == 0
    
    def test_get_summary_by_topic(self, metrics_service):
        """Test aggregazione per topic"""
        # Aggiungi metriche per topic diversi
        metrics_service.record_metric(
            topic="topic-a",
            messages_sent=100,
            messages_failed=0,
            bytes_sent=10000,
            latency_ms=30.0
        )
        
        metrics_service.record_metric(
            topic="topic-b",
            messages_sent=200,
            messages_failed=5,
            bytes_sent=20000,
            latency_ms=40.0
        )
        
        summary = metrics_service.get_summary(period="all")
        
        assert len(summary.by_topic) == 2
        assert "topic-a" in summary.by_topic
        assert "topic-b" in summary.by_topic
        assert summary.by_topic["topic-a"]["messages_sent"] == 100
        assert summary.by_topic["topic-b"]["messages_sent"] == 200
    
    def test_get_summary_with_errors(self, metrics_service):
        """Test summary con errori"""
        # Aggiungi metriche con errori
        metrics_service.record_metric(
            topic="test-topic",
            messages_sent=0,
            messages_failed=5,
            bytes_sent=0,
            latency_ms=0,
            operation_type="batch",
            error_message="Connection timeout"
        )
        
        summary = metrics_service.get_summary(period="today")
        
        assert summary.failed_messages == 5
        assert len(summary.recent_errors) == 1
        assert summary.recent_errors[0]['error'] == "Connection timeout"
    
    def test_get_metrics_by_topic(self, metrics_service):
        """Test filtro metriche per topic"""
        # Aggiungi metriche per topic diversi
        for i in range(10):
            metrics_service.record_metric(
                topic="target-topic",
                messages_sent=1,
                messages_failed=0,
                bytes_sent=100,
                latency_ms=20.0
            )
        
        for i in range(5):
            metrics_service.record_metric(
                topic="other-topic",
                messages_sent=1,
                messages_failed=0,
                bytes_sent=100,
                latency_ms=20.0
            )
        
        topic_metrics = metrics_service.get_metrics_by_topic("target-topic")
        
        assert len(topic_metrics) == 10
        assert all(m['topic'] == "target-topic" for m in topic_metrics)
    
    def test_get_metrics_by_topic_with_limit(self, metrics_service):
        """Test limite metriche per topic"""
        # Aggiungi 100 metriche
        for i in range(100):
            metrics_service.record_metric(
                topic="test-topic",
                messages_sent=1,
                messages_failed=0,
                bytes_sent=100,
                latency_ms=20.0
            )
        
        # Richiedi solo ultime 50
        topic_metrics = metrics_service.get_metrics_by_topic("test-topic", limit=50)
        
        assert len(topic_metrics) == 50
    
    def test_cleanup_old_metrics(self, metrics_service):
        """Test cleanup metriche vecchie"""
        # Aggiungi metriche vecchie (simulando modifica timestamp)
        metrics_service.record_metric(
            topic="old-topic",
            messages_sent=10,
            messages_failed=0,
            bytes_sent=1000,
            latency_ms=30.0
        )
        
        # Modifica timestamp manualmente per simulare record vecchio
        metrics = metrics_service._read_metrics()
        old_timestamp = (datetime.now() - timedelta(days=100)).isoformat()
        metrics[0]['timestamp'] = old_timestamp
        metrics_service._write_metrics(metrics)
        
        # Aggiungi metrica recente
        metrics_service.record_metric(
            topic="new-topic",
            messages_sent=5,
            messages_failed=0,
            bytes_sent=500,
            latency_ms=25.0
        )
        
        # Cleanup con retention 90 giorni
        metrics_service.cleanup_old_metrics(days=90)
        
        # Verifica che solo la metrica recente sia rimasta
        remaining_metrics = metrics_service._read_metrics()
        assert len(remaining_metrics) == 1
        assert remaining_metrics[0]['topic'] == "new-topic"
    
    def test_hourly_stats(self, metrics_service):
        """Test statistiche orarie"""
        # Aggiungi metriche con timestamp diversi nell'ultima ora
        for i in range(10):
            metrics_service.record_metric(
                topic="test-topic",
                messages_sent=10,
                messages_failed=0,
                bytes_sent=1000,
                latency_ms=30.0 + i
            )
        
        hourly_stats = metrics_service.get_hourly_stats(hours=24)
        
        # Dovrebbe esserci almeno 1 ora con dati
        assert len(hourly_stats) >= 1
        
        # Verifica struttura dati
        first_stat = hourly_stats[0]
        assert 'hour' in first_stat
        assert 'messages_sent' in first_stat
        assert 'messages_failed' in first_stat
        assert 'avg_latency_ms' in first_stat
        assert 'success_rate' in first_stat
    
    def test_hourly_stats_empty(self, metrics_service):
        """Test statistiche orarie senza dati"""
        hourly_stats = metrics_service.get_hourly_stats(hours=24)
        
        assert isinstance(hourly_stats, list)
        assert len(hourly_stats) == 0
    
    def test_success_rate_calculation(self, metrics_service):
        """Test calcolo success rate"""
        # 95 successi, 5 fallimenti
        metrics_service.record_metric(
            topic="test-topic",
            messages_sent=95,
            messages_failed=5,
            bytes_sent=50000,
            latency_ms=40.0
        )
        
        summary = metrics_service.get_summary(period="today")
        
        # Success rate dovrebbe essere 95%
        assert summary.success_rate == pytest.approx(95.0, rel=0.1)
    
    def test_metric_entry_validation(self):
        """Test validazione KafkaMetricEntry"""
        entry = KafkaMetricEntry(
            timestamp=datetime.now(),
            topic="test-topic",
            messages_sent=10,
            messages_failed=0,
            bytes_sent=1000,
            latency_ms=45.5,
            operation_type="batch"
        )
        
        assert entry.topic == "test-topic"
        assert entry.messages_sent == 10
        assert entry.operation_type == "batch"
    
    def test_summary_model(self):
        """Test modello KafkaMetricsSummary"""
        summary = KafkaMetricsSummary(
            period="today",
            total_messages=1000,
            successful_messages=990,
            failed_messages=10,
            success_rate=99.0,
            avg_latency_ms=45.5,
            total_bytes=500000,
            by_topic={},
            recent_errors=[]
        )
        
        assert summary.period == "today"
        assert summary.total_messages == 1000
        assert summary.success_rate == 99.0


class TestKafkaMetricsIntegration:
    """Test integrazione con altri servizi"""
    
    def test_singleton_instance(self):
        """Test singleton del servizio metriche"""
        from app.services.kafka_metrics_service import get_kafka_metrics_service
        
        service1 = get_kafka_metrics_service()
        service2 = get_kafka_metrics_service()
        
        assert service1 is service2
