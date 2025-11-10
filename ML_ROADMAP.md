# ML Fog of War Prediction - Roadmap

## État actuel
- ✅ Dataset généré : 2061 lignes (5 matches × ~10 joueurs × ~40 timestamps)
- ✅ Données toutes les 60s via Timeline API
- ✅ Flag `visible_to_enemy` calculé
- ✅ Webapp de visualisation fonctionnelle

## Objectifs

### 1. Améliorer la qualité du fog of war 🎯
**Problème** : Actuellement basé sur des approximations (rayon de vision fixe)

**Tâches** :
- [ ] Raffiner le calcul de vision (terrain, bushes, murs)
- [ ] Utiliser les données réelles de vision de League of Legends
- [ ] Ajouter la vision asymétrique (bushes, angles morts)
- [ ] Intégrer la vision des wards avec leur durée de vie

**Données disponibles** :
- Positions joueurs (60s)
- Events WARD_PLACED / WARD_KILL dans timeline
- Positions des events (x, y)

### 2. Interpolation des positions ⏱️
**Problème** : Grosse perte d'information entre les snapshots 60s

**Approches possibles** :

#### 2a. Interpolation basée sur les events
```
Timeline events disponibles :
- CHAMPION_KILL (x, y, timestamp)
- ITEM_PURCHASED (timestamp, shop → position connue)
- ELITE_MONSTER_KILL (objectif → position connue)
- BUILDING_KILL (tourelle → position fixe)
```

**Stratégie** :
1. Interpolation linéaire entre deux timestamps
2. Ajuster avec les events intermédiaires (kill, shop, objectif)
3. Contraintes physiques (vitesse max de déplacement)

#### 2b. Interpolation des wards
```
Events WARD_PLACED :
- timestamp
- position (x, y)
- type (YELLOW_TRINKET, CONTROL_WARD, etc.)
- creatorId

Durées de vie :
- Yellow trinket : 90-120s
- Control ward : permanent jusqu'à destruction
- WARD_KILL event → fin de vie
```

**Stratégie** :
1. Créer timeline de vision par ward
2. Calculer zones de vision actives à chaque instant
3. Mettre à jour fog en continu

### 3. Modèle de Machine Learning 🤖

**Question fondamentale** : Qu'est-ce qu'on prédit exactement ?

#### Option A : Prédiction de présence binaire
```
Input : 
- État du fog actuel (visible/non-visible par zone)
- Positions connues des alliés
- Dernières positions connues ennemies
- Game time
- Gold, level, objectifs

Output :
- Probabilité de présence ennemie par zone de la map
```

#### Option B : Prédiction de position exacte
```
Input : même
Output :
- Position (x, y) de chaque ennemi caché
- Niveau de confiance
```

#### Option C : Prédiction temporelle
```
Input : Historique des N dernières secondes
Output : Positions dans les T prochaines secondes
```

**Architectures possibles** :
- CNN sur une représentation 2D de la map (image-like)
- LSTM pour la dimension temporelle
- Graph Neural Network (joueurs = nodes, relations spatiales = edges)
- Transformer pour séquences temporelles

## Plan d'action immédiat

### Phase 1 : Consolidation du dataset (1-2 jours)
1. **Améliorer le calcul de fog**
   - Intégrer les wards de la timeline
   - Calculer vision réaliste (pas juste un rayon)
   
2. **Interpolation basique**
   - Interpoler linéairement entre timestamps 60s
   - Ajouter contraintes de vitesse
   - Utiliser events pour ancrer les positions

3. **Enrichir les features**
   - Ajouter contexte de jeu (objectifs pris, or total team, etc.)
   - Calculer métriques dérivées (distance aux objectifs, ward coverage)

### Phase 2 : Exploration ML (2-3 jours)
1. **Baseline simple**
   - Prédiction naïve : "ennemi reste à sa dernière position connue"
   - Mesurer accuracy comme référence

2. **Premier modèle**
   - Commencer avec Option A (présence binaire par zone)
   - Diviser map en grille (ex: 50×50 cases)
   - Random Forest ou XGBoost pour commencer

3. **Évaluation**
   - Métriques : Precision, Recall, F1-score par zone
   - Visualisation des prédictions sur la webapp

### Phase 3 : Itération (ongoing)
1. Feature engineering
2. Tester différentes architectures
3. Augmentation de données (plus de matches)
4. Fine-tuning

## Questions à résoudre

1. **Granularité temporelle** : Interpoler à quelle fréquence ? (1s, 5s, 10s ?)
2. **Granularité spatiale** : Taille de grille pour prédictions ?
3. **Fenêtre temporelle** : Combien d'historique utiliser ? (30s, 1min, 5min ?)
4. **Balance des données** : Beaucoup plus de "non-visible" que "visible"
5. **Train/test split** : Par match ? Par timestamp ? Par joueur ?

## Données additionnelles potentielles

- **Plus de matches** : Récupérer 50-100 matches via Riot API
- **Différents MMR** : Bronze, Silver, Gold, Plat, Diamond (patterns différents)
- **Meta actuelle** : Patch 14.x (champions populaires, stratégies)

## Notes techniques

**Dataset actuel** :
```python
Colonnes : timestamp, participant_id, champion, team, 
          position_x, position_y, visible_to_enemy, 
          level, total_gold, match_id
```

**Code existant** :
- `src/lol_fog_predictor/api/riot_api.py` : Récupération matches
- `src/lol_fog_predictor/api/timeline_processor.py` : Processing timeline
- `src/lol_fog_predictor/fog/vision_calculator.py` : Calcul fog (basique)
- `webapp/app.py` : Visualisation

**Prochains modules à créer** :
- `src/lol_fog_predictor/interpolation/` : Position interpolation
- `src/lol_fog_predictor/features/` : Feature engineering
- `src/lol_fog_predictor/ml/models/` : ML models
- `src/lol_fog_predictor/ml/evaluation/` : Metrics & eval
