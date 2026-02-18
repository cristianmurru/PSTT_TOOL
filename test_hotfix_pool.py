# Test rapido connessioni dopo HOTFIX

import sys
sys.path.insert(0, 'c:\\App\\PSTT_TOOL')

from app.services.connection_service import ConnectionService

print("=" * 60)
print("TEST CONNECTION POOL - HOTFIX 2026-02-11")
print("=" * 60)

# Test 1: Creazione connessione
print("\n1. Test creazione connessione Oracle...")
conn_service = ConnectionService()

# Test 2: Verifica configurazione pool
print("\n2. Verifica configurazione pool...")
pool_config = conn_service._get_pool_config("oracle")
print(f"   pool_pre_ping: {pool_config.get('pool_pre_ping')}")
print(f"   pool_recycle: {pool_config.get('pool_recycle')}s")
print(f"   pool_timeout: {pool_config.get('pool_timeout')}s")

# Test 3: Connessione test
print("\n3. Test connessione P03-CDG-Produzione...")
try:
    result = conn_service.test_connection("P03-CDG-Produzione")
    print(f"   SUCCESS: {result.success}")
    print(f"   Duration: {result.duration_ms:.2f}ms")
    print(f"   Message: {result.message}")
except Exception as e:
    print(f"   ERRORE: {e}")

# Test 4: Pool status
print("\n4. Verifica stato pool...")
try:
    status = conn_service.get_pool_status("P03-CDG-Produzione")
    print(f"   Pool size: {status.get('pool_size')}")
    print(f"   Checked in: {status.get('checked_in')}")
    print(f"   Checked out: {status.get('checked_out')}")
    print(f"   Status: {status.get('status')}")
except Exception as e:
    print(f"   ERRORE: {e}")

# Test 5: Cleanup
print("\n5. Test chiusura connessione...")
try:
    conn_service.close_connection("P03-CDG-Produzione")
    print("   Connessione chiusa correttamente")
except Exception as e:
    print(f"   ERRORE: {e}")

print("\n" + "=" * 60)
print("TEST COMPLETATO")
print("=" * 60)
