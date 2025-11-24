# 📅 Scheduler Export Automatico PSTT Tool

## Funzionalità

- **Scheduling automatico** delle 4 query certificate ogni giorno alle 6:00
- **Export Excel** dei risultati, compressi in formato `.xlsx.gz`
- **Pulizia automatica** dei file export più vecchi di 30 giorni
- **Logging dettagliato** di tutte le operazioni
- **Gestione errori** robusta

---

## Query certificate schedulate

- BOSC-NXV-001--Accessi operatori.sql
- CDG-NXV-005--Dispacci-Gabbie.sql
- CDG-NXV-006--Mazzetti creati.sql
- CDG-NXV-008--Esiti.sql

---

## Dettagli implementativi

### 1. APScheduler
- Utilizzo di `AsyncIOScheduler` per job asincroni
- Schedulazione con `CronTrigger` (giornaliero, ore 6:00 per export, ore 7:00 per pulizia)

### 2. Export automatico
- Esecuzione query tramite `QueryService` con connessione di default
- Salvataggio risultati in Excel (`pandas.DataFrame.to_excel`)
- Compressione file Excel in gzip (`.xlsx.gz`)
- Naming convention: `{query_name}_{YYYY-MM-DD}.xlsx.gz`
- Directory export configurabile (`settings.export_dir`)

### 3. Pulizia automatica
- Job giornaliero alle 7:00
- Eliminazione file `.gz` più vecchi di 30 giorni
- Logging di ogni file eliminato

### 4. Logging e error handling
- Log dettagliati per ogni step: avvio job, export, compressione, pulizia, errori
- Errori gestiti e notificati su log

---

## Esempio di log
```
[SCHEDULER] Avvio export automatico per BOSC-NXV-001--Accessi operatori.sql
[SCHEDULER] Export completato: .../BOSC-NXV-001--Accessi operatori_2025-08-14.xlsx.gz
[SCHEDULER] Avvio pulizia file export > 30 giorni
[SCHEDULER] File eliminato: .../BOSC-NXV-001--Accessi operatori_2025-07-10.xlsx.gz
```

---

## Dipendenze
- `apscheduler`
- `pandas`
- `gzip` (standard library)

---

## Configurazione
- Directory export: configurabile in `settings.export_dir`
- Connessione di default: configurabile in `settings.default_connection`

---

## Estensioni future
- Notifiche email/log in caso di errori
- Scheduling configurabile da UI
- Export anche in CSV
- Monitoraggio stato job da API

---

## Test e validazione
- Verifica generazione file `.xlsx.gz` ogni giorno
- Controllo pulizia automatica file vecchi
- Validazione log e gestione errori

---

**Pronto per ambienti di produzione!**
