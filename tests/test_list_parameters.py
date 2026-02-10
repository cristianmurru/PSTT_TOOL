"""
Test per la gestione dei parametri lista (BARCODE_LIST, CODES, IDS, ecc.)
Verifica la corretta formattazione e validazione degli input multipli.
"""
import pytest
from app.services.query_service import QueryService


class TestFormatListParameter:
    """Test per il metodo _format_list_parameter del QueryService"""
    
    @pytest.fixture
    def query_service(self):
        """Fixture per istanziare QueryService"""
        return QueryService()
    
    def test_format_list_comma_separated(self, query_service):
        """Test formato: valori separati da virgola"""
        input_val = "123,456,789"
        result = query_service._format_list_parameter(input_val)
        assert result == "'123','456','789'"
    
    def test_format_list_newline_separated(self, query_service):
        """Test formato: valori separati da newline"""
        input_val = "123\n456\n789"
        result = query_service._format_list_parameter(input_val)
        assert result == "'123','456','789'"
    
    def test_format_list_crlf_separated(self, query_service):
        """Test formato: valori separati da CR+LF (Windows)"""
        input_val = "123\r\n456\r\n789"
        result = query_service._format_list_parameter(input_val)
        assert result == "'123','456','789'"
    
    def test_format_list_already_formatted(self, query_service):
        """Test formato: già formattato con apici e virgola"""
        input_val = "'123','456','789'"
        result = query_service._format_list_parameter(input_val)
        # Gli apici vengono normalizzati
        assert result == "'123','456','789'"
    
    def test_format_list_mixed_separators(self, query_service):
        """Test formato: mix di separatori (virgola, newline, spazi)"""
        input_val = "123, 456\n789 012"
        result = query_service._format_list_parameter(input_val)
        assert result == "'123','456','789','012'"
    
    def test_format_list_alphanumeric(self, query_service):
        """Test valori alfanumerici (barcode possono essere alfanumerici)"""
        input_val = "ABC123,XYZ789,DEF456"
        result = query_service._format_list_parameter(input_val)
        assert result == "'ABC123','XYZ789','DEF456'"
    
    def test_format_list_variable_length(self, query_service):
        """Test valori di lunghezza variabile"""
        input_val = "1,22,333,4444"
        result = query_service._format_list_parameter(input_val)
        assert result == "'1','22','333','4444'"
    
    def test_format_list_with_quotes_double(self, query_service):
        """Test formato: valori con doppi apici"""
        input_val = '"123","456","789"'
        result = query_service._format_list_parameter(input_val)
        # Doppi apici vengono rimossi e normalizzati con singoli
        assert result == "'123','456','789'"
    
    def test_format_list_empty_string(self, query_service):
        """Test stringa vuota"""
        result = query_service._format_list_parameter("")
        assert result == "''"
    
    def test_format_list_whitespace_only(self, query_service):
        """Test solo spazi bianchi"""
        result = query_service._format_list_parameter("   \n  \r\n  ")
        assert result == "''"
    
    def test_format_list_single_value(self, query_service):
        """Test valore singolo"""
        input_val = "386342847828"
        result = query_service._format_list_parameter(input_val)
        assert result == "'386342847828'"
    
    def test_format_list_max_1000_items(self, query_service):
        """Test validazione limite 1000 elementi"""
        # Genera esattamente 1000 elementi
        items = [str(i) for i in range(1000)]
        input_val = ",".join(items)
        result = query_service._format_list_parameter(input_val)
        # Conta elementi nel risultato
        formatted_items = result.split("','")
        assert len(formatted_items) == 1000
    
    def test_format_list_over_1000_items_truncated(self, query_service):
        """Test troncamento oltre 1000 elementi"""
        # Genera 1500 elementi
        items = [str(i) for i in range(1500)]
        input_val = ",".join(items)
        result = query_service._format_list_parameter(input_val)
        # Conta elementi nel risultato - dovrebbero essere max 1000
        formatted_items = result.split("','")
        assert len(formatted_items) == 1000
    
    def test_format_list_escape_apostrophe(self, query_service):
        """Test escape apici interni (SQL injection prevention)"""
        input_val = "ABC'123,DEF'456"
        result = query_service._format_list_parameter(input_val)
        # Apici singoli vengono rimossi nel processo di normalizzazione
        # Funzione split per separatori rimuove anche gli apici
        assert result == "'ABC123','DEF456'"
    
    def test_format_list_with_extra_whitespace(self, query_service):
        """Test rimozione spazi bianchi extra"""
        input_val = "  123  ,  456  ,  789  "
        result = query_service._format_list_parameter(input_val)
        assert result == "'123','456','789'"


