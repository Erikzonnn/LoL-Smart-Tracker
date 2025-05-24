# app/ai/analyzer.py

SUMMONER_SPELLS = {
    1: "SummonerBoost",    # Cleanse
    3: "SummonerExhaust",  # Exhaust
    4: "SummonerFlash",    # Flash
    6: "SummonerHaste",    # Ghost
    7: "SummonerHeal",     # Heal
    11: "SummonerSmite",   # Smite
    12: "SummonerTeleport",# Teleport
    13: "SummonerMana",    # Clarity (ARAM)
    14: "SummonerDot",     # Ignite
    21: "SummonerBarrier", # Barrier
    32: "SummonerSnowball", # Mark (ARAM)
    54: "Summoner_UltBookPlaceholder", 
    55: "Summoner_UltBookSmitePlaceholder"
}

CDRAGON_RUNE_STYLE_ICON_FILES = {
    8100: "7200_domination.png",
    8000: "7201_precision.png",
    8200: "7202_sorcery.png",
    8300: "7203_whimsy.png", 
    8400: "7204_resolve.png"
}

QUEUE_ID_TO_GAME_MODE_NAME = {
    0: "Custom", 
    400: "Normal (Draft)",
    420: "Ranked Solo/Duo",
    430: "Normal (Blind)",
    440: "Ranked Flex",
    450: "ARAM",
    490: "Normal (Quickplay)",
    700: "Clash",
    830: "Intro Bots",
    840: "Beginner Bots",
    850: "Intermediate Bots",
    900: "URF",
    1020: "One for All",
    1300: "Nexus Blitz",
    1400: "Ultimate Spellbook",
    1700: "Arena",
    1900: "URF (Pick)",
    2000: "Tutorial 1",
    2010: "Tutorial 2",
    2020: "Tutorial 3"
}

