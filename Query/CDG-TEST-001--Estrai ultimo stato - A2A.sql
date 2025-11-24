--Estrazione ultimo evento CdG
--$STEP 1$ -> Inizializza tabella di appoggio
delete from starown.APPO_BARCODE_NO_EMF;

--$STEP 2$ -> Valorizzazione della  tabella temporanea
Insert into starown.APPO_BARCODE_NO_EMF (BARCODE) values ('RR336255819IN');
Insert into starown.APPO_BARCODE_NO_EMF (BARCODE) values ('RR364201860IN');
Insert into starown.APPO_BARCODE_NO_EMF (BARCODE) values ('F2MMRR0000011');

--$STEP 3$ -> Estrazione del recorset finale
alter session set nls_date_format = 'dd/mm/yyyy hh24:mi:ss';
alter session set nls_timestamp_format = 'dd/mm/yyyy hh24:mi:ss';

select c.barcode, a.trkdate as data_evento_recapito, a.track_office as frazionario, a.canale, a.msgtype, a.caunotif,
decode(a.msgtype||nvl(a.caunotif,0), 'M10', '0 - In lavorazione',
'M2PC1','1 - Consegnato (DP11, ritiro allo sportello)',
'M2PC2','3 - Non consegnabile (DP10, invio rifiutato)',
'M2PC5','1 - Consegnato al mittente',
'O20','3 - Non consegnabile (DP15, compiuta giacenza)',
'B20','4 - In giacenza',
'B4PT1','1 - Consegnato (DP1, recapitato)',
'B4PT2','2 - Inviato in giacenza',
'B4PT14','3 - Non consegnabile (DP2, destinatario sconosciuto)',
'B4PT7','3 - Non consegnabile (DP3, destinatario trasferito)',
'B4PT8','3 - Non consegnabile (DP4, destinatario irreperibile)',
'B4PT9','3 - Non consegnabile (DP5, destinatario deceduto)',
'B4PT12','3 - Non consegnabile (DP6, indirizzo inesistente)',
'B4PT10','3 - Non consegnabile (DP7, indirizzo insufficiente)',
'B4PT11','3 - Non consegnabile (DP8, indirizzo inesatto)',
'B4PT44','3 - Non consegnabile (DP9, recapito non tentato)',
'B4PT13','3 - Non consegnabile (DP10, invio rifiutato)',
'B4PT6','5 - Non consegnabile (DP12, furto/smarrimento)',
'B4PT48','5 - Non consegnabile (DP13, busta danneggiata)',
'A10','5 - Non consegnabile (DP13, anomalia)',
'B4PT43','3 - Non consegnabile (DP14, causa forza maggiore)',
'B4PT45','9 - Ritornato al mittente',
'B4PS07','Seguimi',
'B4PT47','Rifiutato dal destinatario per danneggiamento',
'B4PT5','Inesitato - Reso presso altro Ufficio',
'B3PT1','1 - Consegnato (DP1, recapitato)',
'B3PT2','2 - Inviato in giacenza',
'B3PT14','3 - Non consegnabile (DP2, destinatario sconosciuto)',
'B3PT7','3 - Non consegnabile (DP3, destinatario trasferito)',
'B3PT8','3 - Non consegnabile (DP4, destinatario irreperibile)',
'B3PT9','3 - Non consegnabile (DP5, destinatario deceduto)',
'B3PT12','3 - Non consegnabile (DP6, indirizzo inesistente)',
'B3PT10','3 - Non consegnabile (DP7, indirizzo insufficiente)',
'B3PT11','3 - Non consegnabile (DP8, indirizzo inesatto)',
'B3PT44','3 - Non consegnabile (DP9, recapito non tentato)',
'B3PT13','3 - Non consegnabile (DP10, invio rifiutato)',
'B3PT6','5 - Non consegnabile (DP12, furto/smarrimento)',
'B3PT48','5 - Non consegnabile (DP13, busta danneggiata)',
'B3PT43','3 - Non consegnabile (DP14, causa forza maggiore)',
'B3PT45','9 - Ritornato al mittente',
'B3PS07','Seguimi',
'B3PT47','Rifiutato dal destinatario per danneggiamento',
'B3PT5','Inesitato - Reso presso altro Ufficio',
'xxxxxxxxxxxx') as esito, c.trkdate as data_ultimo_evento, c.track_office,d.officename as NOME_FRAZIONARIO, c.office_other as frazionario_dest, c.canale, c.msgtype, c.caunotif
from starown.mailpiece_tracks a, starown.mailpiece_tracks c, starown.po_offices_anag d
where ((a.msgtype(+) in ('B2','O2','M2')
and a.canale(+) ='OMP') or (a.msgtype(+) in ('A1','B4','B3')))
and nvl(a.TRKDATE,trunc(sysdate)) = (Select nvl(max(TRKDATE),trunc(sysdate)) from starown.mailpiece_tracks B Where Barcode=A.Barcode
and ((msgtype in ('B2','O2','M2') and canale='OMP') or (msgtype in ('A1','B4','B3'))))
and c.TRKDATE = (Select max(TRKDATE) from starown.mailpiece_tracks Where Barcode=c.Barcode and msgtype not in ('NP','NF','NV','MP'))
and a.barcode(+)=c.barcode
and (c.track_office = d.officeid and d.last_effective > trunc(sysdate))
and c.barcode in (select barcode from starown.appo_barcode_no_emf)
order by barcode, data_evento_recapito;