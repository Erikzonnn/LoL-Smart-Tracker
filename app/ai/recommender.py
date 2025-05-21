# app/ai/recommender.py
import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import traceback # Para imprimir tracebacks completos en caso de error

# --- Funciones de Análisis Basadas en Reglas (Nivel 1 y Estadístico Avanzado) ---

def analyze_overall_winrate_and_streaks(stats_list):
    recommendations = []
    if not stats_list or len(stats_list) < 3:
        return recommendations

    wins = sum(1 for match in stats_list if match.get("win", False))
    total_games = len(stats_list)
    winrate = wins / total_games if total_games > 0 else 0

    short_losses_count = 0
    for match in stats_list[:min(3, total_games)]: 
        if not match.get("win", False) and match.get("duration", 99) < 22: # Duración en minutos
            short_losses_count += 1
    
    if short_losses_count >= 2:
        recommendations.append(
            "[SUGGESTION] Has tenido varias derrotas en partidas cortas recientemente. "
            "Esto puede ser frustrante. Considera tomar un breve descanso para mantener una mentalidad positiva."
        )
    
    if total_games >= 10 and winrate < 0.40: 
        recommendations.append(
            f"[CRITICAL] Tu winrate en las últimas {total_games} partidas es del {winrate:.0%}. "
            "Un winrate consistentemente bajo puede indicar áreas clave a mejorar. Intenta identificar patrones en tus derrotas."
        )
    elif total_games >= 10 and winrate < 0.50:
         recommendations.append(
            f"[SUGGESTION] Tu winrate en las últimas {total_games} partidas es del {winrate:.0%}. "
            "Estás cerca del equilibrio. Revisa las partidas perdidas para ver qué pequeños cambios podrían inclinar la balanza a tu favor."
        )
    return recommendations

def analyze_champion_performance(stats_list):
    recommendations = []
    if not stats_list:
        return recommendations

    champ_performance = {}
    for match in stats_list:
        champ = match.get("champion")
        if not champ or champ == "N/A": continue

        if champ not in champ_performance:
            champ_performance[champ] = {"kda_ratios": [], "games": 0, "wins": 0, "roles": set()}
        
        champ_performance[champ]["kda_ratios"].append(match.get("kda_ratio", 0))
        champ_performance[champ]["games"] += 1
        role = match.get("role")
        if role and role != "N/A":
            champ_performance[champ]["roles"].add(role)
        if match.get("win", False):
            champ_performance[champ]["wins"] += 1

    for champ, data in champ_performance.items():
        if data["games"] >= 5:  # Umbral de partidas con un campeón para este análisis
            avg_kda = sum(data["kda_ratios"]) / data["games"] if data["games"] > 0 else 0
            winrate = data["wins"] / data["games"] if data["games"] > 0 else 0
            roles_str = "/".join(list(data["roles"])) if data["roles"] else "varios roles"
            
            if winrate < 0.35: # Umbral de winrate bajo
                recommendations.append(
                    f"[CRITICAL] Con {champ} (jugado como {roles_str}), tu winrate es del {winrate:.0%} en {data['games']} partidas. "
                    "Este resultado es muy bajo. Podrías necesitar más práctica o una estrategia diferente con este campeón."
                )
            elif avg_kda < 2.0 : # KDA consistentemente bajo (umbral ejemplo)
                 recommendations.append(
                    f"[SUGGESTION] Tu KDA promedio de {avg_kda:.1f} con {champ} (jugado como {roles_str}) es consistentemente bajo. "
                    "Revisa tu posicionamiento y toma de decisiones para reducir muertes y aumentar tu impacto."
                )
    return recommendations

