---
mode: 'agent'
description: 'Project Instructions'
---

Il tuo scopo è creare un'applicazione avente le seguenti funzionalità:

-	Connessione parametrizzata a database di diversa origine: oracle, postgre, sqlserver. Deve esserci la possibilità di passare da una connessione all’altra, la connessione selezionata deve essere evidenziata ed il nome riportato nella caption della finestra principale. 
    La configurazione delle connessioni deve essere persistente, fai riferimento al file connections.json salvato nella route.
	Nella route è contenuto anche il file .env, così da non esporre le credenziali di accesso al db.
-	Esecuzione di query parametrizzate, eventuali parametri richiesti nella query devono poter essere inseriti da UI, il commento accanto al parametro indica se lo stesso è obbligatorio oppure opzionale, tale indicazione deve essere chiara anche per l’utente.

-	Il risultato delle query sarà visualizzato dall’applicazione in una forma tabellare
	Sulla griglia restituita devono essere permessi filtri (non case-sensitive) sul recordset visualizzato, anche su più colonne contemporaneamente e l'ordinamento per colonna
-	Sarà presente una barra di stato, dove saranno indicate informazioni generali, come ad esempio il numero di record estratti per il recordset visualizzato ed il tempo di risposta della query.
	Se i filtri sono attivi sulla barra di stato sarà specificato il numero di record estratti rispetto il totale recordset, il tempo di risposta della query, i filtri attivi e l'ordinamento applicato

-	Deve esserci una funzionalità che consenta di pianificare l'esecuzione di una query
I file prodotti devono essere eliminati con cadenza periodica.
Nel caso specifico devono essere schedulate le seguenti query contenute in #file..\000000-Report NXV\Query:
  - BOSC-NXV--001--Accessi operatori.sql
  - CDG-NXV--005--Dispacci-Gabbie.sql
  - CDG-NXV--006--Mazzetti creati.sql
  - CDG-NXV--008--Esiti.sql
Ad esempio trovi i rispettivi file prodotti in #file..\Export

Valuta come implementare:
Monitoraggio: Controlla regolarmente i log per verificare il corretto funzionamento
Notifiche: Implementa alerting in caso di errori

- Usa le seguenti tecnologie:
- Python=3.11
- HTML/CSS/JS per il frontend
- Tailwind CSS per lo stile

- Non usare cx_oracle perchè è deprecato

- L’aspetto deve essere professionale, l’interfaccia generale coerente. 
- Devono essere sempre inclusi in tutto il codice blocchi try eccept non vuoti, devono contenere almeno un messaggio di errore generico, meglio se descrittivo.
- Ho bisogno di sapere come strutturare directory e file dell'app
- Le dipendenze devono essere inserite in un file denominato requirements.txt. Non devono essere installate dipendenze non necesssarie.
- Non devono essere presenti dipendenze in stato end-of-life o deprecated.
- Devono essere presenti test unitari per le funzionalità principali dell'applicazione
- Deve essere presente un file README.md che spieghi come installare e avviare l'applicazione, con le istruzioni per la configurazione della connessione al database e l'esecuzione delle query.

# Dettagli di implementazione

* usa il workspace corrente
* Usa la convenzione Python PEP 8 per la scrittura del codice
* assicurati che esista un python virtual environment per il progetto nella cartella .venv
* se non esiste il virtual environment, crealo con il comando `python3.11 -m venv .venv`
* prima di effettuare commit e push assicurati che l'applicazione parta correttamente
* alla fine delle modifiche pusha il branch e crea una pull request
* aggiungi un .gitignore per escludere file e cartelle non necessari dal repository
  * includi le seguenti regole:
    * escludi i file di log
    * escludi i file di cache
    * escludi i file temporanei
    * escludi i file di configurazione dell'IDE
    * escludi i file di configurazione del virtual environment
* ometti dalle commit il folder .venv
* utilizza un file README.md per documentare il progetto e le istruzioni di esecuzione
* mantieni un file CHANGELOG.md per tenere traccia delle modifiche e delle versioni del progetto
* usa il conventional commit style per i messaggi delle commit
* usa il server MCP di github per le pull request
* dopo ogni modifica al codice, chiedi conferma per il passo successivo
* Scrivi opportunamente sui log della console in modo da agevolare il debug

Leggi tutti i riferimenti pre-caricati in #file..\
Prima di iniziare a scrivere il codice, illustra il piano di attività che vuoi eseguire e chiedi conferma.