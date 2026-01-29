define BARCODE=''  --obbligatorio
select 
t.barcode, t.causal,to_char(t.trkdate, 'DD-MM-YYYY HH24:MI:SS') trkdate, arrivetimestamp, t.operator, t.msgtype, mt.msgdescr, t.areadest, t.delreason, t.caunotif, pca.descrizione, t.lat_gps, t.long_gps, t.dscop, t.tipop, 
t.track_office, oa.officename, t.office_other, oah.officename, t.date_other, t.zone_id, t.subzone_id,  
t.mtf_mtfid,t.dt_dispbarcode, t.dt_trkdate, t.bt_bundbarcode, t.bt_trkdate, t.ldt_ldid, t.ldt_trkdate
from starown.mailpiece_tracks t
left join starown.po_causali pca on pca.caunotif = t.caunotif
left join STAROWN.po_offices_anag oa on t.track_office=oa.officeid
left join STAROWN.po_offices_anag oah on t.office_other=oah.officeid
left join starown.msgtypes mt on t.msgtype=mt.msgtype
where t.barcode='&BARCODE'
order by 3
;