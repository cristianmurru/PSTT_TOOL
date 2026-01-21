"""
Modelli Pydantic per configurazione e gestione Kafka
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum


class SecurityProtocol(str, Enum):
    """Protocolli di sicurezza supportati da Kafka"""
    PLAINTEXT = "PLAINTEXT"
    SSL = "SSL"
    SASL_PLAINTEXT = "SASL_PLAINTEXT"
    SASL_SSL = "SASL_SSL"


class SaslMechanism(str, Enum):
    """Meccanismi SASL supportati"""
    PLAIN = "PLAIN"
    SCRAM_SHA_256 = "SCRAM-SHA-256"
    SCRAM_SHA_512 = "SCRAM-SHA-512"
    GSSAPI = "GSSAPI"
    OAUTHBEARER = "OAUTHBEARER"


class CompressionType(str, Enum):
    """Tipi di compressione supportati"""
    NONE = "none"
    GZIP = "gzip"
    SNAPPY = "snappy"
    LZ4 = "lz4"
    ZSTD = "zstd"


class KafkaConnectionConfig(BaseModel):
    """Configurazione connessione Kafka"""
    bootstrap_servers: str = Field(
        ...,
        description="Lista server Kafka (comma-separated): host1:port1,host2:port2"
    )
    security_protocol: SecurityProtocol = Field(
        default=SecurityProtocol.PLAINTEXT,
        description="Protocollo di sicurezza"
    )
    sasl_mechanism: Optional[SaslMechanism] = Field(
        default=None,
        description="Meccanismo SASL (se security_protocol è SASL_*)"
    )
    sasl_username: Optional[str] = Field(
        default=None,
        description="Username SASL"
    )
    sasl_password: Optional[str] = Field(
        default=None,
        description="Password SASL"
    )
    ssl_cafile: Optional[str] = Field(
        default=None,
        description="Path al file CA certificate (PEM)"
    )
    ssl_certfile: Optional[str] = Field(
        default=None,
        description="Path al client certificate (PEM)"
    )
    ssl_keyfile: Optional[str] = Field(
        default=None,
        description="Path alla client private key (PEM)"
    )
    
    @field_validator("bootstrap_servers")
    @classmethod
    def validate_bootstrap_servers(cls, v: str) -> str:
        """Valida formato bootstrap servers"""
        if not v or not v.strip():
            raise ValueError("bootstrap_servers non può essere vuoto")
        # Basic validation: deve contenere almeno un host:port
        servers = [s.strip() for s in v.split(",")]
        for server in servers:
            if ":" not in server:
                raise ValueError(f"Server Kafka malformato: {server}. Formato atteso: host:port")
        return v
    
    def get_bootstrap_servers_list(self) -> List[str]:
        """Restituisce lista di bootstrap servers"""
        return [s.strip() for s in self.bootstrap_servers.split(",")]


class KafkaProducerConfig(BaseModel):
    """Configurazione producer Kafka"""
    compression_type: CompressionType = Field(
        default=CompressionType.SNAPPY,
        description="Tipo di compressione per i messaggi"
    )
    batch_size: int = Field(
        default=16384,
        ge=0,
        description="Batch size in bytes"
    )
    linger_ms: int = Field(
        default=10,
        ge=0,
        description="Tempo di attesa per accumulare batch (ms)"
    )
    max_request_size: int = Field(
        default=1048576,
        ge=1024,
        description="Dimensione massima richiesta in bytes (default: 1MB)"
    )
    request_timeout_ms: int = Field(
        default=30000,
        ge=1000,
        description="Timeout richieste in millisecondi"
    )
    enable_idempotence: bool = Field(
        default=True,
        description="Abilita idempotenza producer (evita duplicati)"
    )
    retry_backoff_ms: int = Field(
        default=100,
        ge=0,
        description="Backoff tra retry in millisecondi"
    )
    max_in_flight_requests: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Max richieste in-flight simultanee"
    )
    acks: str = Field(
        default="all",
        description="Acknowledgment mode: 0, 1, 'all'"
    )
    
    @field_validator("acks")
    @classmethod
    def validate_acks(cls, v: str) -> str:
        """Valida acks mode"""
        valid_values = ["0", "1", "all", "-1"]
        if str(v) not in valid_values:
            raise ValueError(f"acks deve essere uno di: {valid_values}")
        return str(v)


class KafkaExportConfig(BaseModel):
    """Configurazione per export Kafka in scheduling"""
    enabled: bool = Field(
        default=False,
        description="Abilita export verso Kafka"
    )
    topic: str = Field(
        ...,
        min_length=1,
        description="Nome del topic Kafka di destinazione"
    )
    message_key_field: str = Field(
        ...,
        min_length=1,
        description="Campo del risultato query da usare come message key (es: 'barcode')"
    )
    batch_size: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Numero di messaggi per batch"
    )
    include_metadata: bool = Field(
        default=True,
        description="Aggiunge metadata al messaggio (source, timestamp, etc.)"
    )
    custom_headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Header custom da aggiungere ai messaggi Kafka"
    )
    
    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        """Valida nome topic"""
        # Kafka topic naming constraints
        if not v or not v.strip():
            raise ValueError("Topic non può essere vuoto")
        invalid_chars = [" ", "\t", "\n", "\r"]
        for char in invalid_chars:
            if char in v:
                raise ValueError(f"Topic contiene caratteri non validi: {repr(char)}")
        return v.strip()


class KafkaMetrics(BaseModel):
    """Metriche di pubblicazione Kafka"""
    messages_sent: int = Field(
        default=0,
        ge=0,
        description="Numero totale messaggi inviati con successo"
    )
    messages_failed: int = Field(
        default=0,
        ge=0,
        description="Numero totale messaggi falliti"
    )
    bytes_sent: int = Field(
        default=0,
        ge=0,
        description="Byte totali inviati"
    )
    avg_latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Latenza media in millisecondi"
    )
    p90_latency_ms: Optional[float] = Field(
        default=None,
        description="Latenza percentile 90"
    )
    p99_latency_ms: Optional[float] = Field(
        default=None,
        description="Latenza percentile 99"
    )
    last_error: Optional[str] = Field(
        default=None,
        description="Ultimo errore riscontrato"
    )
    last_success_timestamp: Optional[datetime] = Field(
        default=None,
        description="Timestamp ultimo invio con successo"
    )
    last_error_timestamp: Optional[datetime] = Field(
        default=None,
        description="Timestamp ultimo errore"
    )
    success_rate: float = Field(
        default=100.0,
        ge=0.0,
        le=100.0,
        description="Percentuale di successo"
    )
    
    def calculate_success_rate(self) -> float:
        """Calcola il success rate"""
        total = self.messages_sent + self.messages_failed
        if total == 0:
            return 100.0
        return (self.messages_sent / total) * 100.0
    
    def update_success_rate(self) -> None:
        """Aggiorna il success rate calcolato"""
        self.success_rate = self.calculate_success_rate()


class BatchResult(BaseModel):
    """Risultato invio batch di messaggi"""
    total: int = Field(
        ...,
        ge=0,
        description="Numero totale messaggi nel batch"
    )
    succeeded: int = Field(
        ...,
        ge=0,
        description="Numero messaggi inviati con successo"
    )
    failed: int = Field(
        ...,
        ge=0,
        description="Numero messaggi falliti"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Lista errori riscontrati"
    )
    duration_ms: Optional[float] = Field(
        default=None,
        description="Durata totale invio batch in ms"
    )
    
    def get_success_rate(self) -> float:
        """Calcola percentuale di successo"""
        if self.total == 0:
            return 100.0
        return (self.succeeded / self.total) * 100.0
    
    def is_successful(self) -> bool:
        """Verifica se il batch è stato completamente inviato con successo"""
        return self.failed == 0 and self.succeeded == self.total


class KafkaHealthStatus(BaseModel):
    """Status health check Kafka"""
    connected: bool = Field(
        ...,
        description="Producer connesso a Kafka"
    )
    broker_count: Optional[int] = Field(
        default=None,
        description="Numero di broker raggiungibili"
    )
    error: Optional[str] = Field(
        default=None,
        description="Messaggio errore se disconnesso"
    )
    last_check_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp ultimo health check"
    )
    latency_ms: Optional[float] = Field(
        default=None,
        description="Latenza connessione in ms"
    )


class KafkaTopicInfo(BaseModel):
    """Informazioni su un topic Kafka"""
    name: str = Field(
        ...,
        description="Nome del topic"
    )
    partitions: int = Field(
        default=1,
        ge=1,
        description="Numero di partizioni"
    )
    replication_factor: Optional[int] = Field(
        default=None,
        description="Fattore di replica"
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Configurazione del topic"
    )
