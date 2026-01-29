# Testing e Demo PSTT Tool

## 🧪 Modalità Test

Per testare l'applicazione senza connessioni database reali:

### 1. Configura Test Mode

Crea un file `.env.test`:

```env
# Configurazione di test
DEBUG=true
LOG_LEVEL=DEBUG
PORT=8001

# Credenziali di test (non funzionanti)
DB_USER_A00-CDG-Collaudo=test_user
DB_PASS_A00-CDG-Collaudo=test_pass
DB_USER_A01-BOSC-Collaudo=test_user
DB_PASS_A01-BOSC-Collaudo=test_pass
DB_USER_A03-TT2_UFFICIO=test_user
DB_PASS_A03-TT2_UFFICIO=test_pass
DB_USER_B00-CDG-Certificazione=test_user
DB_PASS_B00-CDG-Certificazione=test_pass
DB_USER_C00-CDG-Produzione=test_user
DB_PASS_C00-CDG-Produzione=test_pass
```

### 2. Test Senza Database

L'applicazione funziona anche senza connessioni database attive:

- ✅ **Interfaccia Web**: Completamente funzionale
- ✅ **Lista Query**: Mostra tutte le query SQL disponibili
- ✅ **Form Parametri**: Genera dinamicamente i campi
- ✅ **Parsing Query**: Estrae parametri correttamente
- ❌ **Esecuzione Query**: Fallirà ma mostrerà errori informativi

### 3. Demo delle Funzionalità

#### Test Parsing Query
```bash
# Testa il parsing di una query specifica
.venv\Scripts\python.exe -c "
from app.services.query_service import QueryService
qs = QueryService()
query = qs.get_query('CDG-INF-001--Visualizza Legenza Eventi-Tracce.sql')
if query:
    print(f'Titolo: {query.title}')
    print(f'Parametri: {len(query.parameters)}')
    for p in query.parameters:
        print(f'  - {p.name}: {p.parameter_type} ({\"obbligatorio\" if p.required else \"opzionale\"})')
else:
    print('Query non trovata')
"
```

#### Test Connessioni (senza esecuzione)
```bash
# Testa il caricamento delle configurazioni
.venv\Scripts\python.exe -c "
from app.services.connection_service import ConnectionService
cs = ConnectionService()
connections = cs.get_connections()
print(f'Connessioni caricate: {len(connections)}')
for name, conn in connections.items():
    print(f'  - {name}: {conn.db_type} ({conn.environment})')
"
```

### 4. Simulazione Completa

Per una demo completa delle funzionalità:

1. **Avvia l'applicazione**:
   ```bash
   $env:PORT=8001; .venv\Scripts\python.exe main.py
   ```

2. **Apri l'interfaccia**: http://127.0.0.1:8001

3. **Test workflow**:
   - Seleziona una connessione dal dropdown
   - Scegli una query dalla lista
   - Compila i parametri nel form
   - Prova ad eseguire (mostrerà errore di connessione ma tutto il resto funziona)

### 5. Errori Previsti in Modalità Demo

Gli seguenti errori sono **normali** in modalità demo:

```
❌ DPY-6005: cannot connect to database
❌ [WinError 10060] Impossibile stabilire la connessione
❌ Timeout di connessione
```

Questi indicano che:
- ✅ Il parsing delle query funziona
- ✅ La sostituzione parametri funziona  
- ✅ La generazione SQL funziona
- ❌ Solo la connessione database fallisce (normale senza database reali)

### 6. Cosa Osservare Durante i Test

#### Console Output
```
✅ Configurazioni caricate
✅ ConnectionService inizializzato  
✅ Query SQL trovate e parsate
✅ Parametri estratti correttamente
✅ Server web attivo
❌ Errori connessione database (previsti)
```

#### Web Interface
- ✅ Interfaccia carica correttamente
- ✅ Lista query popolata
- ✅ Dropdown connessioni funzionante
- ✅ Form parametri generato dinamicamente
- ✅ Gestione errori user-friendly

