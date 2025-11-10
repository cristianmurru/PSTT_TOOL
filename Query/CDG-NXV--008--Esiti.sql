WITH latest_tracks AS 
(
  SELECT barcode, MAX(trkdate) AS max_trkdate
  FROM starown.mailpiece_tracks
  WHERE msgtype = 'B4'
    and trkdate >=  to_date(trunc(sysdate-1))
    AND trkdate < to_date(trunc(sysdate-0))
  GROUP BY barcode
)

select /*+ parallel (mt,16) */ 
    mt.track_office as FRAZIONARIO, 
    poa.officename as "NOME_FRAZIONARIO",
    poa.provshort as PROVINCIA,
    poa.regname as REGIONE, 
    trunc(mt.trkdate) as DATA ,
    CASE mt.areadest
        WHEN 'AS' THEN 'MANUALE'
        WHEN 'TP' THEN 'PALMARE'
        WHEN 'RT' THEN 'RT'
        ELSE 'NON VALORIZZATO'
    END AS "TIPO RECAPITO",
    mt.causal||' - '||pc.causalname as PRODOTTO,
    bt.dscop as "UTENZA PTL",
    mt.operator,
    mt.caunotif||' - '||pca.descrizione as "TIPO ESITO", 
    count(*) as TOTALE
from starown.mailpiece_tracks mt
    left join starown.bundle_tracks bt on (mt.bt_bundbarcode = bt.bundbarcode and bt.msgtype = 'BE')
    left join starown.po_offices_anag poa on (mt.track_office = poa.officeid)
    left join starown.po_causals pc on (mt.causal = pc.causal)
    left join starown.po_causali pca on (pca.caunotif = mt.caunotif)
    inner JOIN latest_tracks lt ON mt.barcode = lt.barcode AND mt.trkdate = lt.max_trkdate
  where poa.tipo_ufficio = 'NXV' and poa.last_effective > trunc(sysdate)
  and mt.msgtype = 'B4'
  and mt.trkdate >=  to_date(trunc(sysdate-1))
  AND mt.trkdate < to_date(trunc(sysdate-0))
  and (mt.areadest != ('RT') or mt.areadest is null or (mt.areadest = ('RT') and mt.operator = '888'))
 group by 
 mt.track_office, 
 poa.officename,
 poa.provshort,
 poa.regname, 
 trunc(mt.trkdate),
 CASE mt.areadest
        WHEN 'AS' THEN 'MANUALE'
        WHEN 'TP' THEN 'PALMARE'
        WHEN 'RT' THEN 'RT'
        ELSE 'NON VALORIZZATO'
    END,
 mt.causal||' - '||pc.causalname,
 bt.dscop,
 mt.operator,
 mt.caunotif||' - '||pca.descrizione
 