"""
Benchmark Script per Kafka Integration
Test throughput e performance del sistema

Usage:
    python tools/kafka_benchmark.py --messages 10000 --topic pstt-benchmark
"""
import asyncio
import time
import argparse
import sys
from datetime import datetime
from typing import List, Tuple
from pathlib import Path

# Aggiungi path per import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.kafka_service import get_kafka_service
from loguru import logger


async def benchmark_single_messages(num_messages: int, topic: str) -> dict:
    """Test invio messaggi singoli"""
    service = get_kafka_service()
    
    logger.info(f"Starting benchmark: {num_messages} single messages to topic '{topic}'")
    
    start_time = time.time()
    succeeded = 0
    failed = 0
    latencies = []
    
    for i in range(num_messages):
        msg_start = time.time()
        
        try:
            await service.send_message(
                topic=topic,
                key=f"bench-single-{i}",
                value={
                    "id": i,
                    "type": "benchmark_single",
                    "data": f"Test message {i}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            succeeded += 1
            latency = (time.time() - msg_start) * 1000  # ms
            latencies.append(latency)
        except Exception as e:
            failed += 1
            logger.error(f"Failed to send message {i}: {e}")
        
        # Progress ogni 1000 messaggi
        if (i + 1) % 1000 == 0:
            logger.info(f"Progress: {i + 1}/{num_messages}")
    
    elapsed = time.time() - start_time
    throughput = num_messages / elapsed if elapsed > 0 else 0
    
    # Calcola statistiche latenza
    latencies.sort()
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p50_latency = latencies[len(latencies) // 2] if latencies else 0
    p90_latency = latencies[int(len(latencies) * 0.9)] if latencies else 0
    p99_latency = latencies[int(len(latencies) * 0.99)] if latencies else 0
    
    return {
        "mode": "single",
        "total_messages": num_messages,
        "succeeded": succeeded,
        "failed": failed,
        "elapsed_seconds": round(elapsed, 2),
        "throughput_msg_sec": round(throughput, 2),
        "latency_avg_ms": round(avg_latency, 2),
        "latency_p50_ms": round(p50_latency, 2),
        "latency_p90_ms": round(p90_latency, 2),
        "latency_p99_ms": round(p99_latency, 2)
    }


async def benchmark_batch_messages(num_messages: int, topic: str, batch_size: int = 100) -> dict:
    """Test invio batch messaggi"""
    service = get_kafka_service()
    
    logger.info(f"Starting benchmark: {num_messages} messages in batches of {batch_size} to topic '{topic}'")
    
    # Prepara tutti i messaggi
    messages: List[Tuple[str, dict]] = [
        (
            f"bench-batch-{i}",
            {
                "id": i,
                "type": "benchmark_batch",
                "data": f"Test message {i}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        for i in range(num_messages)
    ]
    
    start_time = time.time()
    
    # Invia in batch
    result = await service.send_batch(
        topic=topic,
        messages=messages,
        batch_size=batch_size
    )
    
    elapsed = time.time() - start_time
    throughput = num_messages / elapsed if elapsed > 0 else 0
    
    return {
        "mode": "batch",
        "total_messages": num_messages,
        "batch_size": batch_size,
        "succeeded": result.succeeded,
        "failed": result.failed,
        "elapsed_seconds": round(elapsed, 2),
        "throughput_msg_sec": round(throughput, 2),
        "errors": result.errors[:5] if result.errors else []  # Prime 5 errori
    }


async def benchmark_mixed_load(duration_seconds: int, topic: str) -> dict:
    """Test load misto per durata specificata"""
    service = get_kafka_service()
    
    logger.info(f"Starting mixed load test for {duration_seconds} seconds on topic '{topic}'")
    
    start_time = time.time()
    end_time = start_time + duration_seconds
    
    total_sent = 0
    total_failed = 0
    
    msg_counter = 0
    
    while time.time() < end_time:
        try:
            # Alterna single e batch
            if msg_counter % 10 == 0:
                # Batch ogni 10 iterazioni
                batch = [
                    (f"bench-mixed-{msg_counter + i}", {"id": msg_counter + i, "type": "mixed_batch"})
                    for i in range(50)
                ]
                result = await service.send_batch(topic=topic, messages=batch)
                total_sent += result.succeeded
                total_failed += result.failed
                msg_counter += 50
            else:
                # Single message
                await service.send_message(
                    topic=topic,
                    key=f"bench-mixed-{msg_counter}",
                    value={"id": msg_counter, "type": "mixed_single"}
                )
                total_sent += 1
                msg_counter += 1
            
            # Piccolo delay per simulare load realistico
            await asyncio.sleep(0.01)
            
        except Exception as e:
            total_failed += 1
            logger.error(f"Error in mixed load: {e}")
    
    elapsed = time.time() - start_time
    throughput = total_sent / elapsed if elapsed > 0 else 0
    
    return {
        "mode": "mixed_load",
        "duration_seconds": round(elapsed, 2),
        "total_sent": total_sent,
        "total_failed": total_failed,
        "throughput_msg_sec": round(throughput, 2)
    }


def print_results(results: dict):
    """Stampa risultati formattati"""
    print("\n" + "="*60)
    print(f"📊 BENCHMARK RESULTS - {results['mode'].upper()}")
    print("="*60)
    
    for key, value in results.items():
        if key == "mode":
            continue
        
        # Formatta il nome
        label = key.replace("_", " ").title()
        
        # Formatta il valore
        if isinstance(value, (int, float)):
            if key.endswith("_sec") or key.endswith("_seconds"):
                formatted = f"{value:.2f}s"
            elif key.endswith("_ms"):
                formatted = f"{value:.2f}ms"
            elif key.endswith("msg_sec"):
                formatted = f"{value:.0f} msg/sec"
            else:
                formatted = str(value)
        elif isinstance(value, list):
            formatted = f"{len(value)} errors" if value else "None"
        else:
            formatted = str(value)
        
        print(f"  {label}: {formatted}")
    
    print("="*60 + "\n")


async def main():
    parser = argparse.ArgumentParser(description="Kafka Integration Benchmark")
    parser.add_argument("--messages", type=int, default=1000, help="Number of messages to send")
    parser.add_argument("--topic", type=str, default="pstt-benchmark", help="Kafka topic")
    parser.add_argument("--mode", type=str, choices=["single", "batch", "mixed", "all"], 
                       default="batch", help="Benchmark mode")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size (for batch mode)")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds (for mixed mode)")
    
    args = parser.parse_args()
    
    logger.info("="*60)
    logger.info("KAFKA BENCHMARK - PSTT Tool")
    logger.info("="*60)
    logger.info(f"Mode: {args.mode}")
    logger.info(f"Messages: {args.messages}")
    logger.info(f"Topic: {args.topic}")
    logger.info("="*60 + "\n")
    
    results = []
    
    try:
        if args.mode == "single" or args.mode == "all":
            result = await benchmark_single_messages(args.messages, args.topic)
            print_results(result)
            results.append(result)
        
        if args.mode == "batch" or args.mode == "all":
            result = await benchmark_batch_messages(args.messages, args.topic, args.batch_size)
            print_results(result)
            results.append(result)
        
        if args.mode == "mixed" or args.mode == "all":
            result = await benchmark_mixed_load(args.duration, args.topic)
            print_results(result)
            results.append(result)
        
        # Summary
        if len(results) > 1:
            print("\n" + "="*60)
            print("📊 SUMMARY")
            print("="*60)
            for r in results:
                mode = r['mode']
                throughput = r.get('throughput_msg_sec', 0)
                print(f"  {mode.upper()}: {throughput:.0f} msg/sec")
            print("="*60 + "\n")
        
        logger.success("✅ Benchmark completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
