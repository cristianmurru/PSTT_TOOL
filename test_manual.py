"""
Test manuale per verificare il funzionamento di PSTT Tool
"""

def test_basic_imports():
    """Test base per verificare che gli import funzionino"""
    # If any import fails an exception will be raised and pytest will mark the test as failed
    from app.core.config import get_settings, get_connections_config
    from app.services.connection_service import ConnectionService
    from app.services.query_service import QueryService
    from app.models.connections import DatabaseConnection
    from app.models.queries import QueryInfo
    assert True


def test_configuration():
    """Test configurazione"""
    from app.core.config import get_settings, get_connections_config

    settings = get_settings()
    assert getattr(settings, 'app_name', None)
    assert getattr(settings, 'app_version', None)

    connections_config = get_connections_config()
    assert hasattr(connections_config, 'connections')


def test_services():
    """Test servizi base"""
    from app.services.connection_service import ConnectionService
    from app.services.query_service import QueryService

    conn_service = ConnectionService()
    query_service = QueryService()

    # Test liste connessioni
    connections = conn_service.get_connections()
    assert connections is not None

    # Test liste query
    queries = query_service.get_queries()
    assert isinstance(queries, list)


def test_query_parsing():
    """Test parsing query"""
    from app.services.query_service import QueryService

    query_service = QueryService()

    # Test parsing parametri
    sql_content = """
    define DATAINIZIO='17/06/2022'   --Obbligatorio
    define STATUS='ACTIVE'           --Opzionale

    SELECT * FROM table 
    WHERE data >= '&DATAINIZIO'
    AND status = '&STATUS';
    """

    parameters = query_service._extract_parameters(sql_content)
    assert len(parameters) >= 1


def main():
    """Esegue tutti i test manuali"""
    print("🧪 Test manuali PSTT Tool\n")
    print("=" * 50)
    
    tests = [
        ("Import moduli", test_basic_imports),
        ("Configurazione", test_configuration), 
        ("Servizi base", test_services),
        ("Parsing query", test_query_parsing)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Test: {test_name}")
        print("-" * 30)
        
        if test_func():
            passed += 1
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED")
    
    print("\n" + "=" * 50)
    print(f"📊 Risultato: {passed}/{total} test passati")
    
    if passed == total:
        print("🎉 Tutti i test sono passati! Il sistema funziona correttamente.")
    else:
        print(f"⚠️  {total - passed} test hanno fallito. Controllare gli errori sopra.")
    
    return passed == total


if __name__ == "__main__":
    main()
