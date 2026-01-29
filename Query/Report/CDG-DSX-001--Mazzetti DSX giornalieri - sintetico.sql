WITH bundles AS (
    SELECT 
        bundbarcode AS codice_contenitore,
        track_office AS office_id,
        TO_CHAR(trkdate, 'yyyy-mm-dd hh24:mi:ss') || '.000' AS data_chiusura,
        CASE WHEN progrcodegu > 850 THEN 'SI' END AS accentramento,
        office_other,
        msgtype,
        bundtype
    FROM 
        starown.bundle_tracks
    WHERE 
        hfunction = 'DSX'
        AND msgtype IN ('B1', 'B7')
        AND trkdate >= TRUNC(SYSDATE)
),
bundles_enriched AS (
    SELECT
        codice_contenitore,
        office_id,
        data_chiusura,
        CASE 
            WHEN msgtype = 'B1' AND bundtype = 'GU'
                THEN office_other 
        END AS office_rtz_dest,
        CASE 
            WHEN msgtype = 'B1' AND bundtype = 'GU' AND office_other IS NOT NULL 
                THEN 'Mazzetto Grandi Utenti RTZ'
            WHEN msgtype = 'B1' AND bundtype = 'GU' AND office_other IS NULL 
                THEN 'Mazzetto Grandi Utenti'
            WHEN msgtype = 'B7' AND bundtype = 'MP'
                THEN 'Mazzetto PortaLettere'
        END AS tipo_mazzetto,
        accentramento
    FROM bundles
)
SELECT 
    b.codice_contenitore,
    b.office_id,
    b.data_chiusura,
    b.office_rtz_dest,
    b.tipo_mazzetto,
    b.accentramento,
    COUNT(*) AS num_oggetti
FROM 
    bundles_enriched b
JOIN 
    starown.mailpiece_tracks mt
    ON mt.bt_bundbarcode = b.codice_contenitore
WHERE 
    mt.hfunction = 'DSX'
    AND mt.msgtype IN ('B1', 'B7')
GROUP BY 
    b.codice_contenitore,
    b.office_id,
    b.data_chiusura,
    b.office_rtz_dest,
    b.tipo_mazzetto,
    b.accentramento;