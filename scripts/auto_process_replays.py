#!/usr/bin/env python3
"""
Pipeline complet : Lancer replay → Capturer données → Parser
"""

import sys
import time
import json
from pathlib import Path

# Importer les modules depuis le même dossier
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from launch_replay import LoLReplayLauncher
from capture_replay_api import LeagueClientAPI


def process_replay(rofl_path: Path, output_dir: Path, capture_duration: int = 300):
    """
    Process complet d'un replay :
    1. Lance LoL avec le replay
    2. Attend que LoL démarre
    3. Capture data via API
    4. Ferme LoL
    5. Parse et sauvegarde
    
    Args:
        rofl_path: Chemin vers .rofl
        output_dir: Dossier de sortie
        capture_duration: Durée de capture (secondes)
    """
    print(f"\n{'='*80}")
    print(f"🎮 TRAITEMENT REPLAY: {rofl_path.name}")
    print(f"{'='*80}\n")
    
    launcher = LoLReplayLauncher()
    api = LeagueClientAPI()
    
    output_file = output_dir / f"{rofl_path.stem}_captured.json"
    
    # Étape 1 : Lancer replay
    print("📌 Étape 1/4: Lancement replay...")
    try:
        launcher.launch_replay(rofl_path, wait=True)
    except Exception as e:
        print(f"❌ Erreur lancement: {e}")
        return False
    
    # Étape 2 : Attendre connexion API
    print("\n📌 Étape 2/4: Connexion API...")
    max_attempts = 10
    for attempt in range(max_attempts):
        time.sleep(2)
        if api.connect():
            break
        print(f"   Tentative {attempt+1}/{max_attempts}...")
    else:
        print("❌ Impossible de se connecter à l'API")
        launcher.kill_lol()
        return False
    
    # Étape 3 : Capture data
    print("\n📌 Étape 3/4: Capture données...")
    try:
        api.record_replay_data(output_file, duration_seconds=capture_duration, interval=1.0)
    except KeyboardInterrupt:
        print("\n⚠️  Capture interrompue par utilisateur")
    except Exception as e:
        print(f"❌ Erreur capture: {e}")
        launcher.kill_lol()
        return False
    
    # Étape 4 : Fermeture
    print("\n📌 Étape 4/4: Fermeture LoL...")
    launcher.kill_lol()
    
    print(f"\n{'='*80}")
    print(f"✅ TRAITEMENT TERMINÉ")
    print(f"{'='*80}")
    print(f"\n📁 Données sauvegardées: {output_file}")
    
    return True


def batch_process_replays(replay_dir: Path, output_dir: Path, max_replays: int = 5):
    """
    Traite plusieurs replays en batch
    
    Args:
        replay_dir: Dossier contenant les .rofl
        output_dir: Dossier de sortie
        max_replays: Nombre max de replays à traiter
    """
    replays = list(replay_dir.glob('*.rofl'))[:max_replays]
    
    if not replays:
        print(f"❌ Aucun replay trouvé dans {replay_dir}")
        return
    
    print(f"\n🎯 Traitement batch: {len(replays)} replays")
    print(f"   Input: {replay_dir}")
    print(f"   Output: {output_dir}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    for i, replay in enumerate(replays, 1):
        print(f"\n{'='*80}")
        print(f"📂 Replay {i}/{len(replays)}")
        print(f"{'='*80}")
        
        success = process_replay(replay, output_dir, capture_duration=120)  # 2min par replay
        
        results.append({
            'replay': replay.name,
            'success': success
        })
        
        if i < len(replays):
            print("\n⏳ Pause 5s avant prochain replay...")
            time.sleep(5)
    
    # Résumé
    print(f"\n{'='*80}")
    print(f"📊 RÉSUMÉ BATCH")
    print(f"{'='*80}\n")
    
    success_count = sum(1 for r in results if r['success'])
    print(f"   Succès: {success_count}/{len(results)}")
    
    for r in results:
        status = "✅" if r['success'] else "❌"
        print(f"   {status} {r['replay']}")


def main():
    """Point d'entrée principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Process LoL replays automatiquement")
    parser.add_argument('--replay', type=Path, help="Replay unique à traiter")
    parser.add_argument('--batch', action='store_true', help="Mode batch (tous les replays)")
    parser.add_argument('--duration', type=int, default=300, help="Durée capture (sec)")
    parser.add_argument('--max', type=int, default=5, help="Max replays en batch")
    
    args = parser.parse_args()
    
    output_dir = Path('data/captured')
    
    if args.replay:
        # Single replay
        if not args.replay.exists():
            print(f"❌ Replay non trouvé: {args.replay}")
            return
        
        process_replay(args.replay, output_dir, capture_duration=args.duration)
    
    elif args.batch:
        # Batch mode
        replay_dir = Path('data/raw/replays')
        batch_process_replays(replay_dir, output_dir, max_replays=args.max)
    
    else:
        # Par défaut: premier replay trouvé
        replay_dir = Path('data/raw/replays')
        replays = list(replay_dir.glob('*.rofl'))
        
        if not replays:
            print("❌ Aucun replay trouvé. Options:")
            print("   --replay <fichier.rofl>  : Traiter un replay spécifique")
            print("   --batch                  : Traiter tous les replays")
            return
        
        print(f"💡 Utilisation par défaut: premier replay")
        print(f"   Replay: {replays[0].name}")
        print(f"\n   Options disponibles:")
        print(f"   --replay <file>  : Replay spécifique")
        print(f"   --batch          : Tous les replays")
        print(f"   --duration N     : Durée capture (défaut: 300s)")
        
        process_replay(replays[0], output_dir, capture_duration=60)  # 1min test


if __name__ == '__main__':
    main()
