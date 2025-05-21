# prepare_ml_data.py
import sqlite3
import pandas as pd
import os

# Configuración de la base de datos
# Asegúrate de que esta ruta sea correcta según dónde ejecutes el script
# Si ejecutas desde la raíz del proyecto, y 'instance' está en la raíz:
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

        # Query para obtener los campeones de cada equipo y quién ganó
        # Asumimos que team_id 100 es azul y 200 es rojo.
        # Y que la tabla 'partida' tiene un campo 'game_mode_name' o 'queue_id'
        # para poder filtrar por modos de juego relevantes si es necesario.
        # También necesitamos saber qué equipo ganó. Podemos inferirlo si un participante del equipo azul ganó.
        
        # Esta query es compleja porque necesitamos pivotar los participantes en columnas por equipo.
        # Una forma más simple es obtener todos los participantes por partida y luego procesar en Pandas.
        
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

        # Procesar los datos crudos para crear un DataFrame con una fila por partida
        # Columnas: match_id, blue_champ1, blue_champ2, ..., blue_champ5, 
        #                     red_champ1, ..., red_champ5, blue_team_won (1 o 0)

        matches_dict = {} 
        # { 
        #   match_id1: {
        #     'blue_champs': [champA, champB,...], 
        #     'red_champs': [champC, champD,...], 
        #     'blue_team_won': 1/0 
        #   }, ... 
        # }

        for row in raw_data:
            match_id, team_id, champion_name, win_status = row
            
            if match_id not in matches_dict:
                matches_dict[match_id] = {
                    'blue_champs': [], 
                    'red_champs': [],
                    'blue_team_won': None # Se determinará por el primer participante del equipo azul
                }
            
            if team_id == 100: # Equipo Azul
                if len(matches_dict[match_id]['blue_champs']) < 5:
                    matches_dict[match_id]['blue_champs'].append(champion_name)
                if matches_dict[match_id]['blue_team_won'] is None: # Asignar resultado del equipo azul
                    matches_dict[match_id]['blue_team_won'] = 1 if win_status else 0
            elif team_id == 200: # Equipo Rojo
                if len(matches_dict[match_id]['red_champs']) < 5:
                    matches_dict[match_id]['red_champs'].append(champion_name)
        
        # Convertir a una lista de diccionarios para el DataFrame final
        dataset_list = []
        for match_id, data in matches_dict.items():
            # Solo incluir partidas con 5 campeones por equipo y resultado claro
            if len(data['blue_champs']) == 5 and len(data['red_champs']) == 5 and data['blue_team_won'] is not None:
                row_data = {'match_id': match_id}
                for i, champ in enumerate(sorted(data['blue_champs'])): # Ordenar para consistencia
                    row_data[f'blue_champ_{i+1}'] = champ
                for i, champ in enumerate(sorted(data['red_champs'])): # Ordenar para consistencia
                    row_data[f'red_champ_{i+1}'] = champ
                row_data['blue_team_won'] = data['blue_team_won']
                dataset_list.append(row_data)
        
        if not dataset_list:
            print("No hay suficientes partidas completas (5v5) para crear el dataset.")
            return None

        df = pd.DataFrame(dataset_list)
        
        # Reordenar columnas para que 'blue_team_won' esté al final (típico para target)
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
        # Guardar el DataFrame en un archivo CSV para uso futuro
        output_path = 'lol_match_compositions_dataset.csv'
        composition_df.to_csv(output_path, index=False)
        print(f"\nDataset guardado en: {output_path}")
        print(f"Total de partidas en el dataset: {len(composition_df)}")
        print(f"Columnas: {composition_df.columns.tolist()}")
    else:
        print("No se generó ningún dataset.")