### 7. Performance Test

L'applicazione dovrebbe:
- Avviarsi in < 5 secondi
- Caricare l'interfaccia in < 2 secondi
- Parsare tutte le query in < 1 secondo
- Rispondere alle API in < 100ms (eccetto esecuzione query)

---

## 🧭 Esecuzione test (pytest)

Qui trovi informazioni pratiche per eseguire la suite di test usando `pytest`, incluse note su `-q` e altri flag utili.

- **`-q` / `--quiet`**: riduce la verbosità dell'output di `pytest`. Mostra un resoconto compatto (puntini e riepilogo compatto) invece dell'elenco dettagliato dei test eseguiti. Utile per run rapidi o CI per avere output più pulito.

Perché si usa:
- In CI o quando vuoi una console pulita con solo il risultato rapido (pass/fail), `-q` rende l'output più leggibile.
- Quando esegui molte centinaia di test, evita output troppo verboso che rende difficile trovare i fallimenti.

Cosa cambia rispetto ad altri flag:
- `-v` / `--verbose` → mostra più informazioni (nomi test, dettagli).
- `-q` → mostra meno informazioni (compatto).
- `-x` / `--exitfirst` → ferma al primo fallimento.
- `-k EXP` → esegue solo i test che corrispondono all'espressione `EXP`.

Raccomandazione pratica:
- Per una verifica rapida della suite: `python -m pytest -q`
- Per debug di fallimenti (vedere quale test fallisce e i dettagli): `python -m pytest -v` oppure esegui senza `-q` per l'output completo.
- Se vuoi solo i nomi dei test falliti e tracebacks completi: esegui `python -m pytest -q` per un run pulito, poi se ci sono fallimenti rilancia con `-vv` o senza `-q` per maggiori dettagli.

Esempi (PowerShell):
```powershell
# Run breve (compatto)
python -m pytest -q

# Run verboso per debug
python -m pytest -v

# Ferma al primo fallimento (combinato con output compatto)
python -m pytest -x -q

# Esegui solo test matching l'espressione
python -m pytest -k "scheduler and not slow"
```

Altri suggerimenti utili:
- Se nel repository sono definiti `markers` (es. `integration`, `manual`), puoi includere o escludere test usando `-m`. Esempio per escludere test manuali/integration in CI:
    ```powershell
    python -m pytest -q -m "not integration and not manual"
    ```
- Se la suite è grande, esegui prima i test unitari (cartella `tests/unit` o con marker) e poi le integrazioni.
- Per troubleshooting dei fallimenti: esegui il singolo test con il percorso completo del file e `-k` o usa `-q` per run pulito seguito da `-vv` per dettagli.

Note CI / pratiche consigliate:
- In pipeline CI, usa `-q` per log più compatti e assicurati di archiviare l'output completo dei test falliti (log) per debug.
- Abilita la memorizzazione delle dipendenze (`pip cache`) e limita i test lunghi sotto marker `slow` o `integration` per le nightly run.


## 🔧 Troubleshooting Demo

### Problema: "Nessuna query trovata"
**Soluzione**: Verifica che i file .sql siano nella directory `Query/`

### Problema: "Errori di encoding"
**Soluzione**: ✅ Risolto automaticamente con multi-encoding support

### Problema: "Porta già in uso"
**Soluzione**: Cambia porta con `$env:PORT=8002`

### Problema: "Import errors"
**Soluzione**: Verifica che il virtual environment sia attivo

---

## 📊 Metriche Demo

Dopo il test, dovresti vedere:

```
📁 Query SQL processate: ~7 file
🔌 Connessioni configurate: 5 database
⚙️  Parametri estratti: ~15-20 totali
📝 Log entries: ~50-100 per sessione
🌐 API endpoints: 15+ attivi
```

Questo dimostra che l'infrastruttura è completa e funzionante!
