# 🚨 Statut: Parser ROFL - Problème Patch Files

## ✅ Ce qui fonctionne

- ✅ **Binaire ROFL compilé** : `/ROFL/target/release/ROFL` (Rust natif Linux)
- ✅ **Environnement Python** : uv + dépendances installées
- ✅ **Structure projet** : Dossiers créés (data/, src/, models/, etc.)
- ✅ **Replay disponible** : `data/raw/replays/EUW1-3830447804.rofl` (version 8.22)

## ❌ Problème Critique

Le binaire ROFL **nécessite les patch files** pour fonctionner :
- Fichiers attendus dans `./patch/8-22.patch/`
- Contenu : `text.bin`, `data.bin`, `rdata.bin`, `result.json`
- Ces fichiers contiennent le code x86-64 du client LoL à émuler
- **Repo archivé** : https://github.com/Mowokuma/ROFL (pas de téléchargement patch)

## 🔍 Options Disponibles

### Option 1: Trouver les Patch Files (Recommandé)
**Sources possibles** :
1. **Releases GitHub archivées** (si backup existe ailleurs)
2. **Communauté LoL** : Reddit r/leagueoflegends, Discord
3. **Archive.org** : Chercher snapshot du repo
4. **Autres repos** : Forks/mirrors de Mowokuma/ROFL

**Fichiers à chercher** :
```
patch/8-22.patch/
├── text.bin
├── data.bin
├── rdata.bin
└── result.json
```

### Option 2: Utiliser des Replays Plus Récents
- Chercher replays **patch 5.x** (2025) si patches disponibles
- Version 8.22 date de 2018, patches probablement perdus

### Option 3: Parser Alternatif (Complexe)
Implémenter parser Python complet :
- ❌ Très complexe (émulation CPU x86-64 via Unicorn Engine)
- ❌ 40-60h de développement
- ❌ Nécessite reverse engineering du format LoL

### Option 4: Changer de Source de Données (❌ Tu as refusé)
- Riot API : Pas de positions détaillées
- Datasets publics : Tu veux uniquement .rofl

## 🎯 Action Immédiate Recommandée

### Chercher Patch Files 8.22

**1. Archive.org**
```bash
# Chercher snapshots du repo
https://web.archive.org/web/*/github.com/Mowokuma/ROFL/releases
```

**2. Reddit / Discord**
```
- r/leagueoflegends
- r/summonerschool
- Discord LoL Dev Community
```

**3. Message Auteur**
```
- Contact @Mowokuma sur GitHub
- Demander backup des patch files
```

### Tester avec Replay Récent

Si tu as accès à un PC avec LoL installé :
1. Jouer une partie
2. Récupérer .rofl dans `C:\Users\<User>\Documents\League of Legends\Replays\`
3. Vérifier version patch actuelle LoL (probablement 14.x en Nov 2025)
4. Chercher patches 14.x pour ROFL

## 📝 Workaround Temporaire

En attendant les patches, on peut :
1. ✅ Développer le **simulateur Fog of War** (module `fog/`)
2. ✅ Créer l'**architecture ML** (modèle CNN)
3. ✅ Préparer les **notebooks d'exploration**
4. ⏳ **Tester avec données synthétiques** (positions simulées)

Une fois les patches obtenus → parser les vrais replays.

## 🔗 Ressources

- **Repo ROFL** : https://github.com/Mowokuma/ROFL (archivé)
- **Unicorn Engine** : https://www.unicorn-engine.org/ (si impl Python)
- **Format .rofl** : Binaire propriétaire Riot, compression ZSTD + chunks

## 💡 Suggestion

**Veux-tu que je** :
1. 🔍 Crée un script pour chercher automatiquement les patches sur Archive.org ?
2. 📊 Continue le développement ML avec données synthétiques en attendant ?
3. 🛠️ Commence l'implémentation du parser Python complet (long) ?
4. 📱 T'aide à rédiger un message pour la communauté LoL ?
