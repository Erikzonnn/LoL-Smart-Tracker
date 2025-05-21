# app/models.py
from .extensions import db # Importamos la instancia db desde extensions.py
from datetime import datetime

class Partida(db.Model):
    __tablename__ = 'partida' # Nombre de la tabla en la base de datos

    match_id = db.Column(db.String(100), primary_key=True) # Ej: "EUW1_1234567890"
    
    # Timestamp de creación de la partida (Unix timestamp en milisegundos de la API)
    # Lo guardaremos como BigInteger ya que puede ser un número grande.
    game_creation = db.Column(db.BigInteger) 
    
    game_duration = db.Column(db.Integer)    # Duración en segundos
    game_version = db.Column(db.String(50))  # Versión del juego/parche
    queue_id = db.Column(db.Integer)
    game_mode_name = db.Column(db.String(100)) # Nombre legible del modo de juego (ej. "Ranked Solo/Duo")
    
    # Fecha en que se guardó este registro en nuestra BD
    fecha_guardado = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación uno-a-muchos con ParticipantePartida
    # 'participantes' permitirá acceder a la lista de objetos ParticipantePartida asociados a esta Partida
    # 'backref='partida_obj'' permitirá a una instancia de ParticipantePartida acceder al objeto Partida
    #   a través del atributo 'partida_obj'.
    # 'lazy=True' es el modo por defecto, significa que los participantes se cargarán cuando se acceda a ellos.
    # 'cascade="all, delete-orphan"' significa que si se borra una Partida, 
    #   se borrarán todos los ParticipantePartida asociados.
    participantes = db.relationship('ParticipantePartida', 
                                    backref=db.backref('partida_obj', lazy=True), 
                                    lazy=True, 
                                    cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Partida {self.match_id}>'

class ParticipantePartida(db.Model):
    __tablename__ = 'participante_partida'

    id = db.Column(db.Integer, primary_key=True) # ID autoincremental para esta tabla, buena práctica
    match_id = db.Column(db.String(100), db.ForeignKey('partida.match_id'), nullable=False, index=True)
    
    participant_puuid = db.Column(db.String(100), index=True, nullable=False) 
    summoner_name = db.Column(db.String(100)) # El nombre del invocador en esa partida (de riotIdGameName)
    
    champion_name = db.Column(db.String(50))
    team_id = db.Column(db.Integer) # 100 para azul, 200 para rojo
    win = db.Column(db.Boolean)
    
    # Estadísticas de rendimiento
    kills = db.Column(db.Integer)
    deaths = db.Column(db.Integer)
    assists = db.Column(db.Integer)
    kda_ratio = db.Column(db.Float)
    cs = db.Column(db.Integer)
    cs_per_min = db.Column(db.Float)
    gold_earned = db.Column(db.Integer)
    gold_per_min = db.Column(db.Float)
    total_damage_to_champions = db.Column(db.Integer)
    damage_per_min = db.Column(db.Float)
    vision_score = db.Column(db.Integer)
    vision_score_per_min = db.Column(db.Float)
    kp_percentage = db.Column(db.Float) # Kill Participation
    
    role = db.Column(db.String(50)) # TOP, MIDDLE, JUNGLE, BOTTOM, UTILITY (o N/A)

    # Items: guardamos los 7 IDs como un string separado por comas.
    item_ids_str = db.Column(db.String(200)) 

    # Hechizos: guardamos las claves de Data Dragon para las imágenes.
    spell1_key = db.Column(db.String(50))
    spell2_key = db.Column(db.String(50))

    # Runas: guardamos los nombres de archivo de los iconos de estilo de Community Dragon.
    primary_rune_style_icon_file = db.Column(db.String(100))
    secondary_rune_style_icon_file = db.Column(db.String(100))
    # Si quisieras guardar más detalles de runas (keystone, perks individuales),
    # podrías añadir más columnas o crear tablas relacionadas para ellas.

    def __repr__(self):
        return f'<Participante {self.summoner_name} ({self.champion_name}) en Partida {self.match_id}>'

# (Opcional) Tabla para los PUUIDs buscados y cuándo se actualizaron sus datos.
# class BusquedaUsuario(db.Model):
#     puuid = db.Column(db.String(100), primary_key=True)
#     game_name = db.Column(db.String(100))
#     tag_line = db.Column(db.String(10))
#     fecha_ultima_busqueda_api = db.Column(db.DateTime, default=datetime.utcnow)
#     # Podrías añadir más campos, como la última vez que se actualizaron sus partidas en tu BD.