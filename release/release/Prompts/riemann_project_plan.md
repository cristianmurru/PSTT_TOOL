# Modulo Riemann – Gestione Configurazione Range Barcode per Gare Custom

## Obiettivo
Gestire la configurazione, assegnazione e notifica di range barcode per diversi clienti e commesse, con integrazione graduale e scalabile, senza impattare il codice esistente.

---

## Vantaggi dell'approccio proposto
- **Modularità**: ogni componente (modelli, servizi, API, integrazioni) è separato e testabile singolarmente, riducendo il rischio di regressioni.
- **Scalabilità**: architettura pensata per gestire facilmente nuovi clienti, commesse, sistemi a valle e canali di notifica.
- **Integrazione graduale**: il modulo Riemann può essere attivato per step (solo API, solo notifiche, solo UI) senza impattare i flussi esistenti.
- **Manutenibilità**: codice organizzato e documentato, facile da estendere e aggiornare.
- **Riutilizzo**: sfrutta tecnologie e configurazioni già presenti (es. FastAPI, SMTP, SQL Server), riducendo tempi e costi di sviluppo.
- **Soluzioni opensource/freeware**: nessun vincolo di licenza, costi contenuti e massima flessibilità.
- **Testabilità**: ogni step prevede test unitari e di integrazione, facilitando la validazione e la qualità.
- **Sicurezza**: separazione dei dati e delle logiche, gestione permessi e logging delle operazioni.

---

## Layout di Progetto

```
app/
  core/
  models/
  services/
  api/
  templates/
  static/
  ...
  riemann/                # <--- Nuovo modulo dedicato
    __init__.py
    models.py             # ORM: Range, Cliente, Commesse, Log, etc.
    services.py           # Logica di business: creazione, validazione, notifica
    api.py                # Endpoints REST per gestione range (CRUD, notifiche)
    tasks.py              # Eventuali job async/notifiche
    integrations/
      mail.py             # Invio mail (usando SMTP configurato)
      ws.py               # Integrazione web service (stub, estendibile)
      file.py             # Generazione file rendicontazione
    tests/
      test_models.py
      test_services.py
      test_api.py
      test_integrations.py
...
requirements.txt          # Aggiornato con pacchetti SQL Server, mail, etc.
```

---

## Piano di Implementazione Progressivo

| Step | Attività | Output | Giorni stimati | Descrizione |
|------|----------|--------|---------------|-------------|
| 1 | Analisi & Setup Database | Schema SQL Server, script migrazione | 3 | Definizione delle tabelle necessarie (Range, Cliente, Commesse, Log, Sistemi a valle, Notifiche), progettazione relazioni e creazione script di migrazione. Configurazione connessione SQL Server e verifica accessi. |
| 2 | Modello Dati & ORM | models.py, test_models.py | 3 | Implementazione dei modelli ORM con SQLAlchemy per tutte le entità principali. Scrittura di test unitari per validare la corretta mappatura e integrità dei dati. |
| 3 | Logica di Business | services.py, test_services.py | 5 | Sviluppo delle funzioni di creazione, aggiornamento, validazione e associazione dei range barcode a commesse/clienti. Gestione regole di business (es. sovrapposizioni, esaurimento range, logging). Test unitari sui servizi. |
| 4 | API RESTful | api.py, test_api.py, OpenAPI | 5 | Creazione degli endpoint REST per CRUD su range, clienti, commesse e per trigger notifiche. Documentazione automatica OpenAPI. Test di integrazione sugli endpoint. |
| 5 | Integrazioni Notifica | mail.py, ws.py, file.py, test_integrations.py | 5 | Implementazione moduli per invio notifiche via mail (SMTP), web service (stub REST), e generazione file di rendicontazione (CSV/XLSX). Test di integrazione per ogni canale. |
| 6 | UI & Template (opzionale) | template HTML, integrazione frontend | 5 | Sviluppo template HTML e componenti frontend per la gestione visuale dei range barcode. Integrazione graduale con l’interfaccia esistente, mantenendo separazione dei flussi. |
| 7 | Test & Validazione | test end-to-end, checklist regressione | 3 | Esecuzione di test end-to-end su tutti i flussi principali, compilazione checklist di regressione e validazione finale del modulo. |
| 8 | Deploy & Attivazione | rilascio graduale, monitoraggio | 2 | Deploy del modulo in ambiente di test, attivazione step-by-step (API, notifiche, UI), monitoraggio e raccolta feedback. |

**Totale stimato:** 31 giorni lavorativi

---

## Tecnologie & Requisiti
- **Database:** SQL Server (pyodbc/sqlalchemy)
- **Mail:** SMTP (configurazione esistente)
- **Web Service/File:** Python standard + opensource (requests, pandas, openpyxl)
- **Framework:** FastAPI
- **Test:** pytest
- **Frontend:** Tailwind CSS, Jinja2 (se serve UI)

---

## Prossimi Passi
1. Conferma layout e piano.
2. Dettaglio schema DB e modelli.
3. Avvio implementazione step 1.

---