class TestListParameterSubstitution:
    """Test per la sostituzione automatica dei parametri lista nel SQL"""
    
    @pytest.fixture
    def query_service(self):
        return QueryService()
    
    def test_barcode_list_parameter_detected(self, query_service):
        """Test rilevamento parametro BARCODE_LIST"""
        from app.models.queries import QueryParameter, ParameterType
        sql = "define BARCODE_LIST = ''\nSELECT * FROM table WHERE barcode IN (&BARCODE_LIST)"
        params = {"BARCODE_LIST": "123,456,789"}
        query_params = [QueryParameter(name="BARCODE_LIST", type=ParameterType.STRING, default_value="", required=True)]
        
        result = query_service._substitute_parameters(sql, params, query_params)
        
        # Verifica che il parametro sia stato trasformato in lista formattata
        assert "'123','456','789'" in result
        assert "&BARCODE_LIST" not in result
    
    def test_codes_parameter_detected(self, query_service):
        """Test rilevamento parametro CODES"""
        from app.models.queries import QueryParameter, ParameterType
        sql = "define CODES = ''\nSELECT * FROM table WHERE code IN (&CODES)"
        params = {"CODES": "A,B,C"}
        query_params = [QueryParameter(name="CODES", type=ParameterType.STRING, default_value="", required=True)]
        
        result = query_service._substitute_parameters(sql, params, query_params)
        
        assert "'A','B','C'" in result
        assert "&CODES" not in result
    
    def test_ids_parameter_detected(self, query_service):
        """Test rilevamento parametro IDS"""
        from app.models.queries import QueryParameter, ParameterType
        sql = "define IDS = ''\nSELECT * FROM table WHERE id IN (&IDS)"
        params = {"IDS": "1,2,3"}
        query_params = [QueryParameter(name="IDS", type=ParameterType.STRING, default_value="", required=True)]
        
        result = query_service._substitute_parameters(sql, params, query_params)
        
        assert "'1','2','3'" in result
        assert "&IDS" not in result
    
    def test_non_list_parameter_not_transformed(self, query_service):
        """Test che parametri normali NON siano trasformati"""
        from app.models.queries import QueryParameter, ParameterType
        sql = "define BARCODE = ''\nSELECT * FROM table WHERE barcode = '&BARCODE'"
        params = {"BARCODE": "123"}
        query_params = [QueryParameter(name="BARCODE", type=ParameterType.STRING, default_value="", required=True)]
        
        result = query_service._substitute_parameters(sql, params, query_params)
        
        # Parametro singolo non deve essere formattato come lista
        assert "123" in result
        assert "'123','456'" not in result
    
    def test_list_parameter_case_insensitive(self, query_service):
        """Test che il rilevamento sia case-insensitive"""
        from app.models.queries import QueryParameter, ParameterType
        sql = "define barcode_list = ''\nSELECT * FROM table WHERE barcode IN (&barcode_list)"
        params = {"barcode_list": "123,456"}
        query_params = [QueryParameter(name="barcode_list", type=ParameterType.STRING, default_value="", required=True)]
        
        result = query_service._substitute_parameters(sql, params, query_params)
        
        # Minuscolo deve funzionare ugualmente
        assert "'123','456'" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