def analyze_farming_cs_per_min(stats_list):
    recommendations = []
    if not stats_list: return recommendations

    role_cs_thresholds = { "TOP": 6.0, "MIDDLE": 6.5, "BOTTOM": 7.0 } # Umbrales de CS/min de ejemplo
    role_stats = {}

    for match in stats_list:
        role = match.get("role")
        if role in role_cs_thresholds: # Solo roles donde el CS es primario
            if role not in role_stats:
                role_stats[role] = {"total_cs_per_min": 0, "games": 0}
            role_stats[role]["total_cs_per_min"] += match.get("cs_per_min", 0)
            role_stats[role]["games"] += 1
            
    for role, data in role_stats.items():
        if data["games"] >= 5: # Mínimo de partidas en ese rol
            avg_cs_per_min = data["total_cs_per_min"] / data["games"] if data["games"] > 0 else 0
            threshold = role_cs_thresholds[role]
            
            if avg_cs_per_min < threshold * 0.85: # Si está un 15% por debajo del objetivo
                recommendations.append(
                    f"[SUGGESTION] Tu CS/min promedio como {role} es de {avg_cs_per_min:.1f}. "
                    f"Un objetivo para mejorar podría ser alrededor de {threshold:.1f} CS/min. "
                    "Practicar el last hitting y la gestión de oleadas es fundamental."
                )
    return recommendations

def analyze_kill_participation(stats_list):
    recommendations = []
    if not stats_list or len(stats_list) < 5: return recommendations

    relevant_games_kp = []
    for match in stats_list:
        # KP% es más relevante para roles que se espera que roten y participen en peleas.
        if match.get("role") in ["JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"] and "kp_percentage" in match:
            relevant_games_kp.append(match["kp_percentage"])
    
    if len(relevant_games_kp) >= 5: # Mínimo de partidas en roles relevantes
        avg_kp = sum(relevant_games_kp) / len(relevant_games_kp) if len(relevant_games_kp) > 0 else 0
        if avg_kp < 45.0: # Umbral de KP% bajo
            recommendations.append(
                f"[SUGGESTION] Tu participación promedio en asesinatos (KP%) en roles de impacto es del {avg_kp:.0f}%. "
                "Intenta estar más atento a las oportunidades de rotar y unirte a las peleas de equipo."
            )
    return recommendations

def analyze_vision_score(stats_list):
    recommendations = []
    if not stats_list or len(stats_list) < 3: return recommendations
    
    sum_vs_per_min = 0
    game_count_for_vision = 0
    support_vs_min_list = []

    for match in stats_list:
        if match.get("duration", 0) > 15: # Partidas de duración razonable
            vs_min = match.get("vision_score_per_min", 0)
            sum_vs_per_min += vs_min
            game_count_for_vision += 1
            if match.get("role") == "UTILITY":
                support_vs_min_list.append(vs_min)

    if game_count_for_vision >= 3:
        avg_vs_per_min_overall = sum_vs_per_min / game_count_for_vision if game_count_for_vision > 0 else 0
        if avg_vs_per_min_overall < 0.75: # Umbral general de VS/min
            recommendations.append(
                f"[SUGGESTION] Tu puntuación de visión promedio por minuto es de {avg_vs_per_min_overall:.2f}. "
                "Mejorar tu control de visión puede tener un gran impacto en el resultado de las partidas."
            )

    if len(support_vs_min_list) >= 3: # Mínimo de partidas como Soporte
        avg_vs_min_support = sum(support_vs_min_list) / len(support_vs_min_list) if len(support_vs_min_list) > 0 else 0
        if avg_vs_min_support < 1.3: # Umbral de VS/min para Soportes
            recommendations.append(
                f"[CRITICAL] Como Soporte, tu puntuación de visión por minuto es de {avg_vs_min_support:.2f}. "
                "Este es un área crítica para tu rol. Prioriza la compra de Guardianes de Control y usa tu baratija de forma proactiva."
            )
    return recommendations

