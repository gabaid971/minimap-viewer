# 🎮 League of Legends Fog of War Prediction

Système de **Machine Learning** pour prédire les positions des joueurs ennemis cachés dans le fog of war de League of Legends.

## 📋 Architecture

```
minimap-viewer/
├── data/
│   ├── riot_api/
│   │   └── matches/         # Matchs téléchargés (JSON + timelines)
│   └── processed/
│       └── fog_dataset.csv  # Dataset avec positions + visibilité fog of war
├── src/lol_fog_predictor/
│   ├── api/
│   │   ├── riot_api.py          # Client API Riot Games
│   │   └── timeline_processor.py # Extraction dataset + calcul fog
│   ├── fog/                 # Simulateur fog of war
│   ├── ml/                  # Modèles ML
│   └── parser/              # Parser ROFL (obsolète)
├── webapp/
│   ├── app.py               # Flask backend avec WardTracker
│   ├── templates/
│   │   └── index.html       # Visualiseur minimap interactif
│   └── static/
│       └── img/minimap.png  # Image Summoner's Rift
└── scripts/                 # Scripts d'analyse
```

## 🚀 Installation

```bash
# Installer uv (si nécessaire)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Installer dépendances
uv sync

# Activer environnement
source .venv/bin/activate
```

## � Configuration API Riot Games

1. Créer un compte sur https://developer.riotgames.com/
2. Obtenir une clé de développement (expire toutes les 24h)
3. Créer `riot_api_key.txt` à la racine avec votre clé

## 📥 Télécharger des matchs

```bash
# Télécharger 5 matchs pour un joueur
python src/lol_fog_predictor/api/riot_api.py

# Les matchs sont sauvegardés dans data/riot_api/matches/
# Format: {match_id}.json + {match_id}_timeline.json
```

## 📊 Générer le dataset

```bash
# Extraire positions + calculer fog of war
python src/lol_fog_predictor/api/timeline_processor.py

# Génère data/processed/fog_dataset.csv
# Colonnes: timestamp, participant_id, champion, team, position_x, position_y, visible_to_enemy, level, total_gold, match_id
```

## 🖥️ Visualiseur Minimap

```bash
# Lancer le serveur Flask
python webapp/app.py

# Ouvrir http://localhost:5000
```

### Fonctionnalités

- **Navigation temporelle** : Slider + flèches + clavier (← →)
- **Visualisation positions** : Joueurs bleus (solides) / rouges (transparents si cachés)
- **Ward tracking** : 
  - Interpolation de position depuis mouvements joueurs
  - Tracking expiration (90s trinket, 150s sight, permanent control)
  - Destruction par matching de type
  - Sélection interactive avec cercle de vision (900 unités)
  - Highlight wards nouvelles (<1min) en doré
- **Stats** : Compteurs équipes, ennemis visibles/cachés, wards actives

## 🧠 Machine Learning (Planifié)

### Architecture : Heatmap Generation

- **Input** : Visibility map (148×148) + last_seen positions + team state + context
- **Model** : U-Net CNN (encoder-decoder)
- **Output** : Heatmap (148×148) avec P(ennemi présent) par pixel
- **Loss** : Binary cross-entropy avec zones pondérées

### Features clés

- `time_since_last_seen` : Utilisation des events (17.9s granularité vs 60s frames)
- `last_seen_x/y` : Dernière position connue
- `velocity` : Vitesse + direction
- `activity_context` : Kills récents, objectifs, teamfights

## 🎯 Milestones

- [x] API Riot Games : Téléchargement matchs avec timelines
- [x] Dataset fog of war : 2,060 positions de 5 matchs
- [x] Visualiseur minimap : Flask webapp avec navigation
- [x] Ward tracking : Interpolation position + expiration + destruction
- [x] Interface interactive : Sélection wards avec vision circles
- [ ] Enhanced dataset : time_since_last_seen avec events
- [ ] Modèle ML : U-Net CNN pour heatmaps
- [ ] Training pipeline : 5-fold cross-validation
- [ ] Démo : Visualisation prédictions en temps réel

## 📚 Ressources

- **Riot Games API** : https://developer.riotgames.com/
- **Match Timeline** : https://developer.riotgames.com/apis#match-v5/GET_getTimeline
- **LoL Vision** : https://leagueoflegends.fandom.com/wiki/Sight
- **Documentation Ward Tracking** : Voir `WARD_TRACKING.md`
