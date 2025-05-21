# train_composition_model.py
import sqlite3
import pandas as pd
import os
import json # Para guardar los top features
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib
import numpy as np
import traceback

# Configuración de Rutas (ajusta si es necesario)
# Asumimos que este script se ejecuta desde la raíz del proyecto,
# y la carpeta 'instance' está en la raíz.
INSTANCE_FOLDER = 'instance'
DB_FILENAME = 'lol_smart_tracker.db'
DB_PATH = os.path.join(INSTANCE_FOLDER, DB_FILENAME)

MODEL_FILENAME = 'team_composition_predictor.joblib'
FEATURES_FILENAME = 'team_composition_features.joblib' # Para guardar la lista ordenada de campeones
TOP_FEATURES_FILENAME = 'top_champion_influencers.json' # Para guardar los N campeones más influyentes

def fetch_and_prepare_data():
    """
    Extrae datos de la BD, los procesa y crea características para el modelo de composición.
    Devuelve: X_features (DataFrame), y_target (Series), sorted_unique_champions (list)
    """
    if not os.path.exists(DB_PATH):
        print(f"Error: La base de datos no se encuentra en {os.path.abspath(DB_PATH)}")
        return None, None, None

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        # Query para obtener los datos necesarios
        query = """
        SELECT 
            pp.match_id,
            p.queue_id, 
            pp.team_id,
            pp.champion_name,
            pp.win 
        FROM participante_partida pp
        JOIN partida p ON pp.match_id = p.match_id
        WHERE p.queue_id IN (400, 420, 430, 440, 450) -- Ejemplo: Filtrar por modos de juego relevantes (Normales, Rankeds, ARAM)
        ORDER BY pp.match_id, pp.team_id;
        """
        
        raw_df = pd.read_sql_query(query, conn)
        
        if raw_df.empty:
            print("No se encontraron datos de partidas relevantes en la base de datos.")
            return None, None, None

        print(f"Datos crudos extraídos: {len(raw_df)} filas de participantes.")

        matches_data = []
        for match_id, group in raw_df.groupby('match_id'):
            blue_champs = sorted(list(group[group['team_id'] == 100]['champion_name'].unique()))
            red_champs = sorted(list(group[group['team_id'] == 200]['champion_name'].unique()))
            
            blue_team_win_series = group[group['team_id'] == 100]['win']
            blue_team_won = blue_team_win_series.iloc[0] if not blue_team_win_series.empty else None
            
            if len(blue_champs) == 5 and len(red_champs) == 5 and blue_team_won is not None:
                match_entry = {'match_id': match_id}
                for i in range(5):
                    match_entry[f'blue_champ_{i+1}'] = blue_champs[i]
                    match_entry[f'red_champ_{i+1}'] = red_champs[i]
                match_entry['blue_team_won'] = int(blue_team_won)
                matches_data.append(match_entry)
        
        if not matches_data:
            print("No hay suficientes partidas completas (5v5) para crear el dataset.")
            return None, None, None

        processed_df = pd.DataFrame(matches_data)
        print(f"Dataset de composiciones procesado con {len(processed_df)} partidas.")
        
        # Umbral mínimo de partidas para intentar entrenar
        if len(processed_df) < 20 : 
             print("Dataset demasiado pequeño para un entrenamiento significativo. Se necesitan al menos 20 partidas.")
             return None, None, None

        # --- Ingeniería de Características: "Bag of Champions" ---
        blue_champ_cols = [f'blue_champ_{i+1}' for i in range(5)]
        red_champ_cols = [f'red_champ_{i+1}' for i in range(5)]
        
        all_champions_in_dataset = set()
        for col in blue_champ_cols + red_champ_cols:
            all_champions_in_dataset.update(processed_df[col].dropna().unique())
        
        sorted_unique_champions = sorted(list(all_champions_in_dataset))
        if not sorted_unique_champions:
            print("No se encontraron nombres de campeones válidos en el dataset.")
            return None, None, None
        print(f"\nCampeones únicos para características ({len(sorted_unique_champions)}): {sorted_unique_champions[:10]}...")

        X_features = pd.DataFrame(0, index=processed_df.index, columns=sorted_unique_champions)

        for index, row in processed_df.iterrows():
            for champ_col in blue_champ_cols:
                champ = row[champ_col]
                if pd.notna(champ) and champ in X_features.columns:
                    X_features.loc[index, champ] = 1 
            for champ_col in red_champ_cols:
                champ = row[champ_col]
                if pd.notna(champ) and champ in X_features.columns:
                    X_features.loc[index, champ] = -1 
        
        y_target = processed_df['blue_team_won'].astype(int)
        
        print(f"\nDimensiones de X_features: {X_features.shape}")
        print(f"Dimensiones de y_target: {y_target.shape}")
        # print("\nPrimeras 5 filas de X_features transformadas:")
        # print(X_features.head())
        
        return X_features, y_target, sorted_unique_champions

    except sqlite3.Error as e:
        print(f"Error de base de datos al extraer datos: {e}")
        return None, None, None
    except Exception as e:
        print(f"Error inesperado durante la preparación de datos: {e}")
        traceback.print_exc()
        return None, None, None
    finally:
        if conn:
            conn.close()

