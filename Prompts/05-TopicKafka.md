Vorrei aggiungere una nuova importante funzionalità, devo estrarre dati dal db Oracle CDG con cadenza giornaliera ed esportare le informazioni estratte su un topic Kafka, in messaggi JSON.
La soluzione deve consentire di effettuare estrazioni anche da db sql server e postgre e deve essere configurabile anche il topic Kafka sul quale iniettare i messaggi.
La soluzione deve essere molto robusta ed in caso di errore devono essere previsti meccanismi di retry.
Devono essere utilizzate soluzione freeware o opensource.
Considera quanto già sviluppato ed il requirements.txt, se possibile riutilizzare qualcosa, ma è necessaria la massima attenzione a non introdurre regressioni.
Serve un layout di progetto ed un piano di implementazione modulare. 
L'approccio deve essere scalabile, in fase iniziale ipotizzo che debbano essere prodotti 20000 messaggi al giorni.
L'integrazione deve essere graduale, ogni step indipendente e testabile.
Rileggi le istruzioni indicate in #file..\prompts\copilot-instructions.md.
Prima di iniziare a scrivere il codice, illustra il piano di attività che vuoi eseguire e chiedi conferma, mi serve il layout di procetto ed un piano di implementazione progressivo diviso in step modulari, fornisci una stima pessimistica dei tempi necessari.

