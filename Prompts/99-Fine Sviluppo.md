---
mode: 'agent'
description: 'Project Instructions'
---

Esegui nell'ordine:
- Ricorda che abbiamo lavorato sul branch feature/R20260212, valuta se integrare o modificare la suite di test pytest, in conseguenza delle modifiche applicate sul branch.
- esegui suite completa di test per verificare che non siano state introdotte regressioni.
- aggiorna changelog in modo coerente con quanto fatto fino ad ora, non mettere unrealeased, ma aggiungi in ordine decrescente versione, data di oggi, breve descrizione e dettaglio delle modifiche applicate sul branch corrente e non ancora committate. Ogni blocco deve avere versione incrementale,data e breve descrizione ed essendo l'ultimo aggiunto deve stare in cima alla lista.
- Se opportuno aggiorna testing.md in modo coerente rispetto i contenuti già presenti
- Se opportuno aggiorna readme.mf in modo coerente rispetto i contenuti già presenti
- Se opportuno aggiorna troubleshooting.md in modo coerente rispetto i contenuti già presenti, si tratta di un documento manutenuto ad hoc per i colleghi che hanno la responsabilità del presidio e dell'esercizio, non indicare in questo documento problemi fixati, che per altro sono già indicati in changelog.
- Crea in setup un documento con la stessa struttura di Update R20251219.md (cambia il nome utilizzando con la data odierna), finalizzato alla distribuzione degli aggiornamenti sulle macchine di collaudo e produzione. 
  Considera che in produzione e collaudo l'applicazione è installata come servizio windows e che per limiti di rete l'allineamento del codice sorgente deve essere fatto dall'operatore manualmente sovrascrivendo i file necessari, ad eccezione dei file connections.json e .env per i quali deve essere descritta la modifica da applicare, se necessarie modifiche ovviamente.
- procedi con add, commit, push e dammi testo per PR
- attendi che io abbia eseguito PR, successivamente alla mia conferma allinea branch master locale ed elimina branch remoto e locale feature/R20260212 in modo che possa iniziare nuovi sviluppi su nuovo branch
- crea nuovo branch locale feature/R20260218