"""
API endpoints per la gestione delle connessioni database
"""
from typing import Dict, List
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
import json
from pathlib import Path
from loguru import logger

from app.services.connection_service import ConnectionService
from app.models.connections import (
    ConnectionsResponse, 
    ConnectionTestRequest, 
    ConnectionTest,
    ConnectionSwitchRequest,
    DatabaseConnection
)
from app.core.config import get_connections_config


router = APIRouter()


def get_connection_service():
    """Dependency injection per ConnectionService"""
    return ConnectionService()


@router.get("/", response_model=ConnectionsResponse, summary="Lista connessioni")
async def get_connections(
    connection_service: ConnectionService = Depends(get_connection_service)
):
    """
    Ottiene la lista di tutte le connessioni database configurate
    """
    try:
        connections_config = get_connections_config()
        connections = connection_service.get_connections()
        
        return ConnectionsResponse(
            connections=list(connections.values()),
            default_connection=connections_config.default_connection,
            environments=connections_config.environments,
            default_environment=connections_config.default_environment
        )
        
    except Exception as e:
        logger.error(f"Errore nel recupero delle connessioni: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno nel recupero delle connessioni"
        )


@router.get("/current", summary="Connessione corrente")
async def get_current_connection(
    connection_service: ConnectionService = Depends(get_connection_service)
):
    """
    Ottiene la connessione database attualmente attiva
    """
    try:
        current_connection = connection_service.get_current_connection()
        
        if not current_connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nessuna connessione corrente configurata"
            )
        
        connection_info = connection_service.get_connection(current_connection)
        
        return {
            "current_connection": current_connection,
            "connection_info": connection_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore nel recupero della connessione corrente: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno nel recupero della connessione corrente"
        )


@router.post("/switch", summary="Cambia connessione")
async def switch_connection(
    request: ConnectionSwitchRequest,
    connection_service: ConnectionService = Depends(get_connection_service)
):
    """
    Cambia la connessione database attiva
    """
    try:
        success = connection_service.set_current_connection(request.connection_name)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connessione non trovata: {request.connection_name}"
            )
        
        logger.info(f"Connessione cambiata a: {request.connection_name}")
        
        return {
            "success": True,
            "message": f"Connessione cambiata a {request.connection_name}",
            "current_connection": request.connection_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore nel cambio connessione: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno nel cambio connessione"
        )


@router.post("/test", response_model=ConnectionTest, summary="Testa connessione")
async def test_connection(
    request: ConnectionTestRequest,
    connection_service: ConnectionService = Depends(get_connection_service)
):
    """
    Testa una connessione database specifica
    """
    try:
        # Verifica che la connessione esista
        connection = connection_service.get_connection(request.connection_name)
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connessione non trovata: {request.connection_name}"
            )
        
        # Esegue il test
        test_result = connection_service.test_connection(request.connection_name)
        
        logger.info(f"Test connessione {request.connection_name}: {'successo' if test_result.success else 'fallito'}")
        
        return test_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore nel test della connessione {request.connection_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno nel test della connessione"
        )


@router.get("/environments", summary="Lista ambienti")
async def get_environments():
    """
    Ottiene la lista degli ambienti configurati
    """
    try:
        connections_config = get_connections_config()
        
        # Raggruppa connessioni per ambiente
        environments = {}
        for conn in connections_config.connections:
            env = conn.environment
            if env not in environments:
                environments[env] = []
            environments[env].append(conn.name)
        
        return {
            "environments": environments,
            "default_environment": connections_config.default_environment,
            "available_environments": connections_config.environments
        }
        
    except Exception as e:
        logger.error(f"Errore nel recupero degli ambienti: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno nel recupero degli ambienti"
        )


@router.get("/list", summary="Elenco connessioni e configurazioni (raw JSON)")
async def get_connections_list():
    path = Path(__file__).parent.parent.parent / "connections.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return JSONResponse(content=data)


@router.get("/{connection_name}", response_model=DatabaseConnection, summary="Dettagli connessione")
async def get_connection_details(
    connection_name: str,
    connection_service: ConnectionService = Depends(get_connection_service)
):
    """
    Ottiene i dettagli di una connessione specifica
    """
    try:
        connection = connection_service.get_connection(connection_name)
        
        if not connection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connessione non trovata: {connection_name}"
            )
        
        return connection
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore nel recupero dettagli connessione {connection_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno nel recupero dei dettagli"
        )


@router.delete("/{connection_name}/close", summary="Chiudi connessione")
async def close_connection(
    connection_name: str,
    connection_service: ConnectionService = Depends(get_connection_service)
):
    """
    Chiude una connessione database specifica
    """
    try:
        success = connection_service.close_connection(connection_name)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Connessione non attiva: {connection_name}"
            )
        
        logger.info(f"Connessione chiusa: {connection_name}")
        
        return {
            "success": True,
            "message": f"Connessione {connection_name} chiusa correttamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore nella chiusura connessione {connection_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore interno nella chiusura della connessione"
        )
