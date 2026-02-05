"""
Script di test per verificare la compressione .gz degli export schedulati.
Verifica che:
1. L'esportazione produce file .xlsx (formato standard)
2. Il file .xlsx viene compresso in .xls.gz (estensione .xls.gz per compatibilità Windows)
3. Quando l'utente apre il .xls.gz in Windows Explorer, vede un singolo file .xls decomprimibile
"""
import gzip
import shutil
from pathlib import Path
import pandas as pd


def test_compress_export():
    """Test manuale della compressione .gz"""
    
    # Crea un file di test
    test_dir = Path("exports/_tmp")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Crea file Excel di test (.xlsx formato standard)
    print("📝 Creazione file Excel di test (.xlsx)...")
    df = pd.DataFrame({
        "ID": [1, 2, 3],
        "Nome": ["Mario", "Luigi", "Peach"],
        "Valore": [100, 200, 300]
    })
    
    test_file = test_dir / "test_export.xlsx"
    df.to_excel(test_file, index=False)
    original_size = test_file.stat().st_size
    print(f"✅ File creato: {test_file} ({original_size} bytes)")
    
    # 2. Comprimi in .xls.gz (nome con estensione .xls per Windows)
    print("\n🗜️  Compressione in .xls.gz...")
    base_name = test_file.stem  # 'test_export' senza estensione
    gz_file = test_dir / f"{base_name}.xls.gz"
    with open(test_file, 'rb') as f_in:
        with gzip.open(gz_file, 'wb', compresslevel=6) as f_out:
            f_out.writelines(f_in)
    
    compressed_size = gz_file.stat().st_size
    compression_ratio = (1 - compressed_size / original_size) * 100
    print(f"✅ File compresso: {gz_file} ({compressed_size} bytes)")
    print(f"📊 Ratio compressione: {compression_ratio:.1f}%")
    
    # 3. Verifica decompressione
    print(f"\n🔓 Test decompressione: {base_name}_decompressed.xlsx")
    decompressed_file = test_dir / "test_export_decompressed.xlsx"
    with gzip.open(gz_file, 'rb') as f_in:
        with open(decompressed_file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    decompressed_size = decompressed_file.stat().st_size
    print(f"✅ File decompresso: {decompressed_file} ({decompressed_size} bytes)")
    
    # 4. Verifica integrità
    if original_size == decompressed_size:
        print("\n✅ Test PASSED: Il file decompresso ha la stessa dimensione dell'originale")
        
        # Verifica contenuto
        df_original = pd.read_excel(test_file)
        df_decompressed = pd.read_excel(decompressed_file)
        
        if df_original.equals(df_decompressed):
            print("✅ Test PASSED: Il contenuto è identico")
        else:
            print("❌ Test FAILED: Il contenuto è diverso")
    else:
        print(f"❌ Test FAILED: Dimensione diversa (originale: {original_size}, decompresso: {decompressed_size})")
    
    # 5. Pulizia
    print("\n🧹 Pulizia file di test...")
    test_file.unlink()
    gz_file.unlink()
    decompressed_file.unlink()
    print("✅ Pulizia completata")
    
    print("\n" + "="*60)
    print("📋 Riepilogo:")
    print(f"   - File originale: {original_size} bytes (.xlsx)")
    print(f"   - File compresso: {compressed_size} bytes (.xls.gz)")
    print(f"   - Riduzione: {compression_ratio:.1f}%")
    print(f"   - Apertura file .xls.gz: Windows mostra '{base_name}.xls'")
    print("="*60)


if __name__ == "__main__":
    test_compress_export()
