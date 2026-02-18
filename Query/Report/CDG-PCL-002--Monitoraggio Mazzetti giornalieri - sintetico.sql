--Monitoraggio PCL richiedente Grisolia Alfonso-Piumelli Gianfranco, data attivazione Febbraio 2026

SELECT 
track_office AS frazionario
, bundtype
, case when
    SUBSTR(BUNDBARCODE, 10, 1) NOT IN ('7', '8') 
    then 'TT_OLD' 
    else 'TT2' 
  end AP_NAME
, COUNT(*) AS totale
FROM starown.bundle_tracks
WHERE MSGTYPE IN ('B1', 'B7')
AND trkdate >=  trunc(sysdate) -7
AND trkdate < trunc(sysdate)
GROUP BY 
track_office
, bundtype
, case when
    SUBSTR(BUNDBARCODE, 10, 1) NOT IN ('7', '8') 
    then 'TT_OLD' 
    else 'TT2' 
  end
order by 1,2,3