def analyze_champion_specific_win_factors(stats_list):
    recommendations = []
    if not stats_list or len(stats_list) < 10: 
        return recommendations

    champ_stats = {} 
    for match in stats_list:
        champ = match.get("champion")
        if not champ or champ == "N/A": continue
        if champ not in champ_stats:
            champ_stats[champ] = {'wins_data': [], 'losses_data': [], 'total_games': 0}
        champ_stats[champ]['total_games'] += 1
        if match.get("win", False):
            champ_stats[champ]['wins_data'].append(match)
        else:
            champ_stats[champ]['losses_data'].append(match)

    MIN_GAMES_PER_OUTCOME_FOR_ANALYSIS = 3 
    MIN_TOTAL_GAMES_FOR_CHAMP_ANALYSIS = 7 

    for champ, data in champ_stats.items():
        if data['total_games'] < MIN_TOTAL_GAMES_FOR_CHAMP_ANALYSIS:
            continue
        if len(data['wins_data']) < MIN_GAMES_PER_OUTCOME_FOR_ANALYSIS or \
           len(data['losses_data']) < MIN_GAMES_PER_OUTCOME_FOR_ANALYSIS:
            continue

        metrics_to_compare = [
            ("kda_ratio", "KDA Ratio", 0.25),
            ("cs_per_min", "CS/min", 0.12),      
            ("damage_per_min", "Daño/min", 0.18), 
            ("gold_per_min", "Oro/min", 0.12),   
            ("kp_percentage", "KP%", 0.18)       
        ]

        for metric_key, metric_name, diff_threshold in metrics_to_compare:
            avg_metric_wins = sum(m.get(metric_key, 0) for m in data['wins_data']) / len(data['wins_data']) if data['wins_data'] else 0
            avg_metric_losses = sum(m.get(metric_key, 0) for m in data['losses_data']) / len(data['losses_data']) if data['losses_data'] else 0

            if avg_metric_losses > 0.01 : 
                percentage_diff = (avg_metric_wins - avg_metric_losses) / avg_metric_losses
                if percentage_diff > diff_threshold: 
                    recommendations.append(
                        f"[INFO] Con {champ}, tu {metric_name} promedio en victorias ({avg_metric_wins:.1f}) " # Cambiado a INFO
                        f"es notablemente mayor que en derrotas ({avg_metric_losses:.1f}). "
                        f"Enfocarte en esta métrica podría ser beneficioso con este campeón."
                    )
            elif avg_metric_wins > (avg_metric_losses + 0.1) and avg_metric_losses <= 0.01 : 
                 recommendations.append(
                        f"[INFO] Con {champ}, tu {metric_name} promedio en victorias es de ({avg_metric_wins:.1f}), " # Cambiado a INFO
                        f"mientras que es muy bajo en derrotas. "
                        f"Conseguir un buen {metric_name} parece crucial para ganar con {champ}."
                    )
    return recommendations

# --- Funciones para Machine Learning (Nivel 2) ---

