from flask import Blueprint, render_template, request, redirect, url_for
from app.riot_api import (
    get_summoner_info, 
    get_match_history,
    get_summoner_v4_details_by_puuid, 
    get_league_v4_entries_by_summoner_id 
)

from app.ai.analyzer import (
    extract_player_stats, 
    process_all_participants_for_display,
    extract_all_participant_stats_for_db,
    QUEUE_ID_TO_GAME_MODE_NAME
)
from app.ai.recommender import ( 
    rule_based_recommendations, 
    get_ml_recommendations,
    analyze_playstyle_with_clustering
)
from app.extensions import db
from app.models import Partida, ParticipantePartida

import requests
import os
import joblib 
import pandas as pd 
import numpy as np 
import traceback
import json

routes = Blueprint("routes", __name__)

# --- Carga del Modelo de Predicción de Composición y Características ---
MODEL_COMPOSITION_PATH = 'team_composition_predictor.joblib'
FEATURES_COMPOSITION_PATH = 'team_composition_features.joblib'
TOP_FEATURES_DATA_PATH = 'top_champion_influencers.json'

composition_model = None
composition_model_features_ordered = [] 
top_champion_influencers = []

try:
    if os.path.exists(MODEL_COMPOSITION_PATH) and os.path.exists(FEATURES_COMPOSITION_PATH):
        composition_model = joblib.load(MODEL_COMPOSITION_PATH)
        composition_model_features_ordered = joblib.load(FEATURES_COMPOSITION_PATH)
        print(f"✅ Modelo de predicción de composición ({MODEL_COMPOSITION_PATH}) y {len(composition_model_features_ordered)} características ({FEATURES_COMPOSITION_PATH}) cargados.")
        
        if os.path.exists(TOP_FEATURES_DATA_PATH):
            with open(TOP_FEATURES_DATA_PATH, 'r') as f:
                top_champion_influencers = json.load(f) 
            print(f"✅ Top campeones influyentes cargados desde: {TOP_FEATURES_DATA_PATH}")
        else:
            print(f"⚠️ Advertencia: No se encontró {TOP_FEATURES_DATA_PATH}. No se mostrarán los top campeones influyentes.")
            
    else:
        print(f"⚠️ Advertencia: No se encontraron los archivos del modelo de predicción de composición y/o características.")
        print(f"   Ruta modelo: {os.path.abspath(MODEL_COMPOSITION_PATH)}")
        print(f"   Ruta features: {os.path.abspath(FEATURES_COMPOSITION_PATH)}")
        print("   Ejecuta 'train_composition_model.py' para generarlos.")
except Exception as e:
    print(f"❌ Error al cargar el modelo de predicción, características o top influencers: {e}")
    traceback.print_exc()
    composition_model = None
    top_champion_influencers = []


DDRAGON_VERSION_CACHE = None 
MATCH_COUNT_FOR_AI = int(os.environ.get("MATCH_COUNT_FOR_AI", 30)) 
MIN_GAMES_FOR_CHAMP_ML = int(os.environ.get("MIN_GAMES_FOR_CHAMP_ML", 15)) 
MIN_GAMES_FOR_CLUSTERING_ML = int(os.environ.get("MIN_GAMES_FOR_CLUSTERING_ML", 10)) 
NUM_CLUSTERS_PLAYSTYLE = int(os.environ.get("NUM_CLUSTERS_PLAYSTYLE", 3)) 

def get_ddragon_version():
    global DDRAGON_VERSION_CACHE
    if DDRAGON_VERSION_CACHE:
        return DDRAGON_VERSION_CACHE
    try:
        response = requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=5)
        response.raise_for_status()
        DDRAGON_VERSION_CACHE = response.json()[0]
        return DDRAGON_VERSION_CACHE
    except Exception:
        DDRAGON_VERSION_CACHE = "14.9.1"
        return DDRAGON_VERSION_CACHE

