from .extensions import db
from datetime import datetime

class Partida(db.Model):
    __tablename__ = 'partida'

    match_id = db.Column(db.String(100), primary_key=True) # Ej: "EUW1_1234567890"
    
    game_creation = db.Column(db.BigInteger) 
    
    game_duration = db.Column(db.Integer)
    game_version = db.Column(db.String(50))
    queue_id = db.Column(db.Integer)
    game_mode_name = db.Column(db.String(100))
    
    # Fecha en que se guardó este registro en la BD
    fecha_guardado = db.Column(db.DateTime, default=datetime.utcnow)
    
    participantes = db.relationship('ParticipantePartida', 
                                    backref=db.backref('partida_obj', lazy=True), 
                                    lazy=True, 
                                    cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Partida {self.match_id}>'

class ParticipantePartida(db.Model):
    __tablename__ = 'participante_partida'

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.String(100), db.ForeignKey('partida.match_id'), nullable=False, index=True)
    
    participant_puuid = db.Column(db.String(100), index=True, nullable=False) 
    summoner_name = db.Column(db.String(100)) # El nombre (riotIdGameName)
    
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
    
    role = db.Column(db.String(50)) # TOP, MIDDLE, JUNGLE, BOTTOM, UTILITY

    # Items
    item_ids_str = db.Column(db.String(200)) 

    # Hechizos
    spell1_key = db.Column(db.String(50))
    spell2_key = db.Column(db.String(50))

    # Runas
    primary_rune_style_icon_file = db.Column(db.String(100))
    secondary_rune_style_icon_file = db.Column(db.String(100))

    def __repr__(self):
        return f'<Participante {self.summoner_name} ({self.champion_name}) en Partida {self.match_id}>'