def generate_ml_insights_for_champion(champion_stats, champion_name):
    """Entrena un Árbol de Decisión simple para un campeón y extrae insights."""
    insights = []
    MIN_SAMPLES_FOR_ML = 10 
    if not champion_stats or len(champion_stats) < MIN_SAMPLES_FOR_ML:
        return insights
    try:
        df = pd.DataFrame(champion_stats)
        features = ['kda_ratio', 'cs_per_min', 'damage_per_min', 'gold_per_min', 'kp_percentage', 'vision_score_per_min']
        target = 'win'

        valid_features_in_df = []
        for feature in features:
            if feature not in df.columns:
                continue 
            df[feature] = pd.to_numeric(df[feature], errors='coerce')
            valid_features_in_df.append(feature)
        
        if not valid_features_in_df: return insights

        df_cleaned = df[valid_features_in_df + [target]].copy()
        df_cleaned.dropna(inplace=True)

        if len(df_cleaned) < MIN_SAMPLES_FOR_ML or \
           (target in df_cleaned and len(df_cleaned[target].unique()) < 2):
            return insights

        X = df_cleaned[valid_features_in_df]
        y = df_cleaned[target].astype(int)

        model = DecisionTreeClassifier(max_depth=3, random_state=42, min_samples_leaf=max(2, int(len(X)*0.1)) ) 
        model.fit(X, y)

        importances = model.feature_importances_
        feature_importance_map = sorted(zip(valid_features_in_df, importances), key=lambda x: x[1], reverse=True)

        if feature_importance_map:
            most_important_feature, importance_score = feature_importance_map[0]
            if importance_score > 0.20: 
                avg_metric_wins = df_cleaned[df_cleaned['win'] == 1][most_important_feature].mean()
                avg_metric_losses = df_cleaned[df_cleaned['win'] == 0][most_important_feature].mean()

                if not pd.isna(avg_metric_wins) and not pd.isna(avg_metric_losses):
                    insight_text = f"[INFO] Análisis de IA para {champion_name}: Tu '{most_important_feature}' parece ser un factor muy influyente. "
                    if avg_metric_wins > avg_metric_losses * 1.10: 
                        insight_text += (f"En tus victorias, tu promedio es {avg_metric_wins:.2f}, mientras que en derrotas es {avg_metric_losses:.2f}. "
                                         f"Un buen rendimiento en esta métrica parece estar asociado a tus victorias.")
                    else:
                        insight_text += (f"Esta métrica ({most_important_feature}) es la que más destaca el modelo, con un promedio de {avg_metric_wins:.2f} en victorias y {avg_metric_losses:.2f} en derrotas. Reflexiona sobre cómo impacta en tus partidas.")
                    insights.append(insight_text)
    except Exception as e:
        print(f"Error generando insight de ML (Árbol de Decisión) para {champion_name}: {e}")
        traceback.print_exc()
    
    return insights


def get_ml_recommendations(stats_list, min_games_for_champion=10):
    """Genera recomendaciones basadas en Árbol de Decisión para campeones jugados frecuentemente."""
    ml_recommendations = []
    if not stats_list or len(stats_list) < min_games_for_champion : 
        return ml_recommendations 

    all_champ_stats = {}
    for match_stats in stats_list:
        champ_name = match_stats.get("champion")
        if not champ_name or champ_name == "N/A":
            continue
        if champ_name not in all_champ_stats:
            all_champ_stats[champ_name] = []
        all_champ_stats[champ_name].append(match_stats)
    
    champions_analyzed_count = 0
    sorted_champs = sorted(all_champ_stats.items(), key=lambda item: len(item[1]), reverse=True)

    for champion_name, champion_specific_stats in sorted_champs:
        if len(champion_specific_stats) >= min_games_for_champion:
            insights = generate_ml_insights_for_champion(champion_specific_stats, champion_name)
            ml_recommendations.extend(insights)
            champions_analyzed_count +=1
            if champions_analyzed_count >= 1 : 
                break 
                
    return ml_recommendations


