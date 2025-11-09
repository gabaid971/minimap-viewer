# 🎯 Ward Tracking System

## Vue d'ensemble

Le système de tracking de wards utilise l'interpolation de position pour déterminer où les wards ont été placées, en se basant sur les positions des joueurs aux timestamps les plus proches.

## Architecture

### 1. Classe `WardTracker` (webapp/app.py)

La classe principale qui gère tout le cycle de vie des wards.

```python
class WardTracker:
    - _get_player_position_at_time(): Interpole la position d'un joueur
    - _build_ward_list(): Construit la liste complète des wards
    - get_active_wards_at(): Retourne les wards actives à un timestamp
    - get_wards_placed_in_window(): Wards placées dans une fenêtre de temps
```

### 2. Dataclass `Ward`

Représente une ward avec toutes ses propriétés:

```python
@dataclass
class Ward:
    creator_id: int           # ID du joueur (1-10)
    champion: str             # Nom du champion
    team: int                 # 100 (bleue) ou 200 (rouge)
    ward_type: str            # YELLOW_TRINKET, CONTROL_WARD, SIGHT_WARD
    placed_at: int            # Timestamp de placement (ms)
    position_x: float         # Position X interpolée
    position_y: float         # Position Y interpolée
    expires_at: Optional[int] # Timestamp d'expiration (None si permanent)
    destroyed_at: Optional[int] # Timestamp de destruction (si applicable)
```

## Durées des Wards

```python
WARD_DURATIONS = {
    'YELLOW_TRINKET': 90000,   # 90 secondes
    'SIGHT_WARD': 150000,      # 150 secondes (2m30)
    'CONTROL_WARD': None,      # Permanent jusqu'à destruction
    'UNDEFINED': 90000         # Par défaut comme trinket
}
```

## Interpolation de Position

### Principe

L'API Riot Timeline ne fournit pas les positions des wards dans les événements WARD_PLACED. Nous utilisons donc une technique d'interpolation:

1. Un événement WARD_PLACED contient: `creatorId` et `timestamp`
2. On cherche la frame la plus proche de ce timestamp (< 60s)
3. On utilise la position du joueur à cette frame comme position approximative de la ward

### Exemple

```
Ward placée à t=47570ms par joueur 2
Frame 0: t=0ms      → position (662, 285)     [trop loin: -48s]
Frame 1: t=60028ms  → position (5988, 5020)   [✅ utilisée: +12s]
Frame 2: t=120041ms → position (9012, 2474)   [trop loin: +72s]
```

### Précision

- ✅ Précision temporelle: ±30 secondes en moyenne
- ✅ Précision spatiale: Bonne pour les wards placées à pied
- ⚠️ Moins précise pour les wards placées en déplacement rapide

## API Endpoints

### GET /api/match/<match_id>/frames

Retourne pour chaque frame:

```json
{
  "timestamp": 600000,
  "time_min": 10,
  "time_sec": 0,
  "players": [...],
  "wards": {
    "blue_ward_count": 3,
    "red_ward_count": 5,
    "active_wards": [
      {
        "creator_id": 2,
        "champion": "Ahri",
        "team": 100,
        "ward_type": "YELLOW_TRINKET",
        "placed_at": 540000,
        "position": {"x": 5988, "y": 5020},
        "expires_at": 630000,
        "destroyed_at": null
      }
    ],
    "wards_placed_this_minute": [
      {
        "creator_id": 4,
        "champion": "Lee Sin",
        "team": 100,
        "ward_type": "CONTROL_WARD",
        "placed_at": 580000,
        "position": {"x": 7500, "y": 6200}
      }
    ]
  }
}
```

## Interface Utilisateur

### Section Stats

- **Wards Bleues Actives**: Nombre de wards bleues actives au timestamp actuel
- **Wards Rouges Actives**: Nombre de wards rouges actives au timestamp actuel

### Section Détails des Wards

Affiche les wards placées dans la **dernière minute** (60 secondes avant le timestamp actuel):

- **Par équipe**: Séparation bleue/rouge
- **Informations affichées**:
  - Nom du champion
  - Type de ward (avec code couleur)
  - Timestamp de placement
  - Position interpolée (x, y)

### Codes Couleur

- 🟡 **YELLOW_TRINKET**: Jaune (#ffd700)
- 🔴 **CONTROL_WARD**: Rose (#ff1493)
- 🟢 **SIGHT_WARD**: Vert (#00ff00)

## Statistiques Exemple

Dans le match `EUW1_7596401539`:

- **Total wards placées**: 255
  - YELLOW_TRINKET: 133
  - UNDEFINED: 77
  - SIGHT_WARD: 38
  - CONTROL_WARD: 7

- **Distribution par équipe**:
  - Bleue: 84 wards
  - Rouge: 171 wards

- **Wards actives à 10min**: 3

## Améliorations Futures

1. **Visualisation sur la minimap**:
   - Dessiner les wards actives avec des icônes
   - Différencier les types visuellement
   - Afficher le temps restant

2. **Calcul du fog of war avec wards**:
   - Intégrer la vision des wards (900 unités)
   - Recalculer la visibilité des ennemis
   - Régénérer le dataset avec meilleure précision

3. **Tracking de destruction**:
   - Améliorer la correspondance WARD_KILL → ward spécifique
   - Utiliser la proximité spatiale + temporelle

4. **Vision des tourelles**:
   - Ajouter les positions fixes des tourelles
   - Vision radius ~1400 unités
   - Tracking de destruction via BUILDING_KILL events

## Tests

Pour tester le système:

```bash
# Démarrer le serveur
cd /home/gabaid/workspace/minimap-viewer
.venv/bin/python3 webapp/app.py

# Ouvrir dans le navigateur
http://localhost:5000

# Sélectionner un match et naviguer dans la timeline
# Les détails des wards s'affichent sous les stats
```

## Code Source

- **Backend**: `webapp/app.py` (lignes 10-135)
- **Frontend**: `webapp/templates/index.html` (lignes 200-250, 500-600)
- **Styles**: Intégré dans index.html (lignes 180-230)
