-- Report ristampe LDV post rerouting | Richiesta PCL Foroni del 15122025
 
select codice,frazionario,data_creazione  
from t_tt2_link_stampe
where data_creazione BETWEEN '2025-12-15T00:00' and '2025-12-16T00:00'
and path_blob_storage like '%stampe/rerouting/%';
 