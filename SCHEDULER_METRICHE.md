# 📊 Scheduler: Metriche Avanzate

## Funzionalità
- Tracciamento storico delle ultime 20 esecuzioni (query, connessione, timestamp, esito, durata, righe, errore)
- Conteggio job di successo e falliti
- Calcolo tempo medio di esecuzione
- Esposizione metriche via API `/api/monitoring/scheduler/status`

## Esempio risposta API
```json
{
  "running": true,
  "active_jobs": 3,
  "scheduled_jobs": 4,
  "last_execution": { ... },
  "jobs": [ ... ],
  "history": [ ... ],
  "success_count": 15,
  "fail_count": 2,
  "avg_duration_sec": 2.13
}
```

## Test automatici
- `test_scheduler_metrics.py`: verifica conteggi e media
- `test_scheduler_api.py`: verifica endpoint API

## Come estendere
- Aumentare profondità storico
- Esportare metriche in CSV/Excel
- Visualizzare metriche in dashboard web