def get_team_composition_prediction_insight(team_participants_data, model, ordered_features):
    if not model or not ordered_features or not team_participants_data or len(team_participants_data) != 10:
        return "Predicción de composición no disponible (datos insuficientes o modelo no cargado)."

    try:
        game_vector_dict = {feature: 0 for feature in ordered_features}
        blue_champs_count = 0; red_champs_count = 0

        for p_info in team_participants_data: 
            champ_name = p_info.get("championName")
            team_id = p_info.get("teamId")
            if champ_name and champ_name in game_vector_dict: 
                if team_id == 100: 
                    game_vector_dict[champ_name] = 1
                    blue_champs_count += 1
                elif team_id == 200: 
                    game_vector_dict[champ_name] = -1
                    red_champs_count += 1
        
        if blue_champs_count != 5 or red_champs_count != 5:
            return "Predicción no disponible (composición 5v5 incompleta)."

        game_vector_df = pd.DataFrame([game_vector_dict], columns=ordered_features)
        
        probabilities = model.predict_proba(game_vector_df)
        prob_blue_wins = probabilities[0][1] 
        
        return f"Estimación de victoria para Equipo Azul (según composición): {prob_blue_wins*100:.0f}%"
    except Exception as e:
        print(f"Error durante la predicción de composición para una partida: {e}")
        traceback.print_exc()
        return "Error al generar predicción de composición."


@routes.route("/", methods=["GET", "POST"])
def index():
    global DDRAGON_VERSION_CACHE 
    DDRAGON_VERSION_CACHE = None 
    if request.method == "POST":
        riot_id_form = request.form.get("riot_id", "").strip()
        if riot_id_form and "#" in riot_id_form:
            return redirect(url_for("routes.summoner", riot_id=riot_id_form))
        else:
            return render_template("index.html", error_format="Formato de Riot ID incorrecto. Debe ser Nombre#TAG.")
    return render_template("index.html")