def analyze_playstyle_with_clustering(stats_list, num_clusters=3, min_games_for_clustering=15):
    """Analiza las partidas recientes para identificar estilos de juego usando K-Means."""
    playstyle_insights = []

    if not stats_list or len(stats_list) < min_games_for_clustering:
        # No añadir mensaje aquí, la plantilla lo maneja si la lista está vacía.
        return playstyle_insights

    features_for_clustering = [
        'kda_ratio', 'cs_per_min', 'damage_per_min', 'gold_per_min', 
        'kp_percentage', 'vision_score_per_min'
    ]
    try:
        df = pd.DataFrame(stats_list)
        valid_features = []
        for feature in features_for_clustering:
            if feature in df.columns:
                df[feature] = pd.to_numeric(df[feature], errors='coerce')
                valid_features.append(feature)
        
        if not valid_features or len(valid_features) < 3:
            return ["[INFO] Faltan datos clave o suficientes características para el análisis de estilos de juego."]
            
        df_clustering_clean = df[valid_features].copy()
        df_clustering_clean.dropna(inplace=True)

        if len(df_clustering_clean) < min_games_for_clustering: 
            return [f"[INFO] No hay suficientes partidas con datos completos después de la limpieza ({len(df_clustering_clean)}, se necesitan {min_games_for_clustering}) para identificar estilos de juego."]
        
        n_samples_unique = len(np.unique(df_clustering_clean.values, axis=0))
        effective_num_clusters = min(num_clusters, n_samples_unique)

        if effective_num_clusters < 2: 
             return [f"[INFO] No hay suficientes datos variados ({n_samples_unique} partidas únicas analizables) para identificar múltiples estilos de juego."]

        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(df_clustering_clean)
        
        kmeans = KMeans(n_clusters=effective_num_clusters, random_state=42, n_init='auto', algorithm='lloyd')
        cluster_labels = kmeans.fit_predict(scaled_features)
        
        df_original_with_clusters = df_clustering_clean.copy() 
        df_original_with_clusters['cluster_label'] = cluster_labels

        playstyle_insights.append(f"[INFO] Análisis de Estilo de Juego (basado en {len(df_clustering_clean)} partidas válidas, agrupadas en {effective_num_clusters} estilos):")
        
        archetypes = [
            {"name": "Carry Dominante / Alto Impacto", "profile": {'kda_ratio': 'muy_alto', 'damage_per_min': 'alto', 'gold_per_min': 'alto', 'kp_percentage': 'alto'}, "tip": "¡Estas son tus mejores partidas! Intenta replicar las condiciones que te llevan a este estado."},
            {"name": "Jugador de Equipo Participativo", "profile": {'kp_percentage': 'muy_alto', 'vision_score_per_min':'alto', 'kda_ratio': 'promedio'}, "tip": "Tu alta participación es valiosa, asegúrate de que se traduzca en ventajas y objetivos para tu equipo."},
            {"name": "Especialista en Farmeo", "profile": {'cs_per_min': 'muy_alto', 'gold_per_min': 'alto', 'kp_percentage': 'bajo'}, "tip": "Un farmeo sólido te da una gran base de oro. Considera si puedes transferir esta ventaja al resto del mapa un poco antes."},
            {"name": "Fase Difícil / Juego de Recuperación", "profile": {'kda_ratio': 'muy_bajo', 'gold_per_min': 'bajo', 'damage_per_min': 'bajo'}, "tip": "En estas partidas parece que te costó arrancar. Analiza si podrías haber jugado más seguro o haber buscado ayuda para recuperarte."}
        ]

        def get_tendency_label(scaled_value):
            if scaled_value > 1.0: return 'muy_alto'
            if scaled_value > 0.4: return 'alto'
            if scaled_value < -1.0: return 'muy_bajo'
            if scaled_value < -0.4: return 'bajo'
            return 'promedio'

        for i in range(effective_num_clusters):
            current_cluster_data_df = df_original_with_clusters[df_original_with_clusters['cluster_label'] == i]
            cluster_size = len(current_cluster_data_df)
            if cluster_size == 0: continue 

            percentage_of_games = (cluster_size / len(df_clustering_clean)) * 100
            
            scaled_centroid_for_cluster_i = kmeans.cluster_centers_[i]
            cluster_feature_tendencies = {} 
            for idx, feature_name in enumerate(valid_features):
                cluster_feature_tendencies[feature_name] = get_tendency_label(scaled_centroid_for_cluster_i[idx])

            best_match_name = None
            best_match_archetype_tip = None
            max_matching_metrics = 0
            best_match_descriptive_parts = []

            for archetype in archetypes:
                match_count = 0
                current_archetype_metric_descriptions = []
                for metric, expected_tendency in archetype["profile"].items():
                    if metric in cluster_feature_tendencies and cluster_feature_tendencies[metric] == expected_tendency:
                        match_count += 1
                        original_avg_val = current_cluster_data_df[metric].mean()
                        current_archetype_metric_descriptions.append(f"{metric} {expected_tendency.replace('_',' ')} ({original_avg_val:.1f})")
                
                if match_count >= 2 and match_count > max_matching_metrics: 
                    max_matching_metrics = match_count
                    best_match_name = archetype["name"]
                    best_match_descriptive_parts = current_archetype_metric_descriptions
                    best_match_archetype_tip = archetype.get("tip", "")


            insight_line = f"[INFO] **{best_match_name if best_match_name else f'Estilo {i+1}'}** ({percentage_of_games:.0f}% de partidas)."
            if best_match_descriptive_parts:
                insight_line += " Se caracteriza por: " + ", ".join(best_match_descriptive_parts) + "."
            elif not best_match_name : 
                fallback_desc_parts = []
                feature_deviations_fallback = sorted(
                    [(name, cluster_feature_tendencies[name], current_cluster_data_df[name].mean()) for name in valid_features],
                    key=lambda x: abs(kmeans.cluster_centers_[i, valid_features.index(x[0])]),
                    reverse=True
                )
                for k_feat, k_tend, k_orig_val in feature_deviations_fallback[:2]:
                    if k_tend != 'promedio':
                         fallback_desc_parts.append(f"{k_feat} {k_tend.replace('_',' ')} ({k_orig_val:.1f})")
                if fallback_desc_parts:
                    insight_line += " Características notables: " + ", ".join(fallback_desc_parts) + "."
                else:
                    insight_line += " Un perfil de juego con métricas equilibradas."
            
            if best_match_archetype_tip: # Añadir el consejo del arquetipo si existe
                insight_line += f" {best_match_archetype_tip}"

            playstyle_insights.append(insight_line)
        
        if len(playstyle_insights) <= 1 : 
             playstyle_insights = ["[INFO] No se pudieron identificar estilos de juego claramente diferenciados con los datos actuales."]

    except Exception as e:
        print(f"Error crítico durante el análisis de clustering de estilo de juego: {e}")
        traceback.print_exc() 
        playstyle_insights.append("[INFO] Ocurrió un error al intentar analizar tus estilos de juego.")

    return playstyle_insights


