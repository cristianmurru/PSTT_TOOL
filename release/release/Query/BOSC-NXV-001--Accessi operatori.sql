-- Query per estrarre gli accessi degli operatori per gli uffici NXV (frazionario 77XXX)

select 
	trim(id) as "ID"
	,trim(operator_name) as "OPERATOR_NAME"
	,trim(status) as "STATUS"
	,trim(last_login) as "LAST_LOGIN"
	,trim(when_created) as "WHEN_CREATED"
	,trim(office_id) as "OFFICE_ID"
	,trim(type) as "TYPE"
	,trim(operator_first_name) as "OPERATOR_FIRST_NAME"
	,trim(operator_surname) as "OPERATOR_SURNAME"
from tt_application.operator o
where o.office_id like '77%'