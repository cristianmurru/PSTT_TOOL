Vorrei poter definire in fase di configurazione della schedulazione il nome del file di output. 
Il nome deve poter contenere le seguenti variabili dinamiche:
•	Il nome della query -> {query_name}
•	la data di esecuzione (formato configurabile) -> {YYYY-MM-DD}
•	la data di esecuzione meno un giorno -> {YYYY-MM-DD} -1 
•	un timestamp completo -> {YYYY-MM-DD HH:MM}
Sposta il campo Data Fine al posto dei campi “giorni della settimana”
Inoltre, deve essere configurabile la modalità di condivisione del file generato:
•	esportazione su una directory del file system, con percorso configurabile
•	invio tramite email, con indirizzi configurabili (supportando più destinatari separati da pipe | invece che da punto e virgola ;, per evitare problemi di parsing)
•	Il flag di scelta della modalità di condivisione, deve precedere le text box previste per Directory di esportazione e Destinatari email, a seconda della scelta effettuata devono essere abilitati i rispettivi campi, il default è esportazione su directory. 
•	Aggiungi la possibilità di pianificare l'esecuzione tramite CHRON EXPRESSION. L'utente deve scegliere se utilizzare chron expression o in alternativa l'attuale modalità di pianificazione temporale: giorni della settimana, ora, minuto. Quindi i campi sono abilitati lato UI sulla base della scelta effettuata, mantieni come default la modalità di pianificazione già esistente.
•	Aggiungi tooltip/guida compilazione per i nuovi campi

L’interfaccia front-end deve essere coerente con il resto dell’applicazione. 
I nuovi campi di configurazione devono essere visibili anche se non valorizzati.
________________________________________
Suggerimenti per il codice:

Gestione CRON vs pianificazione classica:

Usa una variabile schedulingMode ('cron' o 'classic') per abilitare/disabilitare i campi corrispondenti nella UI.
Per interpretare CRON, usa librerie come cron-parser (Node.js) o croniter (Python).


UI/UX:

Usa componenti condizionali per mostrare/nascondere i campi in base alla modalità selezionata.