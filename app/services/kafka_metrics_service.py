"""
Servizio per gestione metriche Kafka con persistenza e aggregazione
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json
from loguru import logger
from pydantic import BaseModel

from app.models.kafka import KafkaMetrics


class KafkaMetricEntry(BaseModel):
    """Entry singola per metriche Kafka"""
    timestamp: datetime
    topic: str
    messages_sent: int
    messages_failed: int
    bytes_sent: int
    latency_ms: float
    operation_type: str  # "single", "batch", "scheduler"
    source: Optional[str] = None  # Nome schedulazione o "manual"
    error_message: Optional[str] = None


class KafkaMetricsSummary(BaseModel):
    """Riepilogo metriche aggregate"""
    period: str  # "today", "last_7_days", "last_30_days"
    total_messages: int
    successful_messages: int
    failed_messages: int
    success_rate: float
    avg_latency_ms: float
    total_bytes: int
    by_topic: Dict[str, dict]
    recent_errors: List[dict]


class KafkaMetricsService:
    """Servizio per persistenza e aggregazione metriche Kafka"""
    
    def __init__(self, metrics_file: Path = None):
        """
        Inizializza il servizio metriche
        
        Args:
            metrics_file: Path al file JSON per persistenza (default: exports/kafka_metrics.json)
        """
        if metrics_file is None:
            metrics_file = Path("exports/kafka_metrics.json")
        
        self.metrics_file = metrics_file
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Crea il file metriche se non esiste"""
        if not self.metrics_file.exists():
            self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
            self._write_metrics([])
            logger.info(f"[KAFKA_METRICS] Creato file metriche: {self.metrics_file}")
    
    def _read_metrics(self) -> List[dict]:
        """Legge tutte le metriche dal file"""
        try:
            with open(self.metrics_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[KAFKA_METRICS] Errore lettura file: {e}")
            return []
    
    def _write_metrics(self, metrics: List[dict]):
        """Scrive metriche nel file"""
        try:
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                json.dump(metrics, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"[KAFKA_METRICS] Errore scrittura file: {e}")
    
    def record_metric(
        self,
        topic: str,
        messages_sent: int,
        messages_failed: int,
        bytes_sent: int,
        latency_ms: float,
        operation_type: str = "single",
        source: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """
        Registra una nuova metrica
        
        Args:
            topic: Nome topic Kafka
            messages_sent: Numero messaggi inviati con successo
            messages_failed: Numero messaggi falliti
            bytes_sent: Bytes totali inviati
            latency_ms: Latenza media operazione
            operation_type: Tipo operazione (single, batch, scheduler)
            source: Nome schedulazione o "manual"
            error_message: Messaggio errore se presente
        """
        try:
            entry = KafkaMetricEntry(
                timestamp=datetime.now(),
                topic=topic,
                messages_sent=messages_sent,
                messages_failed=messages_failed,
                bytes_sent=bytes_sent,
                latency_ms=latency_ms,
                operation_type=operation_type,
                source=source,
                error_message=error_message
            )
            
            metrics = self._read_metrics()
            metrics.append(entry.model_dump(mode='json'))
            self._write_metrics(metrics)
            
            logger.debug(f"[KAFKA_METRICS] Registrata: topic={topic}, sent={messages_sent}, failed={messages_failed}")
            
        except Exception as e:
            logger.error(f"[KAFKA_METRICS] Errore registrazione: {e}")
    
    def get_summary(self, period: str = "today") -> KafkaMetricsSummary:
        """
        Ottiene riepilogo metriche per periodo
        
        Args:
            period: Periodo di aggregazione (today, last_7_days, last_30_days, all)
        
        Returns:
            KafkaMetricsSummary con metriche aggregate
        """
        try:
            metrics = self._read_metrics()
            
            # Filtra per periodo
            now = datetime.now()
            if period == "today":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "last_7_days":
                start_date = now - timedelta(days=7)
            elif period == "last_30_days":
                start_date = now - timedelta(days=30)
            else:  # "all"
                start_date = datetime.min
            
            filtered_metrics = [
                m for m in metrics
                if datetime.fromisoformat(m['timestamp']) >= start_date
            ]
            
            # Aggregazione
            total_messages = sum(m['messages_sent'] for m in filtered_metrics)
            successful_messages = sum(m['messages_sent'] for m in filtered_metrics)
            failed_messages = sum(m['messages_failed'] for m in filtered_metrics)
            total_bytes = sum(m['bytes_sent'] for m in filtered_metrics)
            
            # Success rate
            total_attempts = successful_messages + failed_messages
            success_rate = (successful_messages / total_attempts * 100) if total_attempts > 0 else 0.0
            
            # Latenza media
            latencies = [m['latency_ms'] for m in filtered_metrics if m['messages_sent'] > 0]
            avg_latency_ms = sum(latencies) / len(latencies) if latencies else 0.0
            
            # Aggregazione per topic
            by_topic = {}
            for m in filtered_metrics:
                topic = m['topic']
                if topic not in by_topic:
                    by_topic[topic] = {
                        'messages_sent': 0,
                        'messages_failed': 0,
                        'bytes_sent': 0,
                        'last_send': None
                    }
                
                by_topic[topic]['messages_sent'] += m['messages_sent']
                by_topic[topic]['messages_failed'] += m['messages_failed']
                by_topic[topic]['bytes_sent'] += m['bytes_sent']
                
                timestamp = m['timestamp']
                if by_topic[topic]['last_send'] is None or timestamp > by_topic[topic]['last_send']:
                    by_topic[topic]['last_send'] = timestamp
            
            # Errori recenti (ultimi 10)
            recent_errors = [
                {
                    'timestamp': m['timestamp'],
                    'topic': m['topic'],
                    'error': m.get('error_message', 'Unknown error'),
                    'failed_messages': m['messages_failed']
                }
                for m in sorted(
                    [m for m in filtered_metrics if m['messages_failed'] > 0],
                    key=lambda x: x['timestamp'],
                    reverse=True
                )[:10]
            ]
            
            return KafkaMetricsSummary(
                period=period,
                total_messages=total_messages,
                successful_messages=successful_messages,
                failed_messages=failed_messages,
                success_rate=round(success_rate, 2),
                avg_latency_ms=round(avg_latency_ms, 2),
                total_bytes=total_bytes,
                by_topic=by_topic,
                recent_errors=recent_errors
            )
            
        except Exception as e:
            logger.error(f"[KAFKA_METRICS] Errore calcolo summary: {e}")
            # Ritorna summary vuoto in caso di errore
            return KafkaMetricsSummary(
                period=period,
                total_messages=0,
                successful_messages=0,
                failed_messages=0,
                success_rate=0.0,
                avg_latency_ms=0.0,
                total_bytes=0,
                by_topic={},
                recent_errors=[]
            )
    
    def get_metrics_by_topic(self, topic: str, limit: int = 100) -> List[dict]:
        """
        Ottiene ultime N metriche per un topic specifico
        
        Args:
            topic: Nome topic Kafka
            limit: Numero massimo di entry da ritornare
        
        Returns:
            Lista metriche per il topic
        """
        try:
            metrics = self._read_metrics()
            topic_metrics = [m for m in metrics if m['topic'] == topic]
            topic_metrics.sort(key=lambda x: x['timestamp'], reverse=True)
            return topic_metrics[:limit]
            
        except Exception as e:
            logger.error(f"[KAFKA_METRICS] Errore filtro per topic: {e}")
            return []
    
    def cleanup_old_metrics(self, days: int = 90):
        """
        Rimuove metriche più vecchie di N giorni
        
        Args:
            days: Numero di giorni di retention
        """
        try:
            metrics = self._read_metrics()
            cutoff_date = datetime.now() - timedelta(days=days)
            
            filtered_metrics = [
                m for m in metrics
                if datetime.fromisoformat(m['timestamp']) >= cutoff_date
            ]
            
            removed_count = len(metrics) - len(filtered_metrics)
            if removed_count > 0:
                self._write_metrics(filtered_metrics)
                logger.info(f"[KAFKA_METRICS] Cleanup: rimossi {removed_count} record più vecchi di {days} giorni")
            
        except Exception as e:
            logger.error(f"[KAFKA_METRICS] Errore cleanup: {e}")
    
    def get_hourly_stats(self, hours: int = 24) -> List[dict]:
        """
        Ottiene statistiche aggregate per ora (ultime N ore)
        
        Args:
            hours: Numero di ore da analizzare
        
        Returns:
            Lista di dict con statistiche orarie
        """
        try:
            metrics = self._read_metrics()
            now = datetime.now()
            start_time = now - timedelta(hours=hours)
            
            # Filtra metriche nel periodo
            filtered_metrics = [
                m for m in metrics
                if datetime.fromisoformat(m['timestamp']) >= start_time
            ]
            
            # Aggrega per ora
            hourly_stats = {}
            for m in filtered_metrics:
                timestamp = datetime.fromisoformat(m['timestamp'])
                hour_key = timestamp.replace(minute=0, second=0, microsecond=0).isoformat()
                
                if hour_key not in hourly_stats:
                    hourly_stats[hour_key] = {
                        'hour': hour_key,
                        'messages_sent': 0,
                        'messages_failed': 0,
                        'latencies': []
                    }
                
                hourly_stats[hour_key]['messages_sent'] += m['messages_sent']
                hourly_stats[hour_key]['messages_failed'] += m['messages_failed']
                if m['latency_ms'] > 0:
                    hourly_stats[hour_key]['latencies'].append(m['latency_ms'])
            
            # Calcola statistiche finali
            result = []
            for hour_key in sorted(hourly_stats.keys()):
                stats = hourly_stats[hour_key]
                latencies = stats['latencies']
                
                result.append({
                    'hour': hour_key,
                    'messages_sent': stats['messages_sent'],
                    'messages_failed': stats['messages_failed'],
                    'avg_latency_ms': round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
                    'success_rate': round(
                        stats['messages_sent'] / (stats['messages_sent'] + stats['messages_failed']) * 100, 2
                    ) if (stats['messages_sent'] + stats['messages_failed']) > 0 else 0.0
                })
            
            return result
            
        except Exception as e:
            logger.error(f"[KAFKA_METRICS] Errore calcolo hourly stats: {e}")
            return []


# Singleton instance
_kafka_metrics_service = None

def get_kafka_metrics_service() -> KafkaMetricsService:
    """Ottiene istanza singleton del servizio metriche"""
    global _kafka_metrics_service
    if _kafka_metrics_service is None:
        _kafka_metrics_service = KafkaMetricsService()
    return _kafka_metrics_service
