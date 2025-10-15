# 🐛 Troubleshooting PSTT Tool

## Errori Comuni e Soluzioni

### ❌ Errori Driver Database Oracle

#### Problema: `connect() got an unexpected keyword argument 'encoding'`

**Causa**: Il nuovo driver `oracledb` (2.x) non supporta più i parametri `encoding` e `nencoding` che erano utilizzati nel vecchio `cx_Oracle`.

**Soluzione**: ✅ **RISOLTO** - I parametri sono stati rimossi dalla configurazione pool.

```python
# PRIMA (non funzionava):
"connect_args": {
    "encoding": "UTF-8",
    "nencoding": "UTF-8"
}

# DOPO (corretto):
"connect_args": {}
```

---

### ❌ Errori di Connessione Database

#### Problema: Errori di connettività non mostrati sulla console

**Causa**: Il logging degli errori era configurato solo per i file di log.

**Soluzione**: ✅ **RISOLTO** - Aggiunto logging errori sulla console.

```python
# Ora tutti gli errori vengono mostrati sia su console che su file
logger.add(
    sink=lambda msg: print(msg, end=""),
    level="ERROR",  # Sempre mostra errori sulla console
    format="<red>ERROR</red> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <red>{message}</red>",
    colorize=True
)
```

---

### ❌ Errori Porta di Rete

#### Problema: `[Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000)`

**Causa**: La porta 8000 è già in uso da un altro processo.

**Soluzioni**:

1. **Cambia porta temporaneamente**:
   ```bash
   $env:PORT=8001; .venv\Scripts\python.exe main.py
   ```

2. **Configura porta nel file .env**:
   ```env
   PORT=8001
   ```

3. **Trova e termina il processo**:
   ```powershell
   Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
   Stop-Process -Id [PID_DEL_PROCESSO]
   ```

---

### ❌ Errori Import Python

#### Problema: `ModuleNotFoundError: No module named 'app'`

**Causa**: Virtual environment non attivato o path di lavoro scorretto.

**Soluzioni**:

1. **Verifica virtual environment**:
   ```bash
   .venv\Scripts\python.exe --version  # Deve mostrare Python 3.11
   ```

2. **Verifica directory di lavoro**:
   ```bash
   cd C:\app\PSTT_Tool
   ```

3. **Reinstalla dipendenze se necessario**:
   ```bash
   .venv\Scripts\pip.exe install -r requirements.txt
   ```

---

### ❌ Errori Query SQL

#### Problema: Query con parametri Oracle non funzionano

**Diagnostica**: Controlla i log sulla console per dettagli specifici:
- Parametri mancanti
- Sintassi SQL non valida
- Connessione database non disponibile

**Debug**:
```sql
-- Verifica che i parametri siano definiti correttamente
define DATAINIZIO='17/06/2022'   --Obbligatorio
define DATAFINE='17/06/2025'     --Opzionale

-- Verifica che siano utilizzati nella query
WHERE data >= TO_DATE('&DATAINIZIO', 'dd/mm/yyyy')
AND data < TO_DATE('&DATAFINE', 'dd/mm/yyyy')
```

---

### 🔧 Diagnostic Commands

#### Test Configurazione
```bash
.venv\Scripts\python.exe -c "from app.core.config import get_settings; print('OK')"
```

#### Test Connessioni
```bash
.venv\Scripts\python.exe -c "from app.services.connection_service import ConnectionService; cs = ConnectionService(); print(len(cs.get_connections()), 'connessioni caricate')"
```

#### Test Query
```bash
.venv\Scripts\python.exe -c "from app.services.query_service import QueryService; qs = QueryService(); print(len(qs.get_queries()), 'query trovate')"
```

#### Verifica Health Check
```bash
# Con l'applicazione in esecuzione:
Invoke-WebRequest -Uri 'http://127.0.0.1:8001/health' -UseBasicParsing
```

---

### 📋 Log Files

I log sono salvati in `logs/`:
- **`app.log`**: Log generale dell'applicazione
- **`errors.log`**: Solo errori (utile per debug)
- **`scheduler.log`**: Log del sistema di scheduling

#### Visualizza log recenti:
```bash
Get-Content logs\errors.log -Tail 20
```

---

### 🚨 Modalità Debug

Per abilitare logging dettagliato, aggiungi nel file `.env`:

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

Poi riavvia l'applicazione. Vedrai molto più dettaglio sui log.

---

### 📞 Supporto

Se i problemi persistono:

1. ✅ Controlla i log in `logs/errors.log`
2. ✅ Verifica la configurazione in `connections.json` e `.env`
3. ✅ Testa la connettività database con gli endpoint `/api/connections/test`
4. ✅ Usa la modalità debug per maggiori dettagli

Tutti gli errori sono ora visibili sia sulla console che nei file di log per un debugging più efficace.