def extract_player_stats(match_data, target_puuid):
    player = None
    if not match_data or not isinstance(match_data, dict) or \
       "info" not in match_data or not isinstance(match_data["info"], dict) or \
       "participants" not in match_data["info"] or not isinstance(match_data["info"]["participants"], list):
        return None

    for participant_data in match_data["info"]["participants"]:
        if isinstance(participant_data, dict) and participant_data.get("puuid") == target_puuid:
            player = participant_data
            break
    if not player: return None

    kills = player.get("kills", 0)
    deaths = player.get("deaths", 0)
    assists = player.get("assists", 0)
    cs = player.get("totalMinionsKilled", 0) + player.get("neutralMinionsKilled", 0)
    gold = player.get("goldEarned", 0)
    damage_to_champs = player.get("totalDamageDealtToChampions", 0)
    game_duration_seconds = match_data["info"].get("gameDuration", 0)
    game_duration_minutes_float = game_duration_seconds / 60.0 if game_duration_seconds > 0 else 0.0
    vision_score = player.get("visionScore", 0)

    kda_ratio = (kills + assists) / max(1, deaths)
    
    cs_per_min = 0
    gold_per_min = 0
    damage_per_min = 0
    vision_score_per_min = 0

    if game_duration_minutes_float > 0:
        gold_per_min = gold / game_duration_minutes_float
        damage_per_min = damage_to_champs / game_duration_minutes_float
        vision_score_per_min = vision_score / game_duration_minutes_float
        cs_per_min = cs / game_duration_minutes_float
    else:
        cs_per_min = 0

    kp_percentage = 0.0
    player_team_id = player.get("teamId")
    total_team_kills = 0
    teams_data = match_data["info"].get("teams", [])
    for team_obj in teams_data:
        if isinstance(team_obj, dict) and team_obj.get("teamId") == player_team_id:
            team_objectives = team_obj.get("objectives")
            if isinstance(team_objectives, dict) and isinstance(team_objectives.get("champion"), dict):
                total_team_kills = team_objectives["champion"].get("kills", 0)
            break
    
    if total_team_kills > 0:
        kp_percentage = ((kills + assists) / total_team_kills) * 100
    elif (kills + assists) > 0: 
        kp_percentage = 100.0

    spell1_id = player.get("summoner1Id")
    spell2_id = player.get("summoner2Id")
    spell1_key = SUMMONER_SPELLS.get(spell1_id, f"UnknownSpellID_{spell1_id}")
    spell2_key = SUMMONER_SPELLS.get(spell2_id, f"UnknownSpellID_{spell2_id}")

    primary_rune_style_icon_file = "UnknownRuneStyle.png" 
    secondary_rune_style_icon_file = "UnknownRuneStyle.png"

    perks_data = player.get("perks")
    if perks_data and isinstance(perks_data.get("styles"), list) and len(perks_data["styles"]) > 0:
        primary_style_info = perks_data["styles"][0]
        if isinstance(primary_style_info, dict):
            primary_rune_style_id = primary_style_info.get("style") 
            primary_rune_style_icon_file = CDRAGON_RUNE_STYLE_ICON_FILES.get(primary_rune_style_id, "UnknownRuneStyle.png")
            
        if len(perks_data["styles"]) > 1:
            secondary_style_info = perks_data["styles"][1]
            if isinstance(secondary_style_info, dict):
                secondary_rune_style_id = secondary_style_info.get("style") 
                secondary_rune_style_icon_file = CDRAGON_RUNE_STYLE_ICON_FILES.get(secondary_rune_style_id, "UnknownRuneStyle.png")

    queue_id = match_data["info"].get("queueId")
    game_mode_name = QUEUE_ID_TO_GAME_MODE_NAME.get(queue_id)
    if game_mode_name is None:
        raw_game_mode = match_data["info"].get("gameMode", "Desconocido")
        if raw_game_mode == "CLASSIC" and queue_id is not None: 
             game_mode_name = f"Clásico ({queue_id})" 
        elif raw_game_mode == "CLASSIC":
             game_mode_name = "Clásico (Otro)"
        elif queue_id is not None: 
            game_mode_name = f"Modo ID: {queue_id}"
        else: 
            game_mode_name = raw_game_mode if raw_game_mode != "Desconocido" else "Modo Desconocido"

    return {
        "champion": player.get("championName", "N/A"),
        "win": player.get("win", False),
        "kills": kills,
        "deaths": deaths,
        "assists": assists,
        "kda_ratio": round(kda_ratio, 2),
        "cs": cs,
        "cs_per_min": round(cs_per_min, 1),
        "gold": gold,
        "gold_per_min": round(gold_per_min, 0),
        "damage_to_champs": damage_to_champs,
        "damage_per_min": round(damage_per_min, 0),
        "vision_score": vision_score,
        "vision_score_per_min": round(vision_score_per_min, 2),
        "kp_percentage": round(kp_percentage, 1),
        "duration": int(round(game_duration_minutes_float,0)), 
        "role": player.get("teamPosition", "N/A"),
        "teamId": player.get("teamId", 0), 
        "item_ids": [player.get(f"item{i}", 0) for i in range(7)], 
        "spells": [spell1_key, spell2_key], 
        "runes": { 
            "primary_icon_file": primary_rune_style_icon_file,
            "secondary_icon_file": secondary_rune_style_icon_file 
        },
        "game_mode_name": game_mode_name
    }

def get_spell_ddragon_key(spell_id_from_api):
    full_spell_name = SUMMONER_SPELLS.get(spell_id_from_api)
    if full_spell_name:
        return full_spell_name  
    return f"UnknownSpellID_{spell_id_from_api}"

def process_all_participants_for_display(participants_api_data_list):
    processed_list = []
    if not isinstance(participants_api_data_list, list):
        return processed_list 

    for p_data in participants_api_data_list:
        if not isinstance(p_data, dict): 
            continue
        
        processed_list.append({
            "championName": p_data.get("championName", "N/A"),
            "summonerName": p_data.get("riotIdGameName") or p_data.get("summonerName") or "Jugador Desconocido",
            "teamId": p_data.get("teamId", 0),
            "win": p_data.get("win", False), 
            "spell1_key": get_spell_ddragon_key(p_data.get("summoner1Id")),
            "spell2_key": get_spell_ddragon_key(p_data.get("summoner2Id")),
        })
    return processed_list

