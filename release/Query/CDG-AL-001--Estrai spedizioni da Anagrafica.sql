--Estrazione per divisione Affari Legali
--$STEP 1$ -> Inizializza tabella di appoggio
delete from starown.appo_barcode_cm;

--$STEP 2$ -> Ricerca dei codici corrispondenti e valorizzazione della  tabella temporanea
define DATAINIZIO=''   --Obbligatorio
define DATAFINE='' --Obbligatorio

define SoloDest='1'   -- Obbligatorio: 0-Cerca mittente e destinatario / 1-cerca solo destinatario

define MITT_COGNOME=''  --Opzionale
define MITT_NOME=''  --Opzionale
define MITT_INDIRIZZO=''  --Opzionale
define MITT_CITTA=''  --Opzionale


define DEST_COGNOME='ROSSI'  --Obbligatorio
define DEST_NOME=''  --Opzionale
define DEST_INDIRIZZO=''  --Opzionale
define DEST_CITTA=''  --Opzionale

insert into starown.appo_barcode_cm (barcode)
Select /*+ parallel(a,32) */  distinct MT_Barcode Barcode
from starown.mailpiece_upgrades a
where mt_trkdate >= to_date('&DATAINIZIO', 'dd/mm/yyyy')
and mt_trkdate < to_date('&DATAFINE', 'dd/mm/yyyy')
and (
     (
         (
	 (upper(mitt_name) like  upper('%&MITT_COGNOME%&MITT_NOME%') OR upper(mitt_name) like upper('%&MITT_NOME%&MITT_COGNOME%')) 
            and (NVL(upper(Mitt_Dest),'%%') like upper('%&MITT_CITTA%'))
            and (NVL(upper(Mitt_Addr),'%%') like upper('%&MITT_INDIRIZZO%'))
         ) and '&SoloDest'='0' 
      )--Mittente 
         
         or 
         ( 
         (upper(addressee) like  upper('%&DEST_COGNOME%&DEST_NOME%') OR upper(addressee) like upper('%&DEST_NOME%&DEST_COGNOME%')) 
          and (NVL(upper(Destination),'%%') like upper('%&DEST_CITTA%'))
          and (NVL(upper(Address),'%%') like upper('%&DEST_INDIRIZZO%'))
         )     -- Destinatario
     )

--$STEP 3$ -> Estrazione del recorset finale
With Esiti as 
(
select m.Barcode, max(m.trkdate) TrkDate
from starown.appo_barcode_cm cm
inner join STAROWN.mailpiece_tracks m on m.barcode=cm.barcode
where 1=1
and ((M.msgtype in ('B2','O2','M2') and M.canale ='OMP') or (M.msgtype in ('A1','B4','B3')))
group by m.Barcode
)  

select 
   m.barcode, m.causal, p.causalname, to_char(m.trkdate,'DD-MM-YYYY') TrkDate, m.msgtype, m.caunotif, cau.descrizione Des_CauNotif
    , M.OPERATOR,  M.arrivetimestamp, m.track_office, UffMitt.OfficeName UffMitt , m.office_other, UffDest.OfficeName UffDest, m.areadest, M.lat_gps, m.long_gps
    , case when dd.Addressee is not null then dd.Addressee else mu.Dest_Name_2 end Dest_Name
    , case when dd.Address is not null then dd.Address else mu.Dest_Ind_2 end Dest_Address
    , mu.Dest_CAP Dest_CAP   --non c'è campo campo cap su descriptive datas
    , case when dd.Destination is not null then dd.Destination else mu.Dest_Loc_2 end Dest_Loc
    , dd.Prov_dest Dest_Prov --non c'è campo campo cap su mailpiece_upgrades
    , case when Tel_Dest is not null then Tel_Dest else mu.Tel_Dest_2 end Tel_Dest
    , case when Email_Dest is not null then Email_Dest else mu.Dest_EMail_2 end Email_Dest
    , case when Mitt_Name is not null then Mitt_Name else mu.Mitt_Name_2 end Mitt_Name
    , case when Mitt_addr is not null then Mitt_addr else mu.Mitt_Addr_2 end Mitt_Addr
    , case when Mitt_Zip is not null then Mitt_Zip else mu.Mitt_Zip_2 end Mitt_Zip
    , case when Mitt_dest is not null then Mitt_dest else mu.Mitt_Dest_2 end Mitt_Aest
    , case when Mitt_Prov is not null then Mitt_Prov else mu.Mitt_Prov_2 end Mitt_Prov
from starown.appo_barcode_cm cm
inner join esiti e on e.barcode=cm.barcode 
inner join starown.mailpiece_tracks m on m.barcode=e.barcode and e.trkdate =m.trkdate
left join starown.po_causali cau on cau.caunotif=m.caunotif
left join starown.po_offices_anag UffMitt on UffMitt.officeid=m.track_office and UffMitt.last_effective>trunc(sysdate)
left join starown.po_offices_anag UffDest on UffDest.officeid=m.office_other and UffDest.last_effective>trunc(sysdate)
left join starown.po_causals p on p.causal=m.causal
left join 
    (select dd.Mai_Barcode, max(upper(dd.Addressee)) Addressee,  max(upper(dd.Address)) Address, max(upper(dd.Destination)) Destination, max(upper(dd.Prov_dest)) Prov_dest, max(dd.Tel_Dest) Tel_Dest, max(upper(dd.Email_Dest)) Email_Dest, max(upper(dd.Mitt_Name)) Mitt_Name, max(upper(dd.Mitt_Addr)) Mitt_Addr, max(dd.Mitt_Zip) Mitt_Zip, max(upper(dd.Mitt_Dest)) Mitt_Dest, max(upper(dd.Mitt_Prov)) Mitt_Prov
     from STAROWN.descriptive_datas DD
     group by dd.Mai_Barcode
    ) DD on DD.Mai_Barcode=m.barcode  and dd.ADDRESSEE is not null
left join
    (select MU.MT_Barcode , max(upper(mu.Addressee)) Dest_Name_2,  max(upper(mu.Address)) Dest_Ind_2, max(mu.Zipcode) Dest_CAP, max(upper(mu.Destination)) Dest_Loc_2, max(mu.Tel) Tel_Dest_2, max(upper(mu.Email)) Dest_EMail_2, max(upper(mu.Mitt_Name)) Mitt_Name_2, max(upper(mu.Mitt_Addr)) Mitt_Addr_2, max(mu.Mitt_Zip) Mitt_Zip_2, max(upper(mu.Mitt_Dest)) Mitt_Dest_2, max(upper(mu.Mitt_Prov)) Mitt_Prov_2
     from starown.mailpiece_upgrades mu
     group by MU.MT_Barcode
    ) mu on mu.MT_Barcode=m.barcode
    order by 1
