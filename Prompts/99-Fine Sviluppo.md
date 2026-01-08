---
mode: 'agent'
description: 'Project Instructions'
---

Esegui nell'ordine:
- esegui suite completa di test per verificare che non siano state introdotte regressioni, ricorda che abbiamo lavorato sul branch feature/R20260107.
- aggiorna changelog in modo coerente con quanto fatto fino ad ora, non mettere unrealeased, ma aggiungi in calce la data di oggi e tutte le modifiche applicate sul branch corrente e non ancora committate.
- Se opportuno aggiorna readme in modo coerente rispetto i contenuti già presenti
- Crea in setup un documento con la stessa struttura di Update R20251219.md (cambia il nome utilizzando con la data odierna), finalizzato alla distribuzione degli aggiornamenti sulle macchine di collaudo e produzione. 
  Considera che in produzione e collaudo l'applicazione è installata come servizio windows e che per limiti di rete l'allineamento del codice sorgente deve essere fatto dall'operatore manualmente sovrascrivendo i file necessari, 
  ad eccezione dei file connections.json e .env per i quali deve essere descritta la modifica da applicare, se necessarie modifiche ovviamente.
- procedi con add, commit, push e dammi testo per PR
- attendi che io abbia eseguito PR, successivamente alla mia conferma allinea branch master locale ed elimina branch remoto e locale feature/R20260107 in modo che possa iniziare nuovi sviluppi su nuovo branch
- crea nuovo branch locale feature/R20260109