def extract_all_participant_stats_for_db(single_match_json_data):
    """
    Extrae estadísticas detalladas para los 10 participantes de una partida,
    en un formato adecuado para guardar en la base de datos.
    """
    if not single_match_json_data or not isinstance(single_match_json_data, dict) or \
       "info" not in single_match_json_data or not isinstance(single_match_json_data["info"], dict) or \
       "participants" not in single_match_json_data["info"] or not isinstance(single_match_json_data["info"]["participants"], list):
        return []

    all_participant_stats_for_db = []
    game_duration_seconds = single_match_json_data["info"].get("gameDuration", 1)
    game_duration_minutes_float = game_duration_seconds / 60.0 if game_duration_seconds > 0 else 1.0


    for p_data in single_match_json_data["info"]["participants"]:
        if not isinstance(p_data, dict): continue

        kills = p_data.get("kills", 0)
        deaths = p_data.get("deaths", 0)
        assists = p_data.get("assists", 0)
        
        participant_stats = {
            "participant_puuid": p_data.get("puuid"),
            "summoner_name": p_data.get("riotIdGameName") or p_data.get("summonerName") or "Jugador Desconocido",
            "champion_name": p_data.get("championName", "N/A"),
            "team_id": p_data.get("teamId"),
            "win": p_data.get("win", False),
            "kills": kills,
            "deaths": deaths,
            "assists": assists,
            "kda_ratio": round((kills + assists) / max(1, deaths), 2),
            "cs": p_data.get("totalMinionsKilled", 0) + p_data.get("neutralMinionsKilled", 0),
            "cs_per_min": round((p_data.get("totalMinionsKilled", 0) + p_data.get("neutralMinionsKilled", 0)) / game_duration_minutes_float, 1) if game_duration_minutes_float > 0 else 0,
            "gold_earned": p_data.get("goldEarned", 0),
            "gold_per_min": round(p_data.get("goldEarned", 0) / game_duration_minutes_float, 0) if game_duration_minutes_float > 0 else 0,
            "total_damage_to_champions": p_data.get("totalDamageDealtToChampions", 0),
            "damage_per_min": round(p_data.get("totalDamageDealtToChampions", 0) / game_duration_minutes_float, 0) if game_duration_minutes_float > 0 else 0,
            "vision_score": p_data.get("visionScore", 0),
            "vision_score_per_min": round(p_data.get("visionScore", 0) / game_duration_minutes_float, 2) if game_duration_minutes_float > 0 else 0,
            "kp_percentage": 0.0,
            "role": p_data.get("teamPosition", "N/A"),
            "item_ids_str": ",".join([str(p_data.get(f"item{i}", 0)) for i in range(7)]),
            "spell1_key": SUMMONER_SPELLS.get(p_data.get("summoner1Id"), ""),
            "spell2_key": SUMMONER_SPELLS.get(p_data.get("summoner2Id"), ""),
        }

        # Calcular KP%
        total_team_kills_for_participant = 0
        teams_data = single_match_json_data["info"].get("teams", [])
        for team_obj in teams_data:
            if isinstance(team_obj, dict) and team_obj.get("teamId") == participant_stats["team_id"]:
                team_objectives = team_obj.get("objectives")
                if isinstance(team_objectives, dict) and isinstance(team_objectives.get("champion"), dict):
                    total_team_kills_for_participant = team_objectives["champion"].get("kills", 0)
                break
        if total_team_kills_for_participant > 0:
            participant_stats["kp_percentage"] = round(((kills + assists) / total_team_kills_for_participant) * 100, 1)
        elif (kills + assists) > 0:
            participant_stats["kp_percentage"] = 100.0
        
        # Runas
        primary_icon = "UnknownRuneStyle.png"
        secondary_icon = "UnknownRuneStyle.png"
        perks = p_data.get("perks")
        if perks and isinstance(perks.get("styles"), list) and len(perks["styles"]) > 0:
            style1_id = perks["styles"][0].get("style")
            primary_icon = CDRAGON_RUNE_STYLE_ICON_FILES.get(style1_id, "UnknownRuneStyle.png")
            if len(perks["styles"]) > 1:
                style2_id = perks["styles"][1].get("style")
                secondary_icon = CDRAGON_RUNE_STYLE_ICON_FILES.get(style2_id, "UnknownRuneStyle.png")
        participant_stats["primary_rune_style_icon_file"] = primary_icon
        participant_stats["secondary_rune_style_icon_file"] = secondary_icon
        
        all_participant_stats_for_db.append(participant_stats)
        
    return all_participant_stats_for_db