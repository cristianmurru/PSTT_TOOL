Obiettivo: Integrare la gestione utenti nell'applicazione esistente (Python + Java + HTML) che esegue query e procedure su SQL Server, Oracle e PostgreSQL, con funzionalità di scheduling.
Requisiti funzionali:

Autenticazione basata su dominio Active Directory (max 100 utenti).
Due ruoli: Amministratore (accesso completo) e Standard (funzionalità limitate).
Possibilità di associare a ciascun utente un set di query disponibili.

Vincoli tecnici:

Utilizzare soluzioni freeware o open source.
Le query attualmente risiedono nella cartella Query/ ? serve un meccanismo per mappare query ? utenti.

Aspettative di progetto:

Layout architetturale chiaro.
Piano di implementazione modulare per evitare regressioni.
Aggiornamento della suite di test in parallelo allo sviluppo.

Contesto:

Allegati: README.md, requirements.txt, struttura cartelle.
Tecnologie già in uso: FastAPI, APScheduler, SQLAlchemy, ecc.

Richiesta:

Fornisci un piano dettagliato con:

Architettura proposta (componenti, flussi).
Moduli da implementare (autenticazione, autorizzazione, gestione query per utente).
Strumenti open source consigliati.
Strategia per test e prevenzione regressioni.
Il piano deve includere diagrammi (es. flusso autenticazione, schema DB utenti) e milestone con stima effort.