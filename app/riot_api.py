# app/riot_api.py
import requests
import os
import time
from .extensions import cache

RIOT_API_KEY = ("RGAPI-bda0657c-26d5-4ea6-862f-4a934eb40eac") 
if not RIOT_API_KEY:
    raise ValueError("La variable de entorno RIOT_API_KEY no está configurada. Por favor, configúrala.")

# Cabeceras estándar para todas las solicitudes a la API de Riot
headers = {
    "X-Riot-Token": RIOT_API_KEY
}

# Configuración de regiones
ACCOUNT_REGION = os.environ.get("RIOT_ACCOUNT_REGION", "europe") 
PLATFORM_REGION = os.environ.get("RIOT_PLATFORM_REGION", "euw1") 

API_BASE_URLS = {
    "account": f"https://{ACCOUNT_REGION}.api.riotgames.com/riot/account/v1/accounts",
    "summoner_v4": f"https://{PLATFORM_REGION}.api.riotgames.com/lol/summoner/v4/summoners",
    "league_v4": f"https://{PLATFORM_REGION}.api.riotgames.com/lol/league/v4/entries",
    "match_v5": f"https://{ACCOUNT_REGION}.api.riotgames.com/lol/match/v5/matches"
}

REQUEST_TIMEOUT_SECONDS = 10 # Timeout para las peticiones requests

# --- Funciones para generar claves de caché explícitas ---
def _make_cache_key_summoner_info(*args, **kwargs):
    name = kwargs.get('name', args[0] if args and len(args) > 0 else None)
    tag = kwargs.get('tag', args[1] if args and len(args) > 1 else None)
    name_norm = name.lower() if name else "none"
    tag_norm = tag.upper() if tag else "none" 
    return f"sinfo__{name_norm}__{tag_norm}"

def _make_cache_key_summoner_v4(*args, **kwargs):
    puuid = kwargs.get('puuid', args[0] if args and len(args) > 0 else None)
    return f"sv4__{puuid}"

def _make_cache_key_league_entries(*args, **kwargs):
    encrypted_summoner_id = kwargs.get('encrypted_summoner_id', args[0] if args and len(args) > 0 else None)
    return f"league__{encrypted_summoner_id}"

def _make_cache_key_match_ids(*args, **kwargs):
    puuid = kwargs.get('puuid', args[0] if args and len(args) > 0 else None)
    count = kwargs.get('count', args[1] if args and len(args) > 1 else None)
    start = kwargs.get('start', args[2] if args and len(args) > 2 else 0) 
    return f"matchids__{puuid}__{count}__{start}"

def _make_cache_key_match_detail(*args, **kwargs):
    match_id = kwargs.get('match_id', args[0] if args and len(args) > 0 else None)
    return f"matchdetail__{match_id}"

# --- Funciones de API cacheadas usando make_cache_key ---
@cache.cached(timeout=900, make_cache_key=_make_cache_key_summoner_info) # Cache por 15 minutos
def get_summoner_info(name: str, tag: str):
    """Obtiene la información de la cuenta (incluyendo PUUID) por Riot ID."""
    print(f"[[API CALL w/ make_cache_key]] get_summoner_info para {name}#{tag}") 
    url = f"{API_BASE_URLS['account']}/by-riot-id/{name}/{tag}"
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        error_text = response.text if 'response' in locals() and hasattr(response, 'text') else 'No response text'
        print(f"Error HTTP (Account API) para {name}#{tag}: {http_err} - Status: {response.status_code if 'response' in locals() else 'N/A'} - Text: {error_text}")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"Error de red/conexión (Account API) para {name}#{tag}: {req_err}")
        return None
    except ValueError as json_err: 
        print(f"Error al decodificar JSON (Account API) para {name}#{tag}: {json_err}")
        return None

@cache.cached(timeout=3600, make_cache_key=_make_cache_key_summoner_v4) # Cache por 1 hora
def get_summoner_v4_details_by_puuid(puuid: str):
    """Obtiene detalles del invocador (nivel, icono, ID encriptado) desde SUMMONER-V4."""
    print(f"[[API CALL w/ make_cache_key]] get_summoner_v4_details_by_puuid para PUUID {puuid}")
    if not puuid: return None
    url = f"{API_BASE_URLS['summoner_v4']}/by-puuid/{puuid}"
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        error_text = response.text if 'response' in locals() and hasattr(response, 'text') else 'No response text'
        print(f"Error HTTP (Summoner-V4 API) para PUUID {puuid}: {http_err} - Status: {response.status_code} - Text: {error_text}")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"Error de red/conexión (Summoner-V4 API) para PUUID {puuid}: {req_err}")
        return None
    except ValueError as json_err:
        print(f"Error al decodificar JSON (Summoner-V4 API) para PUUID {puuid}: {json_err}")
        return None

