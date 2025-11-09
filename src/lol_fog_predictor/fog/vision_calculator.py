"""Fog of War vision calculator for League of Legends."""

import numpy as np
from typing import List, Tuple, Dict

VISION_RADIUS = 1200  # Units de vision standard dans LoL


def distance(pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
    """Calculate Euclidean distance between two positions."""
    return np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)


def calculate_fog_of_war(
    ally_positions: List[Dict],
    enemy_positions: List[Dict],
    wards: List[Dict] = None
) -> Tuple[List[Dict], List[Dict]]:
    """
    Détermine quels ennemis sont visibles depuis positions alliées + wards.
    
    Args:
        ally_positions: Liste de positions alliées [{"pos": [x, y], ...}, ...]
        enemy_positions: Liste de positions ennemies
        wards: Liste de wards optionnelle [{"pos": [x, y], ...}, ...]
    
    Returns:
        (visible_enemies, hidden_enemies): Tuple de listes
    """
    if wards is None:
        wards = []
    
    visible = []
    hidden = []
    
    for enemy in enemy_positions:
        is_visible = False
        enemy_pos = tuple(enemy['pos'])
        
        # Check vision depuis alliés
        for ally in ally_positions:
            ally_pos = tuple(ally['pos'])
            if distance(ally_pos, enemy_pos) < VISION_RADIUS:
                is_visible = True
                break
        
        # Check vision depuis wards
        if not is_visible:
            for ward in wards:
                ward_pos = tuple(ward['pos'])
                if distance(ward_pos, enemy_pos) < VISION_RADIUS:
                    is_visible = True
                    break
        
        if is_visible:
            visible.append(enemy)
        else:
            hidden.append(enemy)
    
    return visible, hidden
