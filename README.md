# 🎮 League of Legends Fog of War Prediction

Système de **Machine Learning** pour prédire les positions des joueurs ennemis cachés dans le fog of war de League of Legends.

## 📋 Architecture

```
lol-fog-predictor/
├── data/
│   ├── raw/replays/     # Fichiers .rofl
│   ├── parsed/          # JSON extraits
│   └── ml/              # Dataset ML
├── src/
│   ├── fog/             # Simulateur fog of war
│   └── ml/              # Modèles ML
├── models/              # Modèles entraînés
├── notebooks/           # Jupyter notebooks
├── scripts/             # Scripts utilitaires
└── ROFL/                # Parser Rust compilé
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

## 📦 Phase 1 : Parser les .rofl

### Binaire ROFL compilé

```bash
./ROFL/target/release/ROFL file -r data/raw/replays/game1.rofl -o data/parsed/game1.json
```

### Format JSON attendu

```json
{
  "metadata": {
    "game_len": 1386200,
    "version": "12.5.425.9171",
    "winning_team": "Blue",
    "players": [...]
  },
  "players_state": [
    {
      "timestamp": 18.97,
      "players": [
        {"champ": "Garen", "pos": [1002.0, 4088.0], "role": "Top", "team": "Blue"},
        ...
      ]
    },
    ...
  ],
  "wards": [...]
}
```

## 🎯 Milestones

- [x] Compiler ROFL en Rust natif
- [ ] Parser 5-10 replays .rofl → JSON
- [ ] Créer dataset ML avec fog of war
- [ ] Entraîner modèle CNN baseline
- [ ] Démo avec visualisation heatmap

## 📚 Ressources

- **ROFL Parser** : https://github.com/Mowokuma/ROFL
- **LoL Vision** : https://leagueoflegends.fandom.com/wiki/Sight
