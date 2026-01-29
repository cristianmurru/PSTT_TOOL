-- Report ristampe LDV post rerouting | Richiesta PCL Foroni del 15122025

SELECT codice, frazionario, data_creazione
FROM t_tt2_link_stampe
WHERE data_creazione >= (CURRENT_DATE - 1)
  AND data_creazione <  CURRENT_DATE
  AND path_blob_storage LIKE '%stampe/rerouting%'
