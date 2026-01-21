"""
API endpoints per la gestione Kafka producer
"""
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, status, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import json
from pathlib import Path
from loguru import logger
from datetime import datetime

from app.services.kafka_service import KafkaService
from app.models.kafka import (
    KafkaConnectionConfig,
    KafkaProducerConfig,
    KafkaHealthStatus,
    KafkaMetrics,
    BatchResult
)
from app.core.config import get_settings


router = APIRouter()


# Request/Response Models
class KafkaConnectionTestRequest(BaseModel):
    """Request per test connessione Kafka"""
    connection_name: Optional[str] = Field(None, description="Nome connessione da connections.json")
    bootstrap_servers: Optional[str] = Field(None, description="Bootstrap servers (alternativa a connection_name)")
    security_protocol: Optional[str] = Field("PLAINTEXT", description="Security protocol")
    sasl_mechanism: Optional[str] = Field(None, description="SASL mechanism")
    sasl_username: Optional[str] = Field(None, description="SASL username")
    sasl_password: Optional[str] = Field(None, description="SASL password")


class KafkaPublishRequest(BaseModel):
    """Request per pubblicazione singolo messaggio"""
    topic: str = Field(..., description="Topic Kafka di destinazione")
    key: str = Field(..., description="Message key")
    value: dict = Field(..., description="Message value (JSON object)")
    connection_name: str = Field("default", description="Nome connessione Kafka")
    headers: Optional[Dict[str, str]] = Field(None, description="Message headers opzionali")


class KafkaBatchPublishRequest(BaseModel):
    """Request per pubblicazione batch"""
    topic: str = Field(..., description="Topic Kafka di destinazione")
    messages: List[Dict[str, Any]] = Field(..., description="Lista messaggi con 'key' e 'value'")
    connection_name: str = Field("default", description="Nome connessione Kafka")
    batch_size: int = Field(100, ge=1, le=10000, description="Dimensione chunk per processing")
    max_retries: int = Field(3, ge=1, le=10, description="Numero massimo retry")


class KafkaConnectionInfo(BaseModel):
    """Info connessione Kafka"""
    name: str
    bootstrap_servers: str
    security_protocol: str
    sasl_mechanism: Optional[str] = None
    description: Optional[str] = None


class KafkaConnectionsResponse(BaseModel):
    """Response lista connessioni Kafka"""
    connections: List[KafkaConnectionInfo]
    total: int


def get_kafka_connections() -> Dict[str, dict]:
    """Carica configurazioni Kafka da connections.json"""
    try:
        connections_path = Path("connections.json")
        if not connections_path.exists():
            raise FileNotFoundError("connections.json non trovato")
        
        with open(connections_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data.get('kafka_connections', {})
    except Exception as e:
        logger.error(f"Errore caricamento configurazioni Kafka: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Impossibile caricare configurazioni Kafka: {str(e)}"
        )


def get_kafka_connection_config(connection_name: str) -> KafkaConnectionConfig:
    """Recupera configurazione Kafka per nome connessione"""
    kafka_connections = get_kafka_connections()
    
    if connection_name not in kafka_connections:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connessione Kafka '{connection_name}' non trovata"
        )
    
    return KafkaConnectionConfig(**kafka_connections[connection_name])


@router.get("/connections", response_model=KafkaConnectionsResponse, summary="Lista connessioni Kafka")
async def list_kafka_connections():
    """
    Ottiene la lista di tutte le connessioni Kafka configurate
    """
    try:
        kafka_connections = get_kafka_connections()
        
        connections_info = []
        for name, config in kafka_connections.items():
            connections_info.append(KafkaConnectionInfo(
                name=name,
                bootstrap_servers=config.get('bootstrap_servers', ''),
                security_protocol=config.get('security_protocol', 'PLAINTEXT'),
                sasl_mechanism=config.get('sasl_mechanism'),
                description=config.get('description')
            ))
        
        return KafkaConnectionsResponse(
            connections=connections_info,
            total=len(connections_info)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore nel recupero connessioni Kafka: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/test-connection", response_model=KafkaHealthStatus, summary="Test connessione Kafka")
async def test_kafka_connection(request: KafkaConnectionTestRequest):
    """
    Testa la connettività con un cluster Kafka.
    
    Può usare:
    - connection_name: usa configurazione da connections.json
    - bootstrap_servers: specifica direttamente i server (con altri parametri)
    """
    try:
        # Determina configurazione da usare
        if request.connection_name:
            conn_config = get_kafka_connection_config(request.connection_name)
        elif request.bootstrap_servers:
            conn_config = KafkaConnectionConfig(
                bootstrap_servers=request.bootstrap_servers,
                security_protocol=request.security_protocol or "PLAINTEXT",
                sasl_mechanism=request.sasl_mechanism,
                sasl_username=request.sasl_username,
                sasl_password=request.sasl_password
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Specificare connection_name o bootstrap_servers"
            )
        
        # Test connessione
        producer_config = KafkaProducerConfig()  # usa defaults
        
        async with KafkaService(conn_config, producer_config) as kafka:
            health_status = await kafka.health_check()
        
        return health_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore test connessione Kafka: {e}")
        return KafkaHealthStatus(
            connected=False,
            error=str(e),
            last_check_timestamp=datetime.utcnow()
        )


@router.post("/publish", summary="Pubblica singolo messaggio")
async def publish_message(request: KafkaPublishRequest):
    """
    Pubblica un singolo messaggio su topic Kafka (per debug/test).
    """
    try:
        # Carica configurazione
        conn_config = get_kafka_connection_config(request.connection_name)
        producer_config = KafkaProducerConfig()
        
        # Pubblica messaggio
        async with KafkaService(conn_config, producer_config) as kafka:
            success = await kafka.send_message(
                topic=request.topic,
                key=request.key,
                value=request.value,
                headers=request.headers
            )
        
        if success:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "message": "Messaggio pubblicato con successo",
                    "topic": request.topic,
                    "key": request.key,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invio messaggio fallito"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore pubblicazione messaggio Kafka: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/publish-batch", response_model=BatchResult, summary="Pubblica batch messaggi")
