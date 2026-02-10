define MSGTYPE='%'  --facoltativo
SELECT *
FROM starown.msgtypes M
WHERE (NVL(upper(msgtype),'%%') like upper('%&MSGTYPE%'))
ORDER BY msgtype