def train_model(X, y):
    if X is None or y is None or X.empty or y.empty:
        print("No hay datos válidos para entrenar el modelo.")
        return None

    if len(y.unique()) < 2:
        print("Advertencia: El conjunto de datos solo contiene una clase de resultado (todas victorias o todas derrotas). El modelo no será útil.")
        print(f"Distribución de clases: {y.value_counts()}")
        return None
    
    min_class_count = y.value_counts().min()
    test_size = 0.2 
    
    if len(X) < 20: 
        test_size = 0.1 
    # Para estratificar, cada clase debe tener al menos n_splits (por defecto 5 para CV, pero para train_test_split es 1)
    # Aquí, más importante, para que el reporte de clasificación sea útil, test set debe tener ambas clases.
    stratify_option = y if min_class_count > 1 else None # Solo estratificar si ambas clases tienen más de 1 muestra

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42, stratify=stratify_option)
    
    print(f"\nForma de X_train: {X_train.shape}, Forma de y_train: {y_train.shape}")
    print(f"Forma de X_test: {X_test.shape}, Forma de y_test: {y_test.shape}")

    if len(y_train.unique()) < 2:
        print("Advertencia: El conjunto de entrenamiento solo contiene una clase de resultado después de la división. El modelo no será útil.")
        return None
    if X_test.empty : # Si el test set quedó vacío por pocos datos
         print("Advertencia: El conjunto de prueba está vacío. No se puede evaluar el modelo de forma estándar.")
         # Podríamos entrenar con todo y no evaluar, o evaluar sobre el de entrenamiento (no ideal)
         # Por ahora, no entrenamos si no podemos evaluar de forma mínima.
         return None

    # Ajustar min_samples_split y min_samples_leaf para datasets pequeños
    min_samples_split_val = max(2, int(len(X_train) * 0.05)) if len(X_train) >= 40 else 2
    min_samples_leaf_val = max(1, int(len(X_train) * 0.02)) if len(X_train) >= 50 else 1

    model = RandomForestClassifier(
        n_estimators=100, 
        random_state=42, 
        class_weight='balanced_subsample' if len(y_train.unique()) > 1 else None,
        min_samples_split=min_samples_split_val,
        min_samples_leaf=min_samples_leaf_val
    )
    model.fit(X_train, y_train)
    print("\n✅ Modelo entrenado.")

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\nPrecisión en el conjunto de prueba: {accuracy:.2f}")
    
    if len(y_test.unique()) > 1: # Solo mostrar reporte si hay ambas clases en el test set
         print("Reporte de Clasificación en conjunto de prueba:")
         print(classification_report(y_test, y_pred, zero_division=0))
    else:
        print("Solo una clase en el conjunto de prueba, no se puede generar reporte de clasificación completo.")
        print(f"Clase única en y_test: {y_test.unique()}, Predicciones: {np.unique(y_pred, return_counts=True)}")


    return model

if __name__ == '__main__':
    print("--- Iniciando Script de Entrenamiento del Modelo de Composición de Equipos ---")
    X_features, y_target, champion_list_for_features = fetch_and_prepare_data()
    
    if X_features is not None and y_target is not None and champion_list_for_features is not None:
        trained_model = train_model(X_features, y_target)
        if trained_model:
            joblib.dump(trained_model, MODEL_FILENAME)
            print(f"\n✅ Modelo guardado como: {MODEL_FILENAME}")
            joblib.dump(champion_list_for_features, FEATURES_FILENAME)
            print(f"✅ Lista de campeones (para orden de características) guardada como: {FEATURES_FILENAME}")

            if hasattr(trained_model, 'feature_importances_'):
                importances = trained_model.feature_importances_
                feature_importance_df = pd.DataFrame({
                    'feature': champion_list_for_features, 
                    'importance': importances
                })
                feature_importance_df = feature_importance_df.sort_values(by='importance', ascending=False)
                
                top_n = 10
                top_features_data = feature_importance_df.head(top_n).to_dict(orient='records')
                
                try:
                    with open(TOP_FEATURES_FILENAME, 'w') as f:
                        json.dump(top_features_data, f, indent=4)
                    print(f"✅ Top {top_n} características más importantes guardadas en: {TOP_FEATURES_FILENAME}")
                    print("\nImportancia de Características del Modelo de Composición (Top 10):")
                    print(feature_importance_df.head(top_n))
                except Exception as e:
                    print(f"❌ Error al guardar las top características: {e}")
            else:
                print("⚠️ El modelo entrenado no tiene el atributo 'feature_importances_'.")
        else:
            print("\n❌ No se pudo entrenar el modelo (posiblemente debido a datos insuficientes o no variados).")
    else:
        print("\nNo se generaron datos suficientes o válidos para el entrenamiento del modelo.")
    print("\n--- Script de Entrenamiento Finalizado ---")