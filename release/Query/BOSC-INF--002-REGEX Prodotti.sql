SELECT p.id,p.ptype,p.name,s.RANGE_ID ,t.code_format_regex
from tt_application.product p, tt_application.code_range_product c, tt_application.code_range s, tt_application.code_type t
where  c.product_id=p.id
and c.range_id=s.range_id
and s.code_type_id=t.id group by p.id,p.ptype,p.name,s.RANGE_ID ,t.code_format_regex
ORDER BY 1