@routes.route("/summoner/<path:riot_id>")
def summoner(riot_id):
    context_vars = {
        "summoner_name_display": riot_id,
        "version": get_ddragon_version(),
        "general_recommendations": [],
        "ml_decision_tree_insights": [],
        "playstyle_insights": [],
        "top_champion_influencers": top_champion_influencers,
        "api_warning": None,
        "stats": [],
        "profile_icon_id": None,
        "summoner_level": None,
        "solo_rank_info": {"tier": "UNRANKED", "rank": "", "lp": 0, "wins": 0, "losses": 0},
        "error": None
    }

    if "#" not in riot_id:
        context_vars["error"] = "El Riot ID debe tener el formato nombre#tag."
        return render_template("summoner.html", **context_vars)
    
    try:
        name, tag = riot_id.split("#", 1)
    except ValueError:
        context_vars["error"] = "Error al parsear Riot ID."
        return render_template("summoner.html", **context_vars)

    account_info = get_summoner_info(name, tag)
    if not account_info or "puuid" not in account_info:
        context_vars["error"] = f"No se encontró al invocador: {name}#{tag} o faltan datos de la cuenta."
        return render_template("summoner.html", **context_vars)

    player_puuid = account_info["puuid"]
    current_game_name = account_info.get("gameName", name)
    current_tag_line = account_info.get("tagLine", tag)
    context_vars["summoner_name_display"] = f"{current_game_name}#{current_tag_line}"
    
    summoner_details_v4 = get_summoner_v4_details_by_puuid(player_puuid)
    if summoner_details_v4:
        context_vars["profile_icon_id"] = summoner_details_v4.get("profileIconId")
        context_vars["summoner_level"] = summoner_details_v4.get("summonerLevel")
        encrypted_summoner_id = summoner_details_v4.get("id")
        if encrypted_summoner_id:
            league_entries = get_league_v4_entries_by_summoner_id(encrypted_summoner_id)
            if isinstance(league_entries, list):
                for entry in league_entries:
                    if isinstance(entry, dict) and entry.get("queueType") == "RANKED_SOLO_5x5":
                        context_vars["solo_rank_info"] = {
                            "tier": entry.get("tier", "UNRANKED").upper(),
                            "rank": entry.get("rank", ""),
                            "lp": entry.get("leaguePoints", 0),
                            "wins": entry.get("wins", 0),
                            "losses": entry.get("losses", 0)
                        }
                        break 
    
    match_history_json_list = get_match_history(player_puuid, count=MATCH_COUNT_FOR_AI)
    processed_matches_for_template = []
    newly_added_match_count_to_db = 0

    if match_history_json_list:
        for i, single_match_json_data in enumerate(match_history_json_list):
            if not (isinstance(single_match_json_data, dict) and \
                    "metadata" in single_match_json_data and \
                    isinstance(single_match_json_data["metadata"], dict) and \
                    "info" in single_match_json_data and \
                    isinstance(single_match_json_data["info"], dict) and \
                    isinstance(single_match_json_data["info"].get("participants"), list) and \
                    isinstance(single_match_json_data["info"].get("teams"), list)):
                continue
            match_id = single_match_json_data["metadata"].get("matchId")
            if not match_id: continue

            partida_existente = db.session.get(Partida, match_id)
            if not partida_existente:
                info = single_match_json_data["info"]
                queue_id_val = info.get("queueId")
                game_mode_name_val = QUEUE_ID_TO_GAME_MODE_NAME.get(queue_id_val, info.get("gameMode", "Desconocido"))
                if game_mode_name_val == "CLASSIC" and queue_id_val is not None: game_mode_name_val = f"Clásico ({queue_id_val})"
                elif game_mode_name_val == "CLASSIC": game_mode_name_val = "Clásico (Otro)"
                elif game_mode_name_val == "Desconocido" and queue_id_val is not None: game_mode_name_val = f"Modo ID: {queue_id_val}"

                nueva_partida = Partida(match_id=match_id, game_creation=info.get("gameCreation"),
                                        game_duration=info.get("gameDuration"), game_version=info.get("gameVersion"),
                                        queue_id=queue_id_val, game_mode_name=game_mode_name_val )
                db.session.add(nueva_partida)
                all_participants_data_for_db = extract_all_participant_stats_for_db(single_match_json_data)
                for p_stat in all_participants_data_for_db:
                    if not p_stat.get("participant_puuid"): continue
                    participante = ParticipantePartida(match_id=match_id, **p_stat) 
                    db.session.add(participante)
                try:
                    db.session.commit()
                    newly_added_match_count_to_db += 1
                except Exception as e:
                    db.session.rollback()
                    print(f"Error al guardar partida {match_id} en BD: {e}; {traceback.format_exc()}")
            
            main_player_stats = extract_player_stats(single_match_json_data, player_puuid)
            if main_player_stats:
                all_participants_for_display = process_all_participants_for_display(
                    single_match_json_data["info"]["participants"] )
                main_player_stats["team_members_display"] = all_participants_for_display
                
                if composition_model and composition_model_features_ordered:
                    main_player_stats["composition_prediction_insight"] = get_team_composition_prediction_insight(
                        all_participants_for_display, composition_model, composition_model_features_ordered )
                else:
                    main_player_stats["composition_prediction_insight"] = "Modelo de predicción de composición no disponible."

                teams_api_data = single_match_json_data["info"]["teams"]
                main_player_stats['blue_team_won'] = any(t.get('win', False) for t in teams_api_data if isinstance(t, dict) and t.get('teamId') == 100)
                main_player_stats['red_team_won'] = any(t.get('win', False) for t in teams_api_data if isinstance(t, dict) and t.get('teamId') == 200)
                processed_matches_for_template.append(main_player_stats)
        
        if newly_added_match_count_to_db > 0:
            print(f"Se añadieron {newly_added_match_count_to_db} nuevas partidas y sus participantes a la base de datos.")

        num_matches_processed = len(processed_matches_for_template)
        if len(match_history_json_list) > 0 and num_matches_processed < len(match_history_json_list):
             context_vars["api_warning"] = (
                f"Nota: Se obtuvieron detalles de {len(match_history_json_list)} partidas, "
                f"pero solo se pudieron procesar completamente {num_matches_processed} para el análisis principal. "
                "Esto puede deberse a datos incompletos o modos no soportados." )
        elif MATCH_COUNT_FOR_AI > 0 and len(match_history_json_list) < MATCH_COUNT_FOR_AI and len(match_history_json_list) > 0 :
             context_vars["api_warning"] = (
                f"Nota: Se solicitaron las últimas {MATCH_COUNT_FOR_AI} partidas, "
                f"pero solo se pudieron cargar detalles de {len(match_history_json_list)}. "
                "Algunas partidas podrían no ser accesibles por la API de Riot." )


    context_vars["stats"] = processed_matches_for_template
    context_vars["general_recommendations"] = rule_based_recommendations(processed_matches_for_template)
    context_vars["ml_decision_tree_insights"] = get_ml_recommendations(
        processed_matches_for_template, min_games_for_champion=MIN_GAMES_FOR_CHAMP_ML ) 
    context_vars["playstyle_insights"] = analyze_playstyle_with_clustering(
        processed_matches_for_template, num_clusters=NUM_CLUSTERS_PLAYSTYLE, 
        min_games_for_clustering=MIN_GAMES_FOR_CLUSTERING_ML )

    return render_template("summoner.html", **context_vars)