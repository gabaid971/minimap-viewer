"""
Processeur de timelines API Riot pour créer dataset ML fog of war
Extrait positions + calcule visibilité pour entraînement
"""

import json
import math
from pathlib import Path
from typing import List, Dict, Tuple
import polars as pl
from dataclasses import dataclass


# Constantes de vision League of Legends
VISION_RADIUS = 1200  # Vision standard d'un champion
WARD_VISION_RADIUS = 900  # Vision d'une ward
MAP_SIZE = 14820  # Taille de la map (0-14820 sur x et y)


@dataclass
class Position:
    """Position sur la carte"""
    x: float
    y: float
    
    def distance_to(self, other: 'Position') -> float:
        """Calculer distance euclidienne"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)


def load_timeline(timeline_path: Path) -> Dict:
    """Charger timeline depuis fichier JSON"""
    with open(timeline_path) as f:
        return json.load(f)


def load_match(match_path: Path) -> Dict:
    """Charger match details depuis fichier JSON"""
    with open(match_path) as f:
        return json.load(f)


def get_team_mapping(match_data: Dict) -> Dict[int, int]:
    """
    Mapper participant ID → team ID
    
    Returns:
        {1: 100, 2: 100, ..., 6: 200, ...}  # 100=Blue, 200=Red
    """
    participants = match_data['info']['participants']
    return {i+1: p['teamId'] for i, p in enumerate(participants)}


def extract_ward_positions(frame: Dict, team_id: int) -> List[Position]:
    """
    Extraire positions des wards placées par une équipe
    
    Les events WARD_PLACED donnent la position des wards actives
    
    Args:
        frame: Frame de timeline
        team_id: 100 (blue) ou 200 (red)
    
    Returns:
        Liste des positions de wards actives
    """
    ward_positions = []
    
    events = frame.get('events', [])
    
    for event in events:
        # Types de wards qui donnent de la vision
        if event.get('type') == 'WARD_PLACED':
            # Vérifier que c'est une ward de l'équipe
            creator_id = event.get('creatorId')
            if creator_id:
                # Les IDs 1-5 = blue (100), 6-10 = red (200)
                event_team = 100 if creator_id <= 5 else 200
                
                if event_team == team_id:
                    pos = event.get('position', {})
                    if 'x' in pos and 'y' in pos:
                        ward_positions.append(Position(x=pos['x'], y=pos['y']))
        
        # Les wards peuvent être détruites
        elif event.get('type') == 'WARD_KILL':
            # TODO: tracker destruction de wards pour précision
            # Pour l'instant on utilise snapshot par frame
            pass
    
    return ward_positions


def is_enemy_visible(
    enemy_pos: Position,
    ally_positions: List[Position],
    ward_positions: List[Position] = None,
    vision_radius: float = VISION_RADIUS
) -> bool:
    """
    Vérifier si un ennemi est visible par l'équipe alliée
    
    Prend en compte:
    - Vision des champions alliés (1200 unités)
    - Vision des wards alliées (900 unités)
    - TODO: Tourelles, plantes, etc.
    
    Args:
        enemy_pos: Position de l'ennemi
        ally_positions: Positions de tous les alliés
        ward_positions: Positions des wards alliées
        vision_radius: Rayon de vision champion (1200 par défaut)
    
    Returns:
        True si l'ennemi est visible, False si dans fog
    """
    # Vision des champions
    for ally_pos in ally_positions:
        if enemy_pos.distance_to(ally_pos) <= vision_radius:
            return True
    
    # Vision des wards
    if ward_positions:
        for ward_pos in ward_positions:
            if enemy_pos.distance_to(ward_pos) <= WARD_VISION_RADIUS:
                return True
    
    return False


def process_timeline_to_dataset(
    timeline_path: Path,
    match_path: Path,
    blue_team_perspective: bool = True
) -> pl.DataFrame:
    """
    Convertir timeline en dataset ML
    
    ⭐ FONCTION PRINCIPALE ⭐
    
    Pour chaque frame (60s):
        - Pour chaque joueur de l'équipe ROUGE (ennemis):
            - Position réelle (x, y)
            - Est-il visible par l'équipe BLEUE ? (fog of war)
            - Champion, timestamp, etc.
    
    Args:
        timeline_path: Chemin vers match_timeline.json
        match_path: Chemin vers match.json
        blue_team_perspective: Si True, calcule fog depuis perspective bleue
    
    Returns:
        DataFrame avec colonnes:
        - timestamp: Temps du jeu (ms)
        - participant_id: ID du joueur (1-10)
        - champion: Nom du champion
        - team: 100 (blue) ou 200 (red)
        - position_x: Position X
        - position_y: Position Y
        - visible_to_enemy: True si visible par l'équipe adverse
        - level: Niveau du champion
        - gold: Or total
    """
    
    # Charger données
    timeline_data = load_timeline(timeline_path)
    match_data = load_match(match_path)
    
    # Mapping participant → team
    team_mapping = get_team_mapping(match_data)
    
    # Mapping participant → champion
    participants = match_data['info']['participants']
    champion_mapping = {i+1: p['championName'] for i, p in enumerate(participants)}
    
    # Liste pour stocker toutes les lignes
    rows = []
    
    # Parcourir chaque frame (toutes les 60s)
    frames = timeline_data['info']['frames']
    
    for frame in frames:
        timestamp = frame['timestamp']
        participant_frames = frame['participantFrames']
        
        # Extraire positions de tous les joueurs
        all_positions = {}
        
        for participant_id_str, pf in participant_frames.items():
            participant_id = int(participant_id_str)
            
            # Certaines frames n'ont pas de position (joueur mort, etc.)
            if 'position' not in pf:
                continue
            
            pos = Position(
                x=pf['position']['x'],
                y=pf['position']['y']
            )
            
            all_positions[participant_id] = {
                'position': pos,
                'team': team_mapping[participant_id],
                'champion': champion_mapping[participant_id],
                'level': pf.get('level', 0),
                'totalGold': pf.get('totalGold', 0),
            }
        
        # Séparer équipes
        blue_positions = []
        red_positions = []
        
        for pid, data in all_positions.items():
            if data['team'] == 100:
                blue_positions.append(data['position'])
            else:
                red_positions.append(data['position'])
        
        # Extraire positions des wards
        blue_wards = extract_ward_positions(frame, team_id=100)
        red_wards = extract_ward_positions(frame, team_id=200)
        
        # Pour chaque joueur, calculer visibilité
        for participant_id, data in all_positions.items():
            team = data['team']
            pos = data['position']
            
            # Calculer si visible par l'équipe adverse
            if blue_team_perspective:
                # On s'intéresse aux ennemis ROUGES vus par BLEU
                if team == 200:  # Ennemi rouge
                    visible = is_enemy_visible(pos, blue_positions, blue_wards)
                else:  # Allié bleu (toujours visible pour soi)
                    visible = True
            else:
                # Perspective rouge (inverse)
                if team == 100:  # Ennemi bleu
                    visible = is_enemy_visible(pos, red_positions, red_wards)
                else:  # Allié rouge
                    visible = True
            
            # Ajouter ligne au dataset
            rows.append({
                'timestamp': timestamp,
                'participant_id': participant_id,
                'champion': data['champion'],
                'team': team,
                'position_x': pos.x,
                'position_y': pos.y,
                'visible_to_enemy': visible,
                'level': data['level'],
                'total_gold': data['totalGold'],
            })
    
    # Créer DataFrame Polars
    df = pl.DataFrame(rows)
    
    return df


def process_multiple_matches(
    matches_dir: Path,
    output_path: Path = Path('data/processed/fog_dataset.csv')
) -> pl.DataFrame:
    """
    Traiter plusieurs matchs et combiner en un seul dataset
    
    Args:
        matches_dir: Dossier contenant match.json + match_timeline.json
        output_path: Chemin de sortie du dataset combiné
    
    Returns:
        DataFrame combiné de tous les matchs
    """
    all_dfs = []
    
    # Trouver tous les fichiers timeline
    timeline_files = list(matches_dir.glob('*_timeline.json'))
    
    print(f"\n{'='*80}")
    print(f"📊 TRAITEMENT TIMELINES → DATASET ML")
    print(f"{'='*80}\n")
    
    for i, timeline_path in enumerate(timeline_files, 1):
        # Déduire le chemin du match correspondant
        match_id = timeline_path.stem.replace('_timeline', '')
        match_path = timeline_path.parent / f"{match_id}.json"
        
        if not match_path.exists():
            print(f"⚠️  {i}/{len(timeline_files)}: Match file manquant pour {match_id}")
            continue
        
        print(f"🎮 {i}/{len(timeline_files)}: {match_id}")
        
        try:
            df = process_timeline_to_dataset(timeline_path, match_path)
            
            # Ajouter colonne match_id pour tracking
            df = df.with_columns(pl.lit(match_id).alias('match_id'))
            
            all_dfs.append(df)
            
            # Stats
            total_positions = len(df)
            enemy_positions = df.filter(pl.col('team') == 200).height
            visible_enemies = df.filter((pl.col('team') == 200) & (pl.col('visible_to_enemy'))).height
            hidden_enemies = enemy_positions - visible_enemies
            
            print(f"   ✅ {total_positions} positions extraites")
            print(f"   👁️  Ennemis: {visible_enemies} visibles, {hidden_enemies} dans fog")
            print()
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}\n")
            continue
    
    if not all_dfs:
        print("❌ Aucun match traité avec succès")
        return pl.DataFrame()
    
    # Combiner tous les DataFrames
    combined_df = pl.concat(all_dfs)
    
    # Sauvegarder
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined_df.write_csv(output_path)
    
    print(f"\n{'='*80}")
    print(f"✅ DATASET CRÉÉ")
    print(f"{'='*80}\n")
    print(f"📁 Fichier: {output_path}")
    print(f"📊 Total: {len(combined_df):,} positions")
    print(f"🎮 Matchs: {len(all_dfs)}")
    print(f"\n📈 Statistiques fog of war:")
    
    enemies = combined_df.filter(pl.col('team') == 200)
    visible = enemies.filter(pl.col('visible_to_enemy') == True)
    hidden = enemies.filter(pl.col('visible_to_enemy') == False)
    
    print(f"   Positions ennemies: {enemies.height:,}")
    print(f"   ✅ Visibles: {visible.height:,} ({visible.height/enemies.height*100:.1f}%)")
    print(f"   🌫️  Dans fog: {hidden.height:,} ({hidden.height/enemies.height*100:.1f}%)")
    print()
    
    return combined_df


def analyze_dataset(df: pl.DataFrame):
    """Afficher statistiques détaillées du dataset"""
    
    print(f"\n{'='*80}")
    print(f"📊 ANALYSE DATASET")
    print(f"{'='*80}\n")
    
    print(f"Dimensions: {df.height:,} lignes × {df.width} colonnes")
    print(f"\nColonnes: {', '.join(df.columns)}")
    
    print(f"\n{'─'*80}")
    print("Distribution des équipes:")
    print(df.group_by('team').agg(pl.count()).sort('team'))
    
    print(f"\n{'─'*80}")
    print("Top 10 champions:")
    print(df.group_by('champion').agg(pl.count().alias('count')).sort('count', descending=True).head(10))
    
    print(f"\n{'─'*80}")
    print("Visibilité ennemis (team 200):")
    enemies = df.filter(pl.col('team') == 200)
    print(enemies.group_by('visible_to_enemy').agg(pl.count()))
    
    print(f"\n{'─'*80}")
    print("Statistiques positions:")
    print(df.select(['position_x', 'position_y']).describe())
    
    print(f"\n{'─'*80}")
    print("Échantillon de données:")
    print(df.head(10))
    print()


def main():
    """Test du processeur"""
    
    # Dossier contenant les matchs téléchargés
    matches_dir = Path('data/riot_api/matches')
    
    if not matches_dir.exists():
        print(f"❌ Dossier {matches_dir} non trouvé")
        print("💡 D'abord télécharger des matchs avec riot_api.py")
        return
    
    # Traiter tous les matchs
    df = process_multiple_matches(matches_dir)
    
    if df.height > 0:
        # Analyser le dataset
        analyze_dataset(df)


if __name__ == '__main__':
    main()
