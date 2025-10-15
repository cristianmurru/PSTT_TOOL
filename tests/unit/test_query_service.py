"""
Test unitari per il QueryService
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from app.services.query_service import QueryService
from app.models.queries import (
    QueryInfo,
    QueryParameter, 
    ParameterType,
    QueryExecutionRequest
)


class TestQueryService:
    """Test per il servizio di gestione query"""
    
    @pytest.fixture
    def query_service(self):
        """Istanza di QueryService per i test"""
        with patch('app.services.query_service.get_settings') as mock_settings:
            mock_settings.return_value.query_dir = Path("test_queries")
            return QueryService()
    
    def test_extract_title_from_filename(self, query_service):
        """Test estrazione titolo dal nome file"""
        # Test formato standard
        title1 = query_service._extract_title_from_filename("BOSC-NXV--001--Accessi operatori.sql")
        assert title1 == "Accessi Operatori"
        
        # Test formato semplice
        title2 = query_service._extract_title_from_filename("simple_query.sql")
        assert title2 == "Simple Query"
        
        # Test formato con underscore
        title3 = query_service._extract_title_from_filename("extract_data.sql")
        assert title3 == "Extract Data"
    
    def test_extract_parameters_oracle_define(self, query_service):
        """Test estrazione parametri da define Oracle"""
        sql_content = """
        -- Query di test
        define DATAINIZIO='17/06/2022'   --Obbligatorio
        define DATAFINE='17/06/2025'     --Opzionale
        define STATUS='ACTIVE'           --Obbligatorio: Status attivo
        
        SELECT * FROM table 
        WHERE data >= TO_DATE('&DATAINIZIO', 'dd/mm/yyyy')
        AND data < TO_DATE('&DATAFINE', 'dd/mm/yyyy')
        AND status = '&STATUS';
        """
        
        parameters = query_service._extract_parameters(sql_content)
        
        assert len(parameters) == 3
        
        # Verifica parametro obbligatorio
        param_inizio = next(p for p in parameters if p.name == "DATAINIZIO")
        assert param_inizio.required == True
        assert param_inizio.default_value == "17/06/2022"
        assert param_inizio.parameter_type == ParameterType.DATE
        
        # Verifica parametro opzionale
        param_fine = next(p for p in parameters if p.name == "DATAFINE") 
        assert param_fine.required == False
        assert param_fine.default_value == "17/06/2025"
        
        # Verifica parametro con descrizione
        param_status = next(p for p in parameters if p.name == "STATUS")
        assert param_status.required == True
        assert "Status attivo" in param_status.description
    
    def test_extract_parameters_ampersand_only(self, query_service):
        """Test estrazione parametri solo con &PARAM"""
        sql_content = """
        SELECT * FROM table 
        WHERE id = '&USER_ID'
        AND name LIKE '&USER_NAME%'
        AND created_date > '&START_DATE';
        """
        
        parameters = query_service._extract_parameters(sql_content)
        
        assert len(parameters) == 3
        param_names = [p.name for p in parameters]
        assert "USER_ID" in param_names
        assert "USER_NAME" in param_names  
        assert "START_DATE" in param_names
        
        # Tutti dovrebbero essere obbligatori di default
        for param in parameters:
            assert param.required == True
            assert param.parameter_type == ParameterType.STRING
    
    def test_infer_parameter_type(self, query_service):
        """Test inferenza tipo parametro"""
        # Test date
        assert query_service._infer_parameter_type("DATAINIZIO", "17/06/2022") == ParameterType.DATE
        assert query_service._infer_parameter_type("START_DATE", "") == ParameterType.DATE
        
        # Test integer
        assert query_service._infer_parameter_type("USER_ID", "123") == ParameterType.INTEGER
        assert query_service._infer_parameter_type("COUNT", "") == ParameterType.INTEGER
        
        # Test float
        assert query_service._infer_parameter_type("AMOUNT", "123.45") == ParameterType.FLOAT
        
        # Test boolean
        assert query_service._infer_parameter_type("ACTIVE", "true") == ParameterType.BOOLEAN
        assert query_service._infer_parameter_type("ENABLED", "1") == ParameterType.BOOLEAN
        
        # Test string (default)
        assert query_service._infer_parameter_type("NAME", "test") == ParameterType.STRING
        assert query_service._infer_parameter_type("UNKNOWN", "") == ParameterType.STRING
    
    def test_substitute_parameters(self, query_service):
        """Test sostituzione parametri nella query"""
        sql_content = """
        define DATAINIZIO='17/06/2022'   --Obbligatorio
        define STATUS='ACTIVE'           --Opzionale
        
        SELECT * FROM table 
        WHERE data >= TO_DATE('&DATAINIZIO', 'dd/mm/yyyy')
        AND status = '&STATUS'
        AND office_id = '&OFFICE_ID';
        """
        
        query_params = [
            QueryParameter(name="DATAINIZIO", required=True, default_value="17/06/2022"),
            QueryParameter(name="STATUS", required=False, default_value="ACTIVE"),
            QueryParameter(name="OFFICE_ID", required=True)
        ]
        
        provided_params = {
            "DATAINIZIO": "01/01/2023",
            "OFFICE_ID": "77001"
        }
        
        result = query_service._substitute_parameters(sql_content, provided_params, query_params)
        
        # Verifica sostituzione parametri forniti
        assert "&DATAINIZIO" not in result
        assert "01/01/2023" in result
        assert "&OFFICE_ID" not in result  
        assert "77001" in result
        
        # Verifica uso valore di default per parametro non fornito
        assert "&STATUS" not in result
        assert "ACTIVE" in result
        
        # Verifica rimozione delle righe define
        assert "define DATAINIZIO" not in result
        assert "define STATUS" not in result
    
    def test_validate_parameters(self, query_service):
        """Test validazione parametri obbligatori"""
        query_params = [
            QueryParameter(name="REQUIRED_PARAM", required=True),
            QueryParameter(name="OPTIONAL_PARAM", required=False),
            QueryParameter(name="DEFAULT_PARAM", required=True, default_value="default")
        ]
        
        # Test parametri mancanti
        missing = query_service._validate_parameters(query_params, {})
        assert "REQUIRED_PARAM" in missing
        assert "OPTIONAL_PARAM" not in missing
        assert "DEFAULT_PARAM" not in missing  # Ha valore default
        
        # Test parametri completi
        complete = query_service._validate_parameters(query_params, {
            "REQUIRED_PARAM": "value",
            "OPTIONAL_PARAM": "value"
        })
        assert len(complete) == 0
    
    @pytest.mark.asyncio
    async def test_parse_sql_file(self, query_service, sample_query_file):
        """Test parsing completo di un file SQL"""
        query_info = query_service._parse_sql_file(sample_query_file)
        
        assert query_info is not None
        assert isinstance(query_info, QueryInfo)
        assert query_info.filename == "test_query.sql"
        assert query_info.title is not None
        assert len(query_info.parameters) == 2  # OFFICE_PREFIX e STATUS
        assert query_info.size_bytes > 0
        assert query_info.modified_at is not None
        
        # Verifica parametri estratti
        param_names = [p.name for p in query_info.parameters]
        assert "OFFICE_PREFIX" in param_names
        assert "STATUS" in param_names
        
        office_param = next(p for p in query_info.parameters if p.name == "OFFICE_PREFIX")
        assert office_param.required == True
        assert office_param.default_value == "77%"
