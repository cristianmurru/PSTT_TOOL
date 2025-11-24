Vorrei aggiungere una nuova importante funzionalità, leggi la mail allegata tutto il suo contenuto ed il file Excel al suo interno, serve poter configurare range barcode per diversi clienti, per lo stesso cliente possono essere presenti più range in relazione alla commessa oppure se i barcode precedentemente assegnati sono terminati.
I sistemi a valle, se impattati, dovranno ricevere debita informazione per ogni nuovo range inserito per mezzo del canale scelto: mail, web service, file di rendicontazione, etc...
Devono essere utilizzate soluzione freeware o opensource.
Immagino servirà appoggiarsi ad un database, in questo caso preferirei utilizzare sql server perché  ho maggiore familiarità.
Serve un layout di progetto ed un piano di implementazione modulare, così da non introdurre regressioni.
Considera quanto già sviluppato ed il requirements.txt, se possibile riutilizzare qualcosa, ma aggiungi un nuovo modulo denominato Riemann, avente appunto lo scopo di gestire il processo di configurazione range barcode per gare custom.
L'integrazione deve essere graduale, ogni step indipendente e testabile, il nuovo modulo Riemann non deve interferire con il codice esistente.
L'approccio deve essere scalabile
Rileggi le istruzioni indicate in #file..\prompts\copilot-instructions.md.
Prima di iniziare a scrivere il codice, illustra il piano di attività che vuoi eseguire e chiedi conferma, mi serve il layout di procetto ed un piano di implementazione progressivo diviso in step modulari.

