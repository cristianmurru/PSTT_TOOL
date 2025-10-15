SELECT /*+ parallel (mt,32) */
    mt.track_office AS FRAZIONARIO,
    poa.officename AS "NOME_FRAZIONARIO",
    poa.provshort AS PROVINCIA,
    poa.regname AS REGIONE,
    TRUNC(mt.trkdate) AS DATA,
    DECODE(mt.areadest, 
        'AS', 'MANUALE',
        'TP', 'PALMARE',
        'RT', 'RT',
        'NON VALORIZZATO') AS "TIPO RECAPITO",
    mt.causal || ' - ' || pc.causalname AS PRODOTTO,
    bt.dscop AS "UTENZA PTL",
    mt.operator,
    mt.caunotif || ' - ' || pca.descrizione AS "TIPO ESITO",
    COUNT(*) AS TOTALE
FROM
    starown.mailpiece_tracks mt
    LEFT JOIN starown.bundle_tracks bt 
        ON mt.bt_bundbarcode = bt.bundbarcode AND bt.msgtype = 'BE'
    LEFT JOIN starown.po_offices_anag poa 
        ON mt.track_office = poa.officeid
    LEFT JOIN starown.po_causals pc 
        ON mt.causal = pc.causal
    LEFT JOIN starown.po_causali pca 
        ON pca.caunotif = mt.caunotif
WHERE
    poa.tipo_ufficio = 'NXV'
    AND poa.last_effective > TRUNC(SYSDATE)
    AND mt.msgtype = 'B4'
    AND mt.trkdate >= TRUNC(SYSDATE - 1)
    AND mt.trkdate < TRUNC(SYSDATE)
    -- AND mt.trkdate >= TO_DATE('26/05/2023','dd/mm/yyyy')
    -- AND mt.trkdate < TO_DATE('27/05/2023','dd/mm/yyyy')
    AND (
        mt.areadest != 'RT' 
        OR mt.areadest IS NULL 
        OR (mt.areadest = 'RT' AND mt.operator = '888')
    )
    AND mt.trkdate = (
        SELECT MAX(trkdate)
        FROM starown.mailpiece_tracks
        WHERE barcode = mt.barcode
            AND msgtype = 'B4'
            AND trkdate < TRUNC(SYSDATE)
        -- AND trkdate < TO_DATE('27/05/2023','dd/mm/yyyy')
    )
GROUP BY
    mt.track_office,
    poa.officename,
    poa.provshort,
    poa.regname,
    TRUNC(mt.trkdate),
    mt.areadest,
    mt.causal || ' - ' || pc.causalname,
    bt.dscop,
    mt.operator,
    mt.caunotif || ' - ' || pca.descrizione
