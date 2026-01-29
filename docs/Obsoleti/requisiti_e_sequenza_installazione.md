# Requisiti Hardware e Software

## Requisiti Hardware

- **Memoria RAM**: Minimo 2GB, consigliato 4GB
- **Storage**: Almeno 500MB per installazione base
- **CPU**: Qualsiasi processore moderno (consigliato dual-core o superiore)

## Requisiti Software

- **Sistema Operativo**: Windows 10/11 (64 bit)
- **Python**: Versione 3.11 o superiore
- **Virtual Environment**: Consigliato l'uso di `.venv`
- **Driver Database**:
  - Oracle Instant Client (per connessioni Oracle)
  - PostgreSQL client libraries (per connessioni PostgreSQL)
  - ODBC Driver 18 for SQL Server (per connessioni SQL Server)
- **Pacchetti Python**: Tutti quelli elencati in `requirements.txt`
- **Variabili d'ambiente**: File `.env` con credenziali database

---

# Sequenza Installazione Applicazione

1. **Preparazione Ambiente**
   - Verifica che la macchina soddisfi i requisiti hardware
   - Installa Python 3.11 (https://www.python.org/downloads/)
   - Installa i driver database necessari:
     - [Oracle Instant Client](https://www.oracle.com/database/technologies/instant-client.html)
     - [PostgreSQL Client](https://www.postgresql.org/download/)
     - [ODBC Driver SQL Server](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

2. **Clonazione/Download del Progetto**
   - Scarica o clona la cartella del progetto su una directory locale

3. **Creazione Virtual Environment**
   - Apri PowerShell nella directory del progetto
   - Esegui:
     ```powershell
     python -m venv .venv
     .venv\Scripts\activate
     ```

4. **Installazione Dipendenze Python**
   - Installa i pacchetti richiesti:
     ```powershell
     pip install -r requirements.txt
     ```

5. **Configurazione Variabili d'Ambiente**
   - Crea/modifica il file `.env` con le credenziali reali dei database
   - Segui il formato indicato in README.md

6. **Configurazione Connessioni Database**
   - Modifica il file `connections.json` per configurare le connessioni

7. **Avvio Applicazione**
   - Esegui:
     ```powershell
     python main.py
     ```
   - Accedi all'interfaccia web su [http://localhost:8000](http://localhost:8000)

8. **(Opzionale) Configurazione come Servizio Windows**
   - Crea un file batch `start_pstt.bat`:
     ```batch
     @echo off
     cd /d "C:\percorso\PSTT_Tool"
     .venv\Scripts\activate
     python main.py
     ```
   - Utilizza [NSSM](https://nssm.cc/) o simili per configurare come servizio

---

# Note
- Per troubleshooting e dettagli consultare `README.md` e `TROUBLESHOOTING.md`
- Verificare sempre la corretta installazione dei driver database
- In caso di errori, consultare i file di log nella cartella `logs/`
