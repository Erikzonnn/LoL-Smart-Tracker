import sqlite3
import pandas as pd
import os

# Configuración de la base de datos
DB_PATH = os.path.join('instance', 'lol_smart_tracker.db') 

def fetch_data_for_composition_model():
    """
    Extrae datos de la base de datos y los prepara para un modelo
    de predicción basado en composición de equipos.
    """
    if not os.path.exists(DB_PATH):
        print(f"Error: La base de datos no se encuentra en {DB_PATH}")
        return None

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        query = """
        SELECT 
            p.match_id,
            pp.team_id,
            pp.champion_name,
            pp.win  -- Asumimos que 'win' en ParticipantePartida es el resultado del equipo de ese participante
        FROM partida p
        JOIN participante_partida pp ON p.match_id = pp.match_id
        -- Opcional: Filtrar por modos de juego si solo quieres ciertos tipos
        -- WHERE p.queue_id IN (400, 420, 430, 440) -- Ejemplo: Normales y Rankeds
        ORDER BY p.match_id, pp.team_id;
        """
        
        cursor.execute(query)
        raw_data = cursor.fetchall()
        
        if not raw_data:
            print("No se encontraron datos de partidas en la base de datos.")
            return None

        matches_dict = {} 

        for row in raw_data:
            match_id, team_id, champion_name, win_status = row
            
            if match_id not in matches_dict:
                matches_dict[match_id] = {
                    'blue_champs': [], 
                    'red_champs': [],
                    'blue_team_won': None 
                }
            
            if team_id == 100: # Equipo Azul
                if len(matches_dict[match_id]['blue_champs']) < 5:
                    matches_dict[match_id]['blue_champs'].append(champion_name)
                if matches_dict[match_id]['blue_team_won'] is None:
                    matches_dict[match_id]['blue_team_won'] = 1 if win_status else 0
            elif team_id == 200: # Equipo Rojo
                if len(matches_dict[match_id]['red_champs']) < 5:
                    matches_dict[match_id]['red_champs'].append(champion_name)
        
        # Convertir a una lista de diccionarios para el DataFrame final
        dataset_list = []
        for match_id, data in matches_dict.items():
            if len(data['blue_champs']) == 5 and len(data['red_champs']) == 5 and data['blue_team_won'] is not None:
                row_data = {'match_id': match_id}
                for i, champ in enumerate(sorted(data['blue_champs'])):
                    row_data[f'blue_champ_{i+1}'] = champ
                for i, champ in enumerate(sorted(data['red_champs'])):
                    row_data[f'red_champ_{i+1}'] = champ
                row_data['blue_team_won'] = data['blue_team_won']
                dataset_list.append(row_data)
        
        if not dataset_list:
            print("No hay suficientes partidas completas (5v5) para crear el dataset.")
            return None

        df = pd.DataFrame(dataset_list)
        
        cols = [col for col in df.columns if col != 'blue_team_won'] + ['blue_team_won']
        df = df[cols]
        
        print(f"Dataset creado con {len(df)} partidas.")
        print("Primeras 5 filas del dataset:")
        print(df.head())
        
        return df

    except sqlite3.Error as e:
        print(f"Error de base de datos al extraer datos: {e}")
        return None
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print("Iniciando script de preparación de datos para ML...")
    composition_df = fetch_data_for_composition_model()
    
    if composition_df is not None and not composition_df.empty:
        # Guardar el DataFrame en un archivo CSV
        output_path = 'lol_match_compositions_dataset.csv'
        composition_df.to_csv(output_path, index=False)
        print(f"\nDataset guardado en: {output_path}")
        print(f"Total de partidas en el dataset: {len(composition_df)}")
        print(f"Columnas: {composition_df.columns.tolist()}")
    else:
        print("No se generó ningún dataset.")