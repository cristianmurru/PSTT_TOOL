---
mode: 'agent'
description: 'Project Instructions'
---

Il tuo scopo è creare un'applicazione avente le seguenti funzionalità:

-	Connessione parametrizzata a database di diversa origine: oracle, postgre, sqlserver. Deve esserci la possibilità di passare da una connessione all’altra, la connessione selezionata deve essere evidenziata ed il nome riportato nella caption della finestra principale. Si deve poter definire una connessione predefinita.
-	Esecuzione di query parametrizzate, eventuali parametri richiesti nella query devono poter essere inseriti da UI, il commento accanto al parametro indica se lo stesso è obbligatorio oppure opzionale, tale indicazione deve essere chiara anche per l’utente.

Il risultato delle query sarà visualizzato dall’applicazione.
Sarà presente una barra di stato, dove saranno indicate informazioni generali, come ad esempio il numero di record estratti per il recordset visualizzato ed il tempo di risposta della query.
Devono essere permessi filtri (non case-sensitive) sul recordset visualizzato, anche su più colonne contemporaneamente.
Se i filtri sono attivi sulla barra di stato sarà specificato il numero di record estratti rispetto il totale recordset, il tempo di risposta della query, i filtri attivi.

-	Deve esserci una funzionalità che consenta di pianificare l'esecuzione di una query
I file prodotti devono essere eliminati con cadenza periodica.
Nel caso specifico devono essere schedulate le seguenti query contenute in #file..\000000-Report NXV\Query:
  - BOSC-NXV--001--Accessi operatori.sql
  - CDG-NXV--005--Dispacci-Gabbie.sql
  - CDG-NXV--006--Mazzetti creati.sql
  - CDG-NXV--008--Esiti.sql
Ad esempio trovi i rispettivi file prodotti in #file..\000000-Report NXV\Export

Valuta come implementare:
Monitoraggio: Controlla regolarmente i log per verificare il corretto funzionamento
Notifiche: Implementa alerting in caso di errori

-	Usa le seguenti tecnologie:
- Python>=3.10
- HTML/CSS/JS per il frontend
- Tailwind CSS per lo stile

-	L’aspetto deve essere professionale, l’interfaccia generale coerente. 
-	Devono essere sempre inclusi in tutto il codice blocchi try eccept non vuoti, devono contenere almeno un messaggio di errore generico, meglio se descrittivo.
-	Ho bisogno di sapere come strutturare directory e file dell'app
-	Le dipendenze devono essere inserite in un file denominato requirements.txt. Non devono essere installate dipendenze non necesssarie.
- Non devono essere presenti dipendenze in stato end-of-life o deprecated.
-	Devono essere presenti test unitari per le funzionalità principali dell'applicazione
-	Deve essere presente un file README.md che spieghi come installare e avviare l'applicazione, con le istruzioni per la configurazione della connessione al database e l'esecuzione delle query.