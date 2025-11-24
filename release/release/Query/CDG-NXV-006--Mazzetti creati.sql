Select  /*+ parallel (mt,32) */  mt.track_office as FRAZIONARIO,
       trunc(mt.trkdate) as DATA,
       mt.bt_bundbarcode as MAZZETTO,
       mt.causal||' - '||pc.causalname as PRODOTTO,
       count(*) as NUMERO_PEZZI , mt.operator
  from starown.mailpiece_tracks mt
    left join starown.po_causals pc on (mt.causal = pc.causal)
where mt.track_office in (select distinct officeid from starown.po_offices_anag where tipo_ufficio='NXV')
   and msgtype in ('B7','B1')
   and mt.trkdate >= trunc(sysdate -1)
   and mt.trkdate < trunc(sysdate)
group by mt.track_office, trunc(mt.trkdate), mt.bt_bundbarcode,mt.operator,mt.causal||' - '||pc.causalname
order by mt.track_office, trunc(mt.trkdate)