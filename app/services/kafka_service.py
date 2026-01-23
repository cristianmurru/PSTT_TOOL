"""
Servizio per gestione producer Kafka con connection pooling e retry logic
"""
import json
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, date
from decimal import Decimal
from loguru import logger
from kafka import KafkaProducer
from kafka.errors import (
    KafkaError,
    KafkaTimeoutError,
    NoBrokersAvailable,
    BrokerNotAvailableError,
    NodeNotReadyError,
)

from app.models.kafka import (
    KafkaConnectionConfig,
    KafkaProducerConfig,
    KafkaHealthStatus,
    KafkaMetrics,
    BatchResult,
    SecurityProtocol,
)


# Import lazy del metrics service per evitare circular imports
def _get_metrics_service():
    """Import lazy del metrics service"""
    try:
        from app.services.kafka_metrics_service import get_kafka_metrics_service
        return get_kafka_metrics_service()
    except Exception:
        return None


class KafkaJSONEncoder(json.JSONEncoder):
    """JSON Encoder custom per gestire tipi speciali Oracle/SQL"""

    def default(self, obj):
        """Override default per gestire datetime, date, Decimal"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            # Converti Decimal a float (o string se preferisci precisione esatta)
            return float(obj)
        elif obj is None:
            return None
        # Fallback per altri tipi non serializzabili
        try:
            return super().default(obj)
        except TypeError:
            # Converti a string come ultimo resort
            return str(obj)


class KafkaService:
    """
    Servizio per gestione producer Kafka
    
    Features:
    - Connection pooling
    - Retry automatico con backoff esponenziale
    - Serializzazione JSON custom
    - Health check e metriche
    - Logging strutturato
    """

    def __init__(
        self,
        connection_config: KafkaConnectionConfig,
        producer_config: KafkaProducerConfig,
        max_retries: int = 3,
        log_payload: bool = False,
    ):
        """
        Inizializza KafkaService
        
        Args:
            connection_config: Configurazione connessione Kafka
            producer_config: Configurazione producer
            max_retries: Numero massimo retry su errore
            log_payload: Se True, logga il payload completo dei messaggi
        """
        self.connection_config = connection_config
        self.producer_config = producer_config
        self.max_retries = max_retries
        self.log_payload = log_payload

        self.producer: Optional[KafkaProducer] = None
        self._is_connected: bool = False
        self._metrics = KafkaMetrics()
        self._last_health_check: Optional[datetime] = None

        logger.info(
            f"[KAFKA] KafkaService inizializzato - "
            f"bootstrap_servers={connection_config.bootstrap_servers}, "
            f"security_protocol={connection_config.security_protocol}"
        )

    async def connect(self) -> bool:
        """
        Stabilisce connessione a Kafka cluster
        
        Returns:
            True se connessione riuscita, False altrimenti
        """
        try:
            logger.info(f"[KAFKA] Connessione a Kafka cluster: {self.connection_config.bootstrap_servers}")

            # Risolvi compressione con fallback se libreria mancante
            compression_value = self.producer_config.compression_type.value
            try:
                from app.models.kafka import CompressionType
                if self.producer_config.compression_type == CompressionType.SNAPPY:
                    try:
                        import snappy  # type: ignore
                    except Exception:
                        logger.warning("[KAFKA] Libreria snappy non trovata: fallback a NONE")
                        compression_value = CompressionType.NONE.value
                elif self.producer_config.compression_type == CompressionType.LZ4:
                    try:
                        import lz4.frame  # type: ignore
                    except Exception:
                        logger.warning("[KAFKA] Libreria lz4 non trovata: fallback a NONE")
                        compression_value = CompressionType.NONE.value
                elif self.producer_config.compression_type == CompressionType.ZSTD:
                    try:
                        import zstandard  # type: ignore
                    except Exception:
                        logger.warning("[KAFKA] Libreria zstandard non trovata: fallback a NONE")
                        compression_value = CompressionType.NONE.value
            except Exception:
                # In caso di problemi imprevisti, usa NONE
                compression_value = "none"

            # Configurazione producer
            producer_kwargs = {
                "bootstrap_servers": self.connection_config.get_bootstrap_servers_list(),
                "value_serializer": lambda v: json.dumps(v, cls=KafkaJSONEncoder).encode("utf-8"),
                "key_serializer": lambda k: str(k).encode("utf-8") if k else None,
                "compression_type": compression_value,
                "batch_size": self.producer_config.batch_size,
                "linger_ms": self.producer_config.linger_ms,
                "max_request_size": self.producer_config.max_request_size,
                "request_timeout_ms": self.producer_config.request_timeout_ms,
                "acks": self.producer_config.acks,
                "retries": self.max_retries,
                "retry_backoff_ms": self.producer_config.retry_backoff_ms,
                "max_in_flight_requests_per_connection": self.producer_config.max_in_flight_requests,
            }

            # Configurazione sicurezza
            if self.connection_config.security_protocol != SecurityProtocol.PLAINTEXT:
                producer_kwargs["security_protocol"] = self.connection_config.security_protocol.value

                # SASL
                if "SASL" in self.connection_config.security_protocol.value:
                    if self.connection_config.sasl_mechanism:
                        producer_kwargs["sasl_mechanism"] = self.connection_config.sasl_mechanism.value
                    if self.connection_config.sasl_username:
                        producer_kwargs["sasl_plain_username"] = self.connection_config.sasl_username
                    if self.connection_config.sasl_password:
                        producer_kwargs["sasl_plain_password"] = self.connection_config.sasl_password

                # SSL
                if "SSL" in self.connection_config.security_protocol.value:
                    if self.connection_config.ssl_cafile:
                        producer_kwargs["ssl_cafile"] = self.connection_config.ssl_cafile
                    if self.connection_config.ssl_certfile:
                        producer_kwargs["ssl_certfile"] = self.connection_config.ssl_certfile
                    if self.connection_config.ssl_keyfile:
                        producer_kwargs["ssl_keyfile"] = self.connection_config.ssl_keyfile

            # Idempotenza: kafka-python-ng non supporta il flag 'enable_idempotence'.
            # Manteniamo configurazioni conservative (es. acks=all) senza passare chiavi non riconosciute.
            # Nota: se in futuro si userà un client che supporta idempotenza, aggiungere mapping qui.
            # (Evitiamo l'errore "Unrecognized configs: {'enable_idempotence': True}")
            if self.producer_config.enable_idempotence:
                # Assicura acks='all' per durabilità; non impostare chiave non supportata.
                producer_kwargs["acks"] = self.producer_config.acks

            # Crea producer (operazione sincrona)
            self.producer = await asyncio.to_thread(KafkaProducer, **producer_kwargs)

            self._is_connected = True
            logger.success("[KAFKA] Connessione stabilita con successo")
            return True

        except NoBrokersAvailable as e:
            logger.error(f"[KAFKA] Nessun broker Kafka disponibile: {e}")
            self._is_connected = False
            return False
        except Exception as e:
            logger.error(f"[KAFKA] Errore connessione Kafka: {e}")
            self._is_connected = False
            return False

    async def send_message(
        self,
        topic: str,
        key: str,
        value: dict,
        headers: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Invia singolo messaggio a Kafka topic
        
        Args:
            topic: Nome topic Kafka
            key: Chiave messaggio (per partitioning)
            value: Payload messaggio (dict, sarà serializzato in JSON)
            headers: Header opzionali del messaggio
            
        Returns:
            True se invio riuscito, False altrimenti
        """
        if not self._is_connected or self.producer is None:
            logger.warning("[KAFKA] Producer non connesso, tentativo connessione...")
            connected = await self.connect()
            if not connected:
                logger.error("[KAFKA] Impossibile connettersi a Kafka")
                self._metrics.messages_failed += 1
                self._metrics.update_success_rate()
                return False

        start_time = datetime.utcnow()

        try:
            # Log payload se abilitato (solo per debug)
            if self.log_payload:
                logger.debug(f"[KAFKA] Invio messaggio - topic={topic}, key={key}, payload={value}")
            else:
                logger.debug(f"[KAFKA] Invio messaggio - topic={topic}, key={key}")

            # Prepara headers se presenti
            kafka_headers = None
            if headers:
                kafka_headers = [(k, v.encode("utf-8")) for k, v in headers.items()]

            # Invia messaggio (asincrono)
            future = await asyncio.to_thread(
                self.producer.send,
                topic,
                key=key,
                value=value,
                headers=kafka_headers,
            )

            # Attendi conferma (con timeout)
            record_metadata = await asyncio.to_thread(
                future.get,
                timeout=self.producer_config.request_timeout_ms / 1000,
            )

            # Calcola latenza
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Aggiorna metriche
            self._metrics.messages_sent += 1
            self._metrics.bytes_sent += len(json.dumps(value, cls=KafkaJSONEncoder).encode("utf-8"))
            self._metrics.last_success_timestamp = datetime.utcnow()

            # Aggiorna latenza media
            if self._metrics.messages_sent == 1:
                self._metrics.avg_latency_ms = latency_ms
            else:
                # Moving average
                self._metrics.avg_latency_ms = (
                    self._metrics.avg_latency_ms * (self._metrics.messages_sent - 1) + latency_ms
                ) / self._metrics.messages_sent

            self._metrics.update_success_rate()

            logger.success(
                f"[KAFKA] Messaggio inviato - topic={topic}, partition={record_metadata.partition}, "
                f"offset={record_metadata.offset}, latency={latency_ms:.2f}ms"
            )

            # Persisti metrica (best effort, non bloccare su errori)
            try:
                metrics_service = _get_metrics_service()
                if metrics_service:
                    bytes_sent = len(json.dumps(value, cls=KafkaJSONEncoder).encode("utf-8"))
                    metrics_service.record_metric(
                        topic=topic,
                        messages_sent=1,
                        messages_failed=0,
                        bytes_sent=bytes_sent,
                        latency_ms=latency_ms,
                        operation_type="single",
                        source="manual"
                    )
            except Exception as me:
                logger.debug(f"[KAFKA] Errore registrazione metrica: {me}")

            return True

        except KafkaTimeoutError as e:
            logger.error(f"[KAFKA] Timeout invio messaggio: {e}")
            self._metrics.messages_failed += 1
            self._metrics.last_error = f"Timeout: {str(e)}"
            self._metrics.last_error_timestamp = datetime.utcnow()
            self._metrics.update_success_rate()
            
            # Persisti metrica errore
            try:
                metrics_service = _get_metrics_service()
                if metrics_service:
                    metrics_service.record_metric(
                        topic=topic,
                        messages_sent=0,
                        messages_failed=1,
                        bytes_sent=0,
                        latency_ms=0,
                        operation_type="single",
                        source="manual",
                        error_message=f"Timeout: {str(e)}"
                    )
            except Exception:
                pass
            
            return False

        except (BrokerNotAvailableError, NodeNotReadyError) as e:
            logger.error(f"[KAFKA] Broker non disponibile: {e}")
            self._metrics.messages_failed += 1
            self._metrics.last_error = f"Broker unavailable: {str(e)}"
            self._metrics.last_error_timestamp = datetime.utcnow()
            self._metrics.update_success_rate()
            self._is_connected = False
            
            # Persisti metrica errore
            try:
                metrics_service = _get_metrics_service()
                if metrics_service:
                    metrics_service.record_metric(
                        topic=topic,
                        messages_sent=0,
                        messages_failed=1,
                        bytes_sent=0,
                        latency_ms=0,
                        operation_type="single",
                        source="manual",
                        error_message=f"Broker unavailable: {str(e)}"
                    )
            except Exception:
                pass
            
            return False

        except KafkaError as e:
            logger.error(f"[KAFKA] Errore Kafka generico: {e}")
            self._metrics.messages_failed += 1
            self._metrics.last_error = str(e)
            self._metrics.last_error_timestamp = datetime.utcnow()
            self._metrics.update_success_rate()
            
            # Persisti metrica errore
            try:
                metrics_service = _get_metrics_service()
                if metrics_service:
                    metrics_service.record_metric(
                        topic=topic,
                        messages_sent=0,
                        messages_failed=1,
                        bytes_sent=0,
                        latency_ms=0,
                        operation_type="single",
                        source="manual",
                        error_message=str(e)
                    )
            except Exception:
                pass
            
            return False

        except Exception as e:
            logger.error(f"[KAFKA] Errore imprevisto invio messaggio: {e}")
            self._metrics.messages_failed += 1
            self._metrics.last_error = f"Unexpected: {str(e)}"
            self._metrics.last_error_timestamp = datetime.utcnow()
            self._metrics.update_success_rate()
            return False

    async def send_batch(
        self,
        topic: str,
        messages: List[Tuple[str, dict]],
        batch_size: int = 100,
        headers: Optional[Dict[str, str]] = None,
    ) -> BatchResult:
        """
        Invia batch di messaggi a Kafka topic con retry automatico
        
        Args:
            topic: Nome topic Kafka
            messages: Lista di tuple (key, value) da inviare
            batch_size: Dimensione chunk per sub-batching (default: 100)
            headers: Header opzionali applicati a tutti i messaggi
            
        Returns:
            BatchResult con statistiche invio batch
        """
        if not messages:
            logger.warning("[KAFKA] Batch vuoto, nessun messaggio da inviare")
            return BatchResult(total=0, succeeded=0, failed=0, duration_ms=0.0)

        start_time = datetime.utcnow()
        total_messages = len(messages)
        succeeded = 0
        failed = 0
        errors = []

        logger.info(f"[KAFKA] Avvio invio batch: {total_messages} messaggi su topic '{topic}'")

        # Verifica connessione
        if not self._is_connected or self.producer is None:
            logger.warning("[KAFKA] Producer non connesso, tentativo connessione...")
            connected = await self.connect()
            if not connected:
                logger.error("[KAFKA] Impossibile connettersi a Kafka per batch")
                return BatchResult(
                    total=total_messages,
                    succeeded=0,
                    failed=total_messages,
                    errors=["Producer non connesso"],
                    duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                )

        # Chunking: dividi batch grande in sub-batch più piccoli
        chunks = self._chunk_messages(messages, batch_size)
        total_chunks = len(chunks)

        logger.debug(f"[KAFKA] Batch diviso in {total_chunks} chunk di max {batch_size} messaggi")

        # Processa ogni chunk
        for chunk_idx, chunk in enumerate(chunks, 1):
            chunk_start = datetime.utcnow()

            try:
                # Invia messaggi del chunk in parallelo (accumula futures)
                futures = []
                for key, value in chunk:
                    try:
                        kafka_headers = None
                        if headers:
                            kafka_headers = [(k, v.encode("utf-8")) for k, v in headers.items()]

                        future = await asyncio.to_thread(
                            self.producer.send,
                            topic,
                            key=key,
                            value=value,
                            headers=kafka_headers,
                        )
                        futures.append((future, key))

                    except Exception as e:
                        logger.error(f"[KAFKA] Errore preparazione messaggio key={key}: {e}")
                        failed += 1
                        errors.append(f"Key {key}: {str(e)}")

                # Attendi completamento tutti i messaggi del chunk
                for future, key in futures:
                    try:
                        # Attendi conferma con timeout
                        await asyncio.to_thread(
                            future.get,
                            timeout=self.producer_config.request_timeout_ms / 1000,
                        )
                        succeeded += 1

                    except KafkaTimeoutError as e:
                        logger.warning(f"[KAFKA] Timeout messaggio key={key}")
                        failed += 1
                        errors.append(f"Timeout key {key}")

                    except Exception as e:
                        logger.error(f"[KAFKA] Errore invio messaggio key={key}: {e}")
                        failed += 1
                        errors.append(f"Key {key}: {str(e)}")

                # Log progresso chunk
                chunk_duration = (datetime.utcnow() - chunk_start).total_seconds() * 1000
                logger.debug(
                    f"[KAFKA] Chunk {chunk_idx}/{total_chunks} completato: "
                    f"{len(chunk)} messaggi in {chunk_duration:.0f}ms"
                )

                # Flush periodico per liberare buffer
                if chunk_idx % 10 == 0 or chunk_idx == total_chunks:
                    await asyncio.to_thread(self.producer.flush)

            except Exception as e:
                logger.error(f"[KAFKA] Errore processing chunk {chunk_idx}: {e}")
                failed += len(chunk)
                errors.append(f"Chunk {chunk_idx}: {str(e)}")

        # Flush finale per assicurare che tutti i messaggi siano stati inviati
        try:
            await asyncio.to_thread(self.producer.flush)
        except Exception as e:
            logger.error(f"[KAFKA] Errore flush finale: {e}")

        # Calcola durata totale
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Aggiorna metriche globali
        self._metrics.messages_sent += succeeded
        self._metrics.messages_failed += failed
        self._metrics.update_success_rate()

        # Calcola throughput
        throughput = (succeeded / duration_ms) * 1000 if duration_ms > 0 else 0

        # Log risultato finale
        success_rate = (succeeded / total_messages) * 100 if total_messages > 0 else 0
        logger.info(
            f"[KAFKA] Batch completato: {succeeded}/{total_messages} inviati con successo "
            f"({success_rate:.1f}%) in {duration_ms:.0f}ms ({throughput:.1f} msg/sec)"
        )

        if failed > 0:
            logger.warning(f"[KAFKA] Messaggi falliti: {failed}, primi errori: {errors[:5]}")

        # Persisti metriche batch (best effort)
        try:
            metrics_service = _get_metrics_service()
            if metrics_service:
                # Stima bytes inviati
                total_bytes = sum(
                    len(json.dumps(value, cls=KafkaJSONEncoder).encode("utf-8"))
                    for _, value in messages[:succeeded]  # Solo messaggi riusciti
                )
                
                metrics_service.record_metric(
                    topic=topic,
                    messages_sent=succeeded,
                    messages_failed=failed,
                    bytes_sent=total_bytes,
                    latency_ms=duration_ms / total_messages if total_messages > 0 else 0,
                    operation_type="batch",
                    source="manual",
                    error_message=errors[0] if errors else None
                )
        except Exception as me:
            logger.debug(f"[KAFKA] Errore registrazione metrica batch: {me}")

        return BatchResult(
            total=total_messages,
            succeeded=succeeded,
            failed=failed,
            errors=errors[:100],  # Limita errori per evitare memory bloat
            duration_ms=duration_ms,
        )

    def _chunk_messages(
        self, messages: List[Tuple[str, dict]], chunk_size: int
    ) -> List[List[Tuple[str, dict]]]:
        """
        Divide lista messaggi in chunk più piccoli
        
        Args:
            messages: Lista completa messaggi
            chunk_size: Dimensione desiderata per ogni chunk
            
        Returns:
            Lista di chunk (ogni chunk è una lista di messaggi)
        """
        chunks = []
        for i in range(0, len(messages), chunk_size):
            chunks.append(messages[i : i + chunk_size])
        return chunks

    async def send_batch_with_retry(
        self,
        topic: str,
        messages: List[Tuple[str, dict]],
        batch_size: int = 100,
        max_retries: int = 3,
        retry_backoff_ms: int = 100,
        headers: Optional[Dict[str, str]] = None,
    ) -> BatchResult:
        """
        Invia batch di messaggi con retry automatico su fallimento
        
        Args:
            topic: Nome topic Kafka
            messages: Lista di tuple (key, value) da inviare
            batch_size: Dimensione chunk per sub-batching
            max_retries: Numero massimo retry su fallimento totale batch
            retry_backoff_ms: Backoff esponenziale base tra retry (ms)
            headers: Header opzionali
            
        Returns:
            BatchResult con statistiche invio batch
        """
        last_result = None
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.debug(f"[KAFKA] Tentativo {attempt}/{max_retries} invio batch")

                result = await self.send_batch(
                    topic=topic,
                    messages=messages,
                    batch_size=batch_size,
                    headers=headers,
                )

                # Se success rate > 95%, considera successo
                if result.get_success_rate() >= 95.0:
                    if attempt > 1:
                        logger.info(
                            f"[KAFKA] Batch inviato con successo dopo {attempt} tentativi"
                        )
                    return result

                # Se non tutti i messaggi sono stati inviati, retry dei falliti
                if result.failed > 0 and attempt < max_retries:
                    logger.warning(
                        f"[KAFKA] Tentativo {attempt} parzialmente fallito: "
                        f"{result.failed}/{result.total} messaggi non inviati, retry..."
                    )
                    last_result = result
                    last_error = f"{result.failed} messaggi falliti"

                    # Backoff esponenziale
                    backoff_time = retry_backoff_ms * (2 ** (attempt - 1)) / 1000
                    await asyncio.sleep(backoff_time)
                else:
                    return result

            except Exception as e:
                logger.error(f"[KAFKA] Errore tentativo {attempt}: {e}")
                last_error = str(e)

                if attempt < max_retries:
                    # Backoff esponenziale
                    backoff_time = retry_backoff_ms * (2 ** (attempt - 1)) / 1000
                    logger.debug(f"[KAFKA] Attesa {backoff_time:.2f}s prima del prossimo tentativo")
                    await asyncio.sleep(backoff_time)

        # Tutti i retry falliti
        logger.error(f"[KAFKA] Batch fallito dopo {max_retries} tentativi: {last_error}")

        if last_result:
            return last_result
        else:
            return BatchResult(
                total=len(messages),
                succeeded=0,
                failed=len(messages),
                errors=[f"Tutti i retry falliti: {last_error}"],
            )

    async def health_check(self) -> KafkaHealthStatus:
        """
        Verifica connettività Kafka cluster
        
        Returns:
            KafkaHealthStatus con dettagli dello status
        """
        start_time = datetime.utcnow()

        try:
            if self.producer is None:
                return KafkaHealthStatus(
                    connected=False,
                    error="Producer non inizializzato",
                    last_check_timestamp=datetime.utcnow(),
                )

            # Verifica bootstrap servers raggiungibili
            # Il producer kafka-python mantiene una connessione ai broker
            # Possiamo verificare lo stato controllando i broker disponibili
            if not self._is_connected:
                # Tentativo reconnessione
                connected = await self.connect()
                if not connected:
                    return KafkaHealthStatus(
                        connected=False,
                        error="Impossibile connettersi ai broker Kafka",
                        last_check_timestamp=datetime.utcnow(),
                    )

            # Calcola latenza health check
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Conta broker disponibili (approssimazione)
            # kafka-python non espone facilmente il numero di broker connessi
            # usiamo il numero di bootstrap servers come proxy
            broker_count = len(self.connection_config.get_bootstrap_servers_list())

            self._last_health_check = datetime.utcnow()

            logger.debug(f"[KAFKA] Health check OK - latency={latency_ms:.2f}ms")

            return KafkaHealthStatus(
                connected=True,
                broker_count=broker_count,
                latency_ms=latency_ms,
                last_check_timestamp=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"[KAFKA] Health check fallito: {e}")
            return KafkaHealthStatus(
                connected=False,
                error=str(e),
                last_check_timestamp=datetime.utcnow(),
            )

    async def close(self) -> None:
        """Chiude connessione producer Kafka"""
        try:
            if self.producer:
                logger.info("[KAFKA] Chiusura connessione producer...")
                await asyncio.to_thread(self.producer.close, timeout=10)
                self.producer = None
                self._is_connected = False
                logger.success("[KAFKA] Connessione chiusa")
        except Exception as e:
            logger.error(f"[KAFKA] Errore chiusura producer: {e}")

    def get_metrics(self) -> KafkaMetrics:
        """
        Ottiene metriche correnti di pubblicazione
        
        Returns:
            KafkaMetrics con statistiche aggiornate
        """
        return self._metrics

    def is_connected(self) -> bool:
        """Verifica se producer è connesso"""
        return self._is_connected

    def reset_metrics(self) -> None:
        """Reset metriche a valori iniziali"""
        logger.info("[KAFKA] Reset metriche Kafka")
        self._metrics = KafkaMetrics()

    async def __aenter__(self):
        """Context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()
