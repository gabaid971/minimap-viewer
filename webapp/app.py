"""
Webapp Flask pour visualiser les positions des joueurs sur la minimap
"""

from flask import Flask, render_template, jsonify, request
from pathlib import Path
import polars as pl
import json
from dataclasses import dataclass
from typing import Optional, List, Dict

# === WARD TRACKING ===

WARD_DURATIONS = {
    'YELLOW_TRINKET': 90000,  # 90 secondes
    'SIGHT_WARD': 150000,      # 150 secondes (2m30)
    'CONTROL_WARD': None,      # Permanent jusqu'à destruction
    'UNDEFINED': 2000          # 2 secondes (Farsight Alteration / Zombie Wards / Ghost Poro)
}

@dataclass
class Ward:
    """Représente une ward placée"""
    creator_id: int
    champion: str
    team: int
    ward_type: str
    placed_at: int  # timestamp en ms
    position_x: float
    position_y: float
    expires_at: Optional[int]  # None si permanent (control ward)
    destroyed_at: Optional[int] = None
    
    def is_active(self, timestamp: int) -> bool:
        """Vérifie si la ward est active à un timestamp donné"""
        if self.destroyed_at and timestamp >= self.destroyed_at:
            return False
        if self.expires_at and timestamp >= self.expires_at:
            return False
        return timestamp >= self.placed_at


class WardTracker:
    """Tracker de wards avec interpolation de position"""
    
    def __init__(self, timeline_data: dict, champion_names: Dict[int, str] = None):
        self.timeline_data = timeline_data
        self.frames = timeline_data.get('info', {}).get('frames', [])
        self.champion_names = champion_names or {}
        self.wards: List[Ward] = []
        self._build_ward_list()
    
    def _get_player_position_at_time(self, participant_id: int, target_time: int) -> Optional[tuple]:
        """Interpole la position d'un joueur au moment du placement de ward"""
        closest_frame = None
        min_time_diff = float('inf')
        
        for frame in self.frames:
            frame_time = frame['timestamp']
            time_diff = abs(frame_time - target_time)
            
            if time_diff < min_time_diff:
                min_time_diff = time_diff
                closest_frame = frame
        
        if closest_frame and min_time_diff < 60000:  # Max 60s de différence
            pf = closest_frame.get('participantFrames', {}).get(str(participant_id), {})
            pos = pf.get('position', {})
            
            if 'x' in pos and 'y' in pos:
                return (pos['x'], pos['y'])
        
        return None
    
    def _get_champion_name(self, participant_id: int) -> str:
        """Récupère le nom du champion d'un participant"""
        return self.champion_names.get(participant_id, f'Player{participant_id}')
    
    def _build_ward_list(self):
        """Construit la liste complète des wards avec positions interpolées"""
        ward_placements = []
        ward_kills = []
        
        # Extraire tous les events
        for frame in self.frames:
            for event in frame.get('events', []):
                if event.get('type') == 'WARD_PLACED':
                    ward_placements.append(event)
                elif event.get('type') == 'WARD_KILL':
                    ward_kills.append(event)
        
        # Créer les wards avec positions interpolées
        for event in ward_placements:
            creator_id = event.get('creatorId')
            placed_at = event.get('timestamp')
            ward_type = event.get('wardType', 'UNDEFINED')
            
            # Ignorer les wards UNDEFINED (Farsight Alteration / trinket bleue)
            # Ces wards ne durent que 2 secondes et ne sont pas pertinentes pour le fog of war
            if ward_type == 'UNDEFINED':
                continue
            
            # Interpoler la position
            position = self._get_player_position_at_time(creator_id, placed_at)
            
            if position:
                team = 100 if creator_id <= 5 else 200
                champion = self._get_champion_name(creator_id)
                
                duration = WARD_DURATIONS.get(ward_type)
                expires_at = (placed_at + duration) if duration else None
                
                ward = Ward(
                    creator_id=creator_id,
                    champion=champion,
                    team=team,
                    ward_type=ward_type,
                    placed_at=placed_at,
                    position_x=position[0],
                    position_y=position[1],
                    expires_at=expires_at
                )
                
                # Chercher si la ward a été détruite
                # Matcher par type de ward ET par ordre chronologique
                for kill_event in ward_kills:
                    kill_time = kill_event.get('timestamp')
                    kill_ward_type = kill_event.get('wardType', 'UNDEFINED')
                    
                    # Vérifier que c'est le bon type de ward
                    type_match = (kill_ward_type == ward_type) or (kill_ward_type == 'UNDEFINED' and ward_type == 'UNDEFINED')
                    
                    # Si destruction après placement et avant expiration
                    if type_match and kill_time > placed_at and kill_time < (expires_at or float('inf')):
                        # Vérifier que ce kill n'a pas déjà été assigné à une autre ward
                        already_used = any(w.destroyed_at == kill_time and w.ward_type == ward_type for w in self.wards)
                        
                        if not already_used:
                            ward.destroyed_at = kill_time
                            break
                
                self.wards.append(ward)
    
    def get_active_wards_at(self, timestamp: int) -> List[Ward]:
        """Retourne les wards actives à un timestamp donné"""
        return [w for w in self.wards if w.is_active(timestamp)]
    
    def get_wards_placed_in_window(self, start_time: int, end_time: int) -> List[Ward]:
        """Retourne les wards placées dans une fenêtre de temps"""
        return [w for w in self.wards if start_time <= w.placed_at < end_time]