@cache.cached(timeout=300, make_cache_key=_make_cache_key_league_entries) # Cache por 5 minutos
def get_league_v4_entries_by_summoner_id(encrypted_summoner_id: str):
    """Obtiene las entradas de liga (rango) para un invocador desde LEAGUE-V4."""
    print(f"[[API CALL w/ make_cache_key]] get_league_v4_entries_by_summoner_id para EncryptedID {encrypted_summoner_id}")
    if not encrypted_summoner_id: return []
    url = f"{API_BASE_URLS['league_v4']}/by-summoner/{encrypted_summoner_id}"
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json() 
    except requests.exceptions.HTTPError as http_err:
        error_text = response.text if 'response' in locals() and hasattr(response, 'text') else 'No response text'
        print(f"Error HTTP (League-V4 API) para EncryptedID {encrypted_summoner_id}: {http_err} - Status: {response.status_code} - Text: {error_text}")
        return []
    except requests.exceptions.RequestException as req_err:
        print(f"Error de red/conexión (League-V4 API) para EncryptedID {encrypted_summoner_id}: {req_err}")
        return []
    except ValueError as json_err:
        print(f"Error al decodificar JSON (League-V4 API) para EncryptedID {encrypted_summoner_id}: {json_err}")
        return []

@cache.cached(timeout=300, make_cache_key=_make_cache_key_match_ids) # Cache lista de IDs por 5 minutos
def _get_match_ids_from_api(puuid: str, count: int, start: int = 0):
    """Función auxiliar para obtener solo la lista de IDs de partidas (cacheable)."""
    print(f"[[API CALL w/ make_cache_key]] _get_match_ids_from_api para PUUID {puuid}, count {count}, start {start}")
    match_ids_url = f"{API_BASE_URLS['match_v5']}/by-puuid/{puuid}/ids?start={start}&count={count}"
    try:
        response_ids = requests.get(match_ids_url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        response_ids.raise_for_status()
        return response_ids.json()
    except requests.exceptions.HTTPError as http_err:
        error_text = response_ids.text if 'response_ids' in locals() and hasattr(response_ids, 'text') else 'No response text'
        print(f"Error HTTP obteniendo IDs de partidas para PUUID {puuid}: {http_err} - Status: {response_ids.status_code} - Text: {error_text}")
        return []
    except requests.exceptions.RequestException as req_err:
        print(f"Error de red/conexión obteniendo IDs de partidas para PUUID {puuid}: {req_err}")
        return []
    except ValueError as json_err: 
        print(f"Error al decodificar JSON de IDs de partidas para PUUID {puuid}: {json_err}")
        return []

@cache.cached(timeout=86400, make_cache_key=_make_cache_key_match_detail) # Cache detalles de partida por 1 día
def _get_single_match_detail_from_api(match_id: str):
    """Función auxiliar para obtener detalles de UNA partida (cacheable)."""
    print(f"[[API CALL w/ make_cache_key]] _get_single_match_detail_from_api para MatchID {match_id}")
    if not match_id or not isinstance(match_id, str):
        print(f"Error: Match ID inválido para _get_single_match_detail_from_api: {match_id}")
        return None

    match_detail_url = f"{API_BASE_URLS['match_v5']}/{match_id}"
    try:
        response_match = requests.get(match_detail_url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        response_match.raise_for_status()
        return response_match.json()
    except requests.exceptions.HTTPError as http_err:
        error_text = response_match.text if 'response_match' in locals() and hasattr(response_match, 'text') else 'No response text'
        print(f"Error HTTP obteniendo detalles de la partida {match_id}: {http_err} - Status: {response_match.status_code} - Text: {error_text}")
        return None 
    except requests.exceptions.RequestException as req_err:
        print(f"Error de red/conexión obteniendo detalles de la partida {match_id}: {req_err}")
        return None
    except ValueError as json_err: 
        print(f"Error al decodificar JSON de detalles de la partida {match_id}: {json_err}")
        return None

def get_match_history(puuid: str, count: int = 10):
    """Obtiene el historial de partidas, usando funciones cacheadas para IDs y detalles."""
    if not puuid:
        print("Error: Se requiere un PUUID para obtener el historial de partidas.")
        return []
            
    match_ids = _get_match_ids_from_api(puuid=puuid, count=count, start=0) 

    if not isinstance(match_ids, list):
        print(f"Error: Se esperaba una lista de IDs de partidas de _get_match_ids_from_api, pero se obtuvo: {type(match_ids)}")
        return []
    if not match_ids:
        return []

    match_data_list = []
    successful_details_count = 0 
    max_details_to_fetch = count 

    for id_partida in match_ids:
        if successful_details_count >= max_details_to_fetch:
            break 

        if not isinstance(id_partida, str): 
            print(f"Advertencia: Se encontró un ID de partida con formato incorrecto en la lista: {id_partida}")
            continue
        
        match_details = _get_single_match_detail_from_api(match_id=id_partida) 
        if match_details: 
            match_data_list.append(match_details)
            successful_details_count += 1
        else:
            print(f"Advertencia: No se pudieron obtener/cachear los detalles para la partida {id_partida}.")
        
        time.sleep(0.15)
            
    return match_data_list