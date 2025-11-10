# 🔍 RÈGLES DE VISION / FOG OF WAR

## 📊 Constantes de Vision (Correctes)

### Vision Range par Type
- **1350 unités** : Champions, Pets, Super Minions, **Tourelles**
- **900 unités** : Totem Wards, Stealth Wards, Control Wards, Zombie Wards, Effigies
- **1200 unités** : Melee/Caster/Siege Minions (non implémenté actuellement)

### Taille de la Map
- **14820 unités** (0-14820 sur x et y)

---

## 🏰 Positions Tourelles

### Blue Team (11 tourelles)

**Top Lane:**
1. Top Outer: `(981, 10441)`
2. Top Inner: `(1512, 6699)`
3. Top Inhibitor: `(1169, 4287)`

**Mid Lane:**
4. Mid Outer: `(5846, 6396)`
5. Mid Inner: `(5048, 4812)`
6. Mid Inhibitor: `(3651, 3696)`

**Bot Lane:**
7. Bot Outer: `(10504, 1029)`
8. Bot Inner: `(6919, 1483)`
9. Bot Inhibitor: `(4281, 1253)`

**Base:**
10. Nexus Top: `(1748, 2270)`
11. Nexus Bot: `(2177, 1807)`

### Red Team (11 tourelles)

**Top Lane:**
1. Top Outer: `(10481, 13650)`
2. Top Inner: `(7943, 13411)`
3. Top Inhibitor: `(10504, 13650)`

**Mid Lane:**
4. Mid Outer: `(8955, 8510)`
5. Mid Inner: `(9767, 10113)`
6. Mid Inhibitor: `(11134, 11207)`

**Bot Lane:**
7. Bot Outer: `(13866, 4505)`
8. Bot Inner: `(13327, 8226)`
9. Bot Inhibitor: `(13624, 10572)`

**Base:**
10. Nexus Top: `(13052, 12612)`
11. Nexus Bot: `(12611, 13084)`

---

## 🧮 Calcul de Visibilité

### Fonction: `is_enemy_visible()`

Un ennemi est **VISIBLE** si sa distance à l'une des sources suivantes est inférieure au rayon correspondant:

1. **Champions alliés** : ≤ 1350 unités
2. **Tourelles alliées** : ≤ 1350 unités  
3. **Wards alliées** : ≤ 900 unités

### Calcul de distance
```python
distance = sqrt((x1 - x2)² + (y1 - y2)²)
```

---

## ✅ Implémentation Actuelle

### Dans `timeline_processor.py`

**Sources de vision prises en compte:**
- ✅ Champions alliés (1350 unités)
- ✅ Tourelles alliées (1350 unités) - **NOUVEAU**
- ✅ Wards alliées (900 unités) - **ATTENTION: positions manquantes dans API**

**Non implémenté:**
- ❌ Minions (1200 unités)
- ❌ Bushes (zones réduisant vision)
- ❌ Jungle camps/plantes

### Problème Wards

⚠️ **Les events `WARD_PLACED` de l'API Riot n'incluent PAS le champ `position`**

Impact: La fonction `extract_ward_positions()` retourne toujours une liste vide, donc:
- Vision de wards **non prise en compte** dans le dataset actuel
- Seulement Champions (1350) + Tourelles (1350) sont utilisés

**Solutions possibles:**
1. Utiliser WardTracker de webapp (a les positions)
2. Interpoler positions depuis autres events
3. Ignorer wards pour le dataset initial

---

## 📋 Dataset Généré

### Colonnes
- `timestamp` : Temps du jeu (ms)
- `participant_id` : ID joueur (1-10)
- `champion` : Nom du champion
- `team` : 100 (Blue) ou 200 (Red)
- `position_x`, `position_y` : Position réelle
- `visible_to_enemy` : Boolean - visible par équipe adverse
- `level` : Niveau du champion
- `total_gold` : Or total
- `match_id` : ID du match

### Perspective
- **Actuelle** : POV Blue team uniquement
- `visible_to_enemy=True` signifie "visible PAR l'équipe bleue"

### Calcul
Pour chaque joueur Red (ennemi) :
```python
visible = is_enemy_visible(
    enemy_pos,
    blue_champion_positions,  # 5 champions (1350 range)
    BLUE_TURRET_POSITIONS,    # 11 tourelles (1350 range)
    blue_wards                # 0-N wards (900 range) - VIDE actuellement
)
```

---

## 🎯 Prochaines Étapes

### Priorité 1 - Validation
1. **Vérifier positions tourelles** : Tester avec vraies données de match
2. **Régénérer dataset** : Avec vision tourelles activée
3. **Comparer stats** : % visible avant/après tourelles

### Priorité 2 - Amélioration Wards
1. **Intégrer WardTracker** : Utiliser positions depuis webapp
2. **Recalculer fog** : Avec wards actives
3. **Valider impact** : Quelle différence ça fait ?

### Priorité 3 - Expansion
1. **Vision Minions** : Ajouter si pertinent
2. **Perspective Red** : Générer dataset Red POV
3. **Bushes** : Définir zones et réduire vision