app = Flask(__name__)

# Charger le dataset
DATASET_PATH = Path(__file__).parent.parent / 'data' / 'processed' / 'fog_dataset.csv'
df = None

def load_dataset():
    """Charger le dataset au démarrage"""
    global df
    if DATASET_PATH.exists():
        df = pl.read_csv(DATASET_PATH)
        print(f"✅ Dataset chargé: {df.height} positions")
    else:
        print(f"❌ Dataset non trouvé: {DATASET_PATH}")


@app.route('/')
def index():
    """Page principale"""
    return render_template('index.html')


@app.route('/api/matches')
def get_matches():
    """Liste des matchs disponibles avec infos"""
    if df is None:
        return jsonify({'error': 'Dataset non chargé'}), 500
    
    # Grouper par match
    matches = df.group_by('match_id').agg([
        pl.col('timestamp').max().alias('duration'),
        pl.col('timestamp').count().alias('frame_count')
    ]).sort('match_id')
    
    result = []
    for row in matches.iter_rows(named=True):
        result.append({
            'match_id': row['match_id'],
            'duration_ms': row['duration'],
            'duration_min': row['duration'] // 60000,
            'frame_count': row['frame_count'] // 10  # 10 joueurs par frame
        })
    
    return jsonify(result)


@app.route('/api/match/<match_id>/frames')
def get_match_frames(match_id):
    """Récupérer toutes les frames d'un match"""
    if df is None:
        return jsonify({'error': 'Dataset non chargé'}), 500
    
    # Paramètre team pour POV (100=blue, 200=red, all=tous)
    pov_team = request.args.get('team', 'all')
    
    # Filtrer par match
    match_data = df.filter(pl.col('match_id') == match_id).sort('timestamp')
    
    if match_data.height == 0:
        return jsonify({'error': 'Match non trouvé'}), 404
    
    # Charger la timeline pour tracker les wards
    matches_dir = Path(__file__).parent.parent / 'data' / 'riot_api' / 'matches'
    timeline_file = matches_dir / f"{match_id}_timeline.json"
    match_file = matches_dir / f"{match_id}.json"
    
    # Charger les noms des champions depuis le match data
    champion_names = {}
    if match_file.exists():
        with open(match_file) as f:
            match_full = json.load(f)
            participants = match_full.get('info', {}).get('participants', [])
            for i, participant in enumerate(participants):
                participant_id = i + 1  # participantId va de 1 à 10
                champion_names[participant_id] = participant.get('championName', f'Player{participant_id}')
    
    ward_tracker = None
    if timeline_file.exists():
        with open(timeline_file) as f:
            timeline_full = json.load(f)
            ward_tracker = WardTracker(timeline_full, champion_names)
    
    # Grouper par timestamp
    frames = []
    for timestamp in match_data.select('timestamp').unique().sort('timestamp').to_series():
        frame_data = match_data.filter(pl.col('timestamp') == timestamp)
        
        players = []
        for row in frame_data.iter_rows(named=True):
            # Ne plus filtrer côté backend - envoyer tous les joueurs
            # Le frontend gère le filtrage selon le POV
            players.append({
                'participant_id': row['participant_id'],
                'champion': row['champion'],
                'team': row['team'],
                'position': {
                    'x': row['position_x'],
                    'y': row['position_y']
                },
                'visible_to_enemy': row['visible_to_enemy'],
                'level': row['level'],
                'total_gold': row['total_gold']
            })
        
        # Informations sur les wards
        ward_info = {
            'active_wards': [],
            'blue_ward_count': 0,
            'red_ward_count': 0
        }
        
        if ward_tracker:
            # Wards actives au timestamp actuel
            active_wards = ward_tracker.get_active_wards_at(timestamp)
            ward_info['blue_ward_count'] = sum(1 for w in active_wards if w.team == 100)
            ward_info['red_ward_count'] = sum(1 for w in active_wards if w.team == 200)
            
            # Marquer les wards placées dans la dernière minute
            minute_start = max(0, timestamp - 60000)
            
            # Wards actives détaillées
            for ward in active_wards:
                is_new = ward.placed_at >= minute_start
                ward_info['active_wards'].append({
                    'creator_id': ward.creator_id,
                    'champion': ward.champion,
                    'team': ward.team,
                    'ward_type': ward.ward_type,
                    'placed_at': ward.placed_at,
                    'position': {'x': ward.position_x, 'y': ward.position_y},
                    'expires_at': ward.expires_at,
                    'destroyed_at': ward.destroyed_at,
                    'is_new': is_new  # Placée dans la dernière minute
                })
        
        frames.append({
            'timestamp': timestamp,
            'time_min': timestamp // 60000,
            'time_sec': (timestamp // 1000) % 60,
            'players': players,
            'wards': ward_info
        })
    
    return jsonify({
        'match_id': match_id,
        'frames': frames
    })


@app.route('/api/match/<match_id>/frame/<int:timestamp>')
def get_frame(match_id, timestamp):
    """Récupérer une frame spécifique"""
    if df is None:
        return jsonify({'error': 'Dataset non chargé'}), 500
    
    # Filtrer par match et timestamp
    frame_data = df.filter(
        (pl.col('match_id') == match_id) & 
        (pl.col('timestamp') == timestamp)
    )
    
    if frame_data.height == 0:
        return jsonify({'error': 'Frame non trouvée'}), 404
    
    players = []
    for row in frame_data.iter_rows(named=True):
        players.append({
            'participant_id': row['participant_id'],
            'champion': row['champion'],
            'team': row['team'],
            'position': {
                'x': row['position_x'],
                'y': row['position_y']
            },
            'visible_to_enemy': row['visible_to_enemy'],
            'level': row['level'],
            'total_gold': row['total_gold']
        })
    
    return jsonify({
        'timestamp': timestamp,
        'time_min': timestamp // 60000,
        'time_sec': (timestamp // 1000) % 60,
        'players': players
    })


if __name__ == '__main__':
    load_dataset()
    print("\n" + "="*80)
    print("🌐 MINIMAP VIEWER - Serveur Flask")
    print("="*80)
    print("📍 URL: http://localhost:5000")
    print("🎮 Ouvrir dans le navigateur pour visualiser les matchs")
    print("="*80 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
