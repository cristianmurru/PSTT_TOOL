Obiettivo: 
Progettare una soluzione per estrarre dati da DB Oracle CDG (e successivamente SQL Server e PostgreSQL) con cadenza giornaliera e pubblicarli su un topic Kafka in formato JSON.

Contesto: 
Considera il requirements.txt, se possibile riutilizzare qualcosa, ma è necessaria la massima attenzione a non introdurre regressioni.
I file allegati ProvaQueryJSon.sql e ProvaFileJSon.Json sono prodotti a titolo di esempio, come base per iniziare l'implementazione, l'analisi per definire la query per l'estrazione del recordset ed il payload json deve ancora essere effettuata.

Vincoli:
Soluzioni freeware o opensource.
Robustezza con meccanismi di retry.
Scalabilità (in fase iniziale l'applicazione dovrà generare almeno 20.000 messaggi/giorno, a tendere i messaggi generati potrebbero essere 200000/giorno).
Integrazione graduale, step modulari e testabili.
Riutilizzare quanto già sviluppato senza introdurre regressioni.

Output atteso:
Un documento con:
Layout del progetto (diagrammi, moduli, flussi).
Piano di implementazione progressivo diviso in step modulari.
Stima pessimistica dei tempi per ogni step.
Istruzioni: Prima di scrivere codice, illustra il piano e chiedi conferma.