# 🕒 Guida Utente: Configurazione Schedulazione Query Automatica

## Dove configurare

La configurazione delle schedulazioni avviene nel file `connections.json` nella sezione `scheduling`.

---

## Struttura della sezione `scheduling`

```json
"scheduling": [
  {
    "query": "BOSC-NXV-001--Accessi operatori.sql",
    "hour": 6,
    "minute": 0,
    "connection": "A01-BOSC-Collaudo"
  },
  {
    "query": "CDG-NXV-005--Dispacci-Gabbie.sql",
    "hour": 6,
    "minute": 10,
    "connection": "A00-CDG-Collaudo"
  }
]
```

### Campi disponibili
- **query**: Nome del file SQL da eseguire (deve essere presente nella cartella Query)
- **hour**: Ora di esecuzione (0-23)
- **minute**: Minuto di esecuzione (0-59)
- **connection**: Nome della connessione/database su cui eseguire la query (come da sezione `connections`)

---

## Esempio completo

```json
"scheduling": [
  {
    "query": "BOSC-NXV-001--Accessi operatori.sql",
    "hour": 6,
    "minute": 0,
    "connection": "A01-BOSC-Collaudo"
  },
  {
    "query": "CDG-NXV-005--Dispacci-Gabbie.sql",
    "hour": 6,
    "minute": 10,
    "connection": "A00-CDG-Collaudo"
  },
  {
    "query": "CDG-NXV-006--Mazzetti creati.sql",
    "hour": 6,
    "minute": 20,
    "connection": "A00-CDG-Collaudo"
  },
  {
    "query": "CDG-NXV-008--Esiti.sql",
    "hour": 6,
    "minute": 30,
    "connection": "A00-CDG-Collaudo"
  }
]
```

---

## Come modificare le schedulazioni
1. Apri il file `connections.json` nella root del progetto.
2. Vai alla sezione `scheduling`.
3. Aggiungi, modifica o elimina i job secondo le tue esigenze.
4. Salva il file e riavvia l'applicazione per applicare le nuove schedulazioni.

---

## Note importanti
- Il nome della query deve corrispondere esattamente al file SQL presente nella cartella `Query`.
- Il nome della connessione deve essere uno di quelli definiti nella sezione `connections`.
- Puoi schedulare più job per lo stesso orario o su database diversi.
- La modifica delle schedulazioni richiede il riavvio dell'applicazione per essere applicata.

---

## Troubleshooting
- Se una query non viene eseguita, verifica che il nome sia corretto e che la connessione sia attiva.
- Controlla i log per eventuali errori di esecuzione o di connessione.

---

**Configurazione flessibile e pronta per ambienti di produzione!**