async def publish_batch(request: KafkaBatchPublishRequest):
    """
    Pubblica un batch di messaggi su topic Kafka.
    
    Ogni messaggio deve avere struttura: {"key": "...", "value": {...}}
    """
    try:
        # Valida formato messaggi
        messages = []
        for idx, msg in enumerate(request.messages):
            if 'key' not in msg or 'value' not in msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Messaggio {idx}: deve contenere 'key' e 'value'"
                )
            messages.append((msg['key'], msg['value']))
        
        # Carica configurazione
        conn_config = get_kafka_connection_config(request.connection_name)
        producer_config = KafkaProducerConfig()
        
        # Pubblica batch con retry
        async with KafkaService(conn_config, producer_config) as kafka:
            result = await kafka.send_batch_with_retry(
                topic=request.topic,
                messages=messages,
                batch_size=request.batch_size,
                max_retries=request.max_retries
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore pubblicazione batch Kafka: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/health", response_model=KafkaHealthStatus, summary="Health check Kafka")
async def kafka_health(connection_name: str = "default"):
    """
    Verifica health status di una connessione Kafka.
    """
    try:
        conn_config = get_kafka_connection_config(connection_name)
        producer_config = KafkaProducerConfig()
        
        async with KafkaService(conn_config, producer_config) as kafka:
            health_status = await kafka.health_check()
        
        return health_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore health check Kafka: {e}")
        return KafkaHealthStatus(
            connected=False,
            error=str(e),
            last_check_timestamp=datetime.utcnow()
        )


@router.get("/metrics", response_model=KafkaMetrics, summary="Metriche producer Kafka corrente")
async def get_kafka_metrics(connection_name: str = "default"):
    """
    Ottiene le metriche del producer Kafka corrente (messaggi inviati, latenza, ecc.).
    
    Nota: Le metriche sono per sessione producer. Per metriche persistenti e aggregate,
    usare /metrics/summary o /metrics/hourly.
    """
    try:
        conn_config = get_kafka_connection_config(connection_name)
        producer_config = KafkaProducerConfig()
        
        async with KafkaService(conn_config, producer_config) as kafka:
            metrics = kafka.get_metrics()
        
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore recupero metriche Kafka: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/metrics/summary", summary="Riepilogo metriche aggregate")
async def get_metrics_summary(period: str = "today"):
    """
    Ottiene riepilogo metriche aggregate per periodo.
    
    Args:
        period: Periodo di aggregazione (today, last_7_days, last_30_days, all)
    
    Returns:
        Metriche aggregate con breakdown per topic ed errori recenti
    """
    try:
        from app.services.kafka_metrics_service import get_kafka_metrics_service
        
        metrics_service = get_kafka_metrics_service()
        summary = metrics_service.get_summary(period)
        
        return summary.model_dump(mode='json')
        
    except Exception as e:
        logger.error(f"Errore recupero summary metriche: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/metrics/hourly", summary="Statistiche metriche orarie")
async def get_hourly_metrics(hours: int = 24):
    """
    Ottiene statistiche aggregate per ora (ultime N ore).
    
    Args:
        hours: Numero di ore da analizzare (default: 24)
    
    Returns:
        Lista statistiche per ora con messaggi inviati, latenza, success rate
    """
    try:
        from app.services.kafka_metrics_service import get_kafka_metrics_service
        
        if hours < 1 or hours > 168:  # Max 1 settimana
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="hours deve essere tra 1 e 168 (1 settimana)"
            )
        
        metrics_service = get_kafka_metrics_service()
        hourly_stats = metrics_service.get_hourly_stats(hours)
        
        return {"hours": hours, "data": hourly_stats}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore recupero hourly metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/metrics/topic/{topic}", summary="Metriche per topic specifico")
async def get_topic_metrics(topic: str, limit: int = 100):
    """
    Ottiene ultime N metriche per un topic specifico.
    
    Args:
        topic: Nome topic Kafka
        limit: Numero massimo di entry da ritornare (default: 100)
    
    Returns:
        Lista metriche per il topic
    """
    try:
        from app.services.kafka_metrics_service import get_kafka_metrics_service
        
        if limit < 1 or limit > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="limit deve essere tra 1 e 1000"
            )
        
        metrics_service = get_kafka_metrics_service()
        topic_metrics = metrics_service.get_metrics_by_topic(topic, limit)
        
        return {"topic": topic, "count": len(topic_metrics), "metrics": topic_metrics}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore recupero topic metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/metrics/cleanup", summary="Cleanup metriche vecchie")
async def cleanup_old_metrics(days: int = 90):
    """
    Rimuove metriche più vecchie di N giorni.
    
    Args:
        days: Numero di giorni di retention (default: 90)
    
    Returns:
        Conferma operazione
    """
    try:
        from app.services.kafka_metrics_service import get_kafka_metrics_service
        
        if days < 7:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="days deve essere almeno 7 per sicurezza"
            )
        
        metrics_service = get_kafka_metrics_service()
        metrics_service.cleanup_old_metrics(days)
        
        return {
            "success": True,
            "message": f"Cleanup completato: rimossi record più vecchi di {days} giorni"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore cleanup metriche: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
