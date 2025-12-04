define MSGTYPE='%'  --facoltativo
select * 
from starown.msgtypes M
where (NVL(upper(msgtype),'%%') like upper('%&MSGTYPE%'))
order by msgtype