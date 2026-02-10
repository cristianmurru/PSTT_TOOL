define BARCODE_LIST = '386342847828' -- Lista barcode separati da virgola, newline CR+LF oppure già formattati con apici e virgola (max 1000)

alter session set nls_date_format = 'DD-MM-YYYY HH24:MI:SS';
alter session set nls_timestamp_format = 'DD-MM-YYYY HH24:MI:SS';

WITH RsPrimoEvento as
(
SELECT T.BARCODE, min(t.trkdate) Data_Primo_Evento
FROM starown.mailpiece_tracks t
WHERE 1=1
AND T.BARCODE in (&BARCODE_LIST)
GROUP BY t.barcode
)
, RsPrimoRecapito as
(
SELECT t.barcode,  min(t.trkdate) Data_Primo_Recapito
FROM RsPrimoEvento rs
INNER
JOIN starown.mailpiece_tracks t on t.barcode=rs.barcode
WHERE t.msgtype in ('BE','B3','B4','B5')
and t.caunotif not in ('PT44') --recapito non tentato
GROUP BY t.barcode
)
, RsUltimoRecapito as
(
SELECT t.barcode, max(t.trkdate) Data_Ultimo_Recapito
FROM RsPrimoEvento rs
INNER
JOIN starown.mailpiece_tracks t on t.barcode=rs.barcode
LEFT
JOIN STAROWN.mt_flags MF ON T.mtf_mtfid = mf.mtfid
WHERE t.msgtype in ('BE','B3','B4','B5','M2')
and t.caunotif not in ('PT44') --recapito non tentato
and mf.back_to_sender=0
GROUP BY t.barcode
)
, RsOMP as
(
SELECT t.barcode, min(t.trkdate) Data_OMP
FROM RsPrimoEvento rs
INNER
JOIN starown.mailpiece_tracks t on t.barcode=rs.barcode
WHERE ((t.msgtype='M2') OR (t.msgtype='O2' AND t.canale='OMP'))
GROUP BY t.barcode
)
,RsUltimoEvento as
(
SELECT t.barcode, max(t.trkdate) Data_Ultimo_Evento
FROM RsPrimoEvento rs
INNER
JOIN starown.mailpiece_tracks t on t.barcode=rs.barcode
GROUP BY t.barcode

)

SELECT pe.barcode, to_char(pe.data_primo_evento,'dd-mm-yyyy hh24:mi:ss') "DATA PRIMO EVENTO", omin.officeid "ID UFFICIO PRIMO EVENTO", omin.officename "NOME UFFICIO PRIMO EVENTO", tmin.msgtype "COD ESITO PRIMO EVENTO", mtmin.msgdescr "DESC ESITO PRIMO EVENTO"
  , to_char(pr.data_primo_recapito,'dd-mm-yyyy hh24:mi:ss') "DATA PRIMO RECAPITO", orec.officeid "ID UFFICIO PRIMO RECAPITO", orec.officename "NOME UFFICIO PRIMO RECAPITO", trec.msgtype "COD ESITO PRIMO RECAPITO", trec.caunotif "COD CAUSALE", pca.descrizione "DESC CAUSALE"
  , trunc(pr.data_primo_recapito) - trunc(pe.data_primo_evento) "DELTA GG SOLARI"
  , to_char(pomp.Data_OMP,'dd-mm-yyyy hh24:mi:ss') "DATA ESITO OMP", oomp.officeid "ID UFFICIO OMP", oomp.officename "NOME UFFICIO OMP", tomp.msgtype "COD ESITO OMP", mtomp.msgdescr "DESC ESITO OMP"

  , to_char(ur.data_ultimo_recapito ,'dd-mm-yyyy hh24:mi:ss') "DATA ULTIMO RECAPITO"
  , ourec.officeid "ID UFFICIO ULTIMO RECAPITO", ourec.officename"NOME UFFICIO ULTIMO RECAPITO", turec.msgtype "COD ESITO ULTIMO RECAPITO", mturec.msgdescr "DESC ESITO ULTIMO RECAPITO"
  , turec.caunotif "COD CAUSALE", pcau.descrizione "DESC CAUSALE"

  , to_char(ue.Data_Ultimo_Evento,'dd-mm-yyyy hh24:mi:ss') "DATA ULTIMO EVENTO", omax.officeid "ID UFFICIO ULTIMO EVENTO", omax.officename"NOME UFFICIO ULTIMO EVENTO"
  , tmax.office_other "OFFICE_OTH ULTIMO EVENTO", oomax.officename "OFFICE_OTH ULTIMO EVENTO"
  , tmax.msgtype "COD ESITO ULTIMO EVENTO", mtmax.msgdescr "DESC ESITO ULTIMO EVENTO"

  --, tmax.caunotif "COD CAUSALE", pcaue.descrizione "DESC CAUSALE"
  , mf.back_to_sender

