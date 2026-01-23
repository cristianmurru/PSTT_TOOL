# Script: Kafka Daily Check
# Descrizione: Verifica quotidiana stato Kafka (health, metriche, errori)
# Uso: .\kafka_daily_check.ps1

param(
    [string]$BaseUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"
$date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Kafka Daily Check - $date" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

try {
    # 1. Health Status
    Write-Host "[1/5] Health Check..." -ForegroundColor Yellow
    $health = Invoke-RestMethod -Uri "$BaseUrl/api/kafka/health" -Method Get
    
    if ($health.connected) {
        Write-Host "  ✅ Kafka Connected" -ForegroundColor Green
        Write-Host "     - Broker Count: $($health.broker_count)" -ForegroundColor Gray
        Write-Host "     - Latency: $($health.latency_ms)ms" -ForegroundColor Gray
        Write-Host "     - Last Check: $($health.last_check)" -ForegroundColor Gray
    } else {
        Write-Host "  ❌ Kafka Disconnected!" -ForegroundColor Red
        Write-Host "     - Error: $($health.error)" -ForegroundColor Red
        exit 1
    }
    Write-Host ""

    # 2. Metriche ultime 24h
    Write-Host "[2/5] Metriche Ultime 24h..." -ForegroundColor Yellow
    $hourly = Invoke-RestMethod -Uri "$BaseUrl/api/kafka/metrics/hourly?hours=24" -Method Get
    
    $totalSent = ($hourly | Measure-Object -Property messages_sent -Sum).Sum
    $totalFailed = ($hourly | Measure-Object -Property messages_failed -Sum).Sum
    $totalMessages = $totalSent + $totalFailed
    
    Write-Host "  📊 Messages Sent: $totalSent" -ForegroundColor Cyan
    if ($totalFailed -gt 0) {
        Write-Host "  ⚠️  Messages Failed: $totalFailed" -ForegroundColor Yellow
    } else {
        Write-Host "  ✅ Messages Failed: 0" -ForegroundColor Green
    }
    Write-Host ""

    # 3. Success Rate & Latency
    Write-Host "[3/5] Success Rate & Latency..." -ForegroundColor Yellow
    $summary = Invoke-RestMethod -Uri "$BaseUrl/api/kafka/metrics/summary" -Method Get
    
    if ($totalMessages -gt 0) {
        $successRate = [math]::Round(($totalSent / $totalMessages) * 100, 2)
        
        if ($successRate -ge 99) {
            Write-Host "  ✅ Success Rate: $successRate%" -ForegroundColor Green
        } elseif ($successRate -ge 95) {
            Write-Host "  ⚠️  Success Rate: $successRate%" -ForegroundColor Yellow
        } else {
            Write-Host "  ❌ Success Rate: $successRate% (CRITICAL!)" -ForegroundColor Red
        }
    } else {
        Write-Host "  ℹ️  No messages sent in last 24h" -ForegroundColor Gray
    }
    
    Write-Host "  ⏱️  Avg Latency: $([math]::Round($summary.avg_latency_ms, 2))ms" -ForegroundColor Cyan
    Write-Host "  ⏱️  P90 Latency: $([math]::Round($summary.p90_latency_ms, 2))ms" -ForegroundColor Cyan
    Write-Host "  ⏱️  P99 Latency: $([math]::Round($summary.p99_latency_ms, 2))ms" -ForegroundColor Cyan
    Write-Host ""

    # 4. Breakdown per Topic
    Write-Host "[4/5] Breakdown per Topic..." -ForegroundColor Yellow
    $topics = Invoke-RestMethod -Uri "$BaseUrl/api/kafka/metrics/topics" -Method Get
    
    if ($topics.Count -gt 0) {
        foreach ($topic in $topics) {
            $topicSuccessRate = if ($topic.total_sent -gt 0) {
                [math]::Round(($topic.total_sent / ($topic.total_sent + $topic.total_failed)) * 100, 2)
            } else { 0 }
            
            Write-Host "  📍 Topic: $($topic.topic_name)" -ForegroundColor Cyan
            Write-Host "     - Sent: $($topic.total_sent)" -ForegroundColor Gray
            Write-Host "     - Failed: $($topic.total_failed)" -ForegroundColor Gray
            Write-Host "     - Success Rate: $topicSuccessRate%" -ForegroundColor Gray
            Write-Host "     - Avg Latency: $([math]::Round($topic.avg_latency_ms, 2))ms" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ℹ️  No topics with activity" -ForegroundColor Gray
    }
    Write-Host ""

    # 5. Errori Recenti
    Write-Host "[5/5] Errori Recenti (ultimi 50 log errors)..." -ForegroundColor Yellow
    
    $errorLogPath = Join-Path (Get-Location) "logs\pstt_errors.log"
    
    if (Test-Path $errorLogPath) {
        $recentErrors = Get-Content $errorLogPath -Tail 50 | Where-Object { $_ -match "kafka" -or $_ -match "Kafka" }
        
        if ($recentErrors) {
            Write-Host "  ⚠️  Trovati $($recentErrors.Count) errori Kafka:" -ForegroundColor Yellow
            $recentErrors | Select-Object -First 5 | ForEach-Object {
                Write-Host "     $_" -ForegroundColor Gray
            }
            if ($recentErrors.Count -gt 5) {
                Write-Host "     ... e altri $($recentErrors.Count - 5) errori" -ForegroundColor Gray
            }
        } else {
            Write-Host "  ✅ Nessun errore Kafka recente" -ForegroundColor Green
        }
    } else {
        Write-Host "  ℹ️  File log errori non trovato: $errorLogPath" -ForegroundColor Gray
    }
    Write-Host ""

    # Summary finale
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host " CHECK COMPLETATO" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Criteri di alert
    if ($totalMessages -gt 0 -and $successRate -lt 95) {
        Write-Host "⚠️  ATTENZIONE: Success rate sotto soglia 95%!" -ForegroundColor Yellow
        Write-Host "   Azione suggerita: Verificare log e KAFKA_RUNBOOK.md" -ForegroundColor Yellow
    }
    
    if ($summary.p99_latency_ms -gt 2000) {
        Write-Host "⚠️  ATTENZIONE: Latency P99 elevata (>2000ms)!" -ForegroundColor Yellow
        Write-Host "   Azione suggerita: Verificare performance tuning in KAFKA_SETUP.md" -ForegroundColor Yellow
    }

} catch {
    Write-Host ""
    Write-Host "❌ ERRORE durante check:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    exit 1
}
