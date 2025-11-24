select /*+ PARALLEL (mt,32) */ mt.track_office as FRAZIONARIO,
       	decode(mt.msgtype,'C1','C1 - Controllo con immagine elettronica', 'C2', 'C2 - Controllo senza immagine elettronica') AS CONTROLLO_FORMAZIONE,
       	trunc(mt.trkdate) as DATA,
       	decode(substr(mt.dt_dispbarcode,0,2),'SV','GABBIA','DISPACCIO') as TIPO,
       	mt.dt_dispbarcode as SIGILLO,
       	mt.causal||' - '||pc.causalname as PRODOTTO,
       	count(*) as NUMERO_PEZZI, mt.operator as OPERATORE
from starown.mailpiece_tracks mt, starown.po_causals pc
where mt.causal = pc.causal
	and mt.track_office in (select distinct officeid from starown.po_offices_anag where tipo_ufficio='NXV')
  	and msgtype in ('C1','C2')
   	and mt.trkdate >= trunc(sysdate-1)  -- cambiato da arrivetimestamp a trkdate
   	and mt.trkdate < trunc(sysdate)
group by mt.track_office, mt.msgtype, trunc(mt.trkdate), mt.dt_dispbarcode,mt.causal||' - '||pc.causalname,mt.operator
order by mt.track_office, mt.msgtype, mt.dt_dispbarcode
