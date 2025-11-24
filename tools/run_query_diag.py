from app.services.query_service import QueryService
from app.models.queries import QueryExecutionRequest

if __name__ == '__main__':
    qs = QueryService()
    req = QueryExecutionRequest(
        query_filename='CDG-SPOT-001--Estrai ultimo stato - A2A.sql',
        connection_name='A00-CDG-Collaudo',
        parameters={},
        limit=None
    )
    res = qs.execute_query(req)
    print('Success:', res.success)
    print('Row count:', res.row_count)
    if res.error_message:
        print('Error:', res.error_message)
    else:
        print('Columns:', res.column_names)
        print('First rows:', res.data[:5])