FROM RsPrimoEvento PE
LEFT
JOIN starown.mailpiece_tracks tmin on tmin.barcode=pe.barcode and tmin.trkdate=pe.data_primo_evento and tmin.msgtype<>'NF'
LEFT
JOIN STAROWN.msgtypes mtmin on tmin.msgtype=mtmin.msgtype
LEFT
JOIN STAROWN.po_offices_anag omin on tmin.track_office=omin.officeid

LEFT
JOIN RsPrimoRecapito PR on PE.barcode=PR.barcode
LEFT
JOIN starown.mailpiece_tracks trec on trec.barcode=pr.barcode and trec.trkdate=pr.Data_Primo_Recapito and trec.msgtype<>'MV'
LEFT
JOIN STAROWN.msgtypes mtrec on trec.msgtype=mtrec.msgtype
LEFT
JOIN STAROWN.po_offices_anag orec on trec.track_office=orec.officeid
LEFT
JOIN starown.po_causali pca on pca.caunotif = trec.caunotif

LEFT
JOIN RsOMP pomp on PE.barcode=pomp.barcode
LEFT
JOIN starown.mailpiece_tracks tomp on tomp.barcode=pomp.barcode and tomp.trkdate=pomp.Data_OMP
LEFT
JOIN STAROWN.msgtypes mtomp on tomp.msgtype=mtomp.msgtype
LEFT
JOIN STAROWN.po_offices_anag oomp on tomp.track_office=oomp.officeid

LEFT
JOIN RsUltimoRecapito UR on PE.barcode=UR.barcode
LEFT
JOIN starown.mailpiece_tracks turec on turec.barcode=ur.barcode and turec.trkdate=ur.data_ultimo_recapito  and turec.msgtype<>'MV'
LEFT
JOIN STAROWN.msgtypes mturec on turec.msgtype=mturec.msgtype
LEFT
JOIN STAROWN.po_offices_anag ourec on turec.track_office=ourec.officeid
LEFT
JOIN starown.po_causali pcau on pcau.caunotif = turec.caunotif

LEFT
JOIN RsUltimoEvento UE on PE.barcode=UE.barcode
LEFT
JOIN starown.mailpiece_tracks tmax on tmax.barcode=ue.barcode and tmax.trkdate=ue.Data_Ultimo_Evento
LEFT
JOIN STAROWN.msgtypes mtmax on tmax.msgtype=mtmax.msgtype
LEFT
JOIN STAROWN.po_offices_anag omax on tmax.track_office=omax.officeid
LEFT
JOIN STAROWN.po_offices_anag oomax on tmax.office_other=oOmax.officeid
LEFT
JOIN STAROWN.mt_flags MF ON tmax.mtf_mtfid = mf.mtfid
LEFT
JOIN starown.po_causali pcaue on pcaue.caunotif = tmax.caunotif
--where 1=1
--and trec.msgtype not in ('MV')
--and turec.msgtype not in ('MV')