# --- Función Principal para Recomendaciones Basadas en Reglas (Nivel 1 y Estadístico Avanzado) ---
def rule_based_recommendations(stats_list):
    if not stats_list or len(stats_list) < 3 : 
        return ["Juega más partidas para que podamos analizar tu rendimiento y ofrecerte recomendaciones personalizadas."]
    all_recommendations = []
    all_recommendations.extend(analyze_overall_winrate_and_streaks(stats_list))
    all_recommendations.extend(analyze_champion_performance(stats_list))
    all_recommendations.extend(analyze_farming_cs_per_min(stats_list))
    all_recommendations.extend(analyze_kill_participation(stats_list))
    all_recommendations.extend(analyze_vision_score(stats_list))
    all_recommendations.extend(analyze_champion_specific_win_factors(stats_list))
    
    unique_recommendations = []
    seen_recommendations = set()
    for rec in all_recommendations:
        if rec not in seen_recommendations:
            unique_recommendations.append(rec)
            seen_recommendations.add(rec)
    
    max_recommendations = 4 
    if not unique_recommendations and len(stats_list) >= 5: 
        return ["[POSITIVE] ¡Buen trabajo! No hemos detectado patrones negativos significativos en tus últimas partidas según nuestros criterios actuales."]
    elif not unique_recommendations:
         return ["Aún estamos analizando tu juego. Juega algunas partidas más para obtener un informe más detallado."]

    if len(unique_recommendations) > max_recommendations:
        final_recommendations = unique_recommendations[:max_recommendations]
        final_recommendations.append("[INFO] Hemos encontrado más áreas de mejora. ¡Concéntrate en estas por ahora!")
    else:
        final_recommendations = unique_recommendations
    return final_recommendations