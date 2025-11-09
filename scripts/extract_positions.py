#!/usr/bin/env python3
"""
Pipeline complet pour parser un fichier .rofl et extraire positions
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from lol_fog_predictor.parser import (
    parse_rofl,
    ChunkParser,
    BlockParser,
    parse_path_packet,
    PositionTracker
)


def extract_positions_from_rofl(rofl_path: Path, output_path: Path):
    """
    Parse un .rofl et extrait toutes les positions des joueurs
    """
    print(f"📂 Parsing: {rofl_path.name}")
    
    # 1. Parse metadata
    print("  [1/4] Extraction métadonnées...")
    metadata, chunks_data = parse_rofl(rofl_path)
    
    print(f"    ✓ Version: {metadata.version}")
    print(f"    ✓ Durée: {metadata.game_len / 1000:.1f}s")
    print(f"    ✓ Joueurs: {len(metadata.players)}")
    
    # 2. Parse chunks
    print("  [2/4] Décompression chunks...")
    chunk_parser = ChunkParser(chunks_data)
    chunks = chunk_parser.parse_all_chunks()
    print(f"    ✓ Chunks parsés: {len(chunks)}")
    
    # 3. Parse blocks et extraire packets de mouvement
    print("  [3/4] Extraction blocks et positions...")
    tracker = PositionTracker()
    
    movement_packets = []
    total_blocks = 0
    
    for chunk in chunks:
        if chunk.payload is None or chunk.type_ == 0x02:
            continue
        
        block_parser = BlockParser(chunk.payload)
        blocks = block_parser.parse_all_blocks()
        total_blocks += len(blocks)
        
        for block in blocks:
            # Packet ID pour mouvement (à identifier dans le code Rust)
            # Typiquement 0x61, 0x64, etc. pour waypoints
            if block.packet_id in [0x61, 0x64]:
                path_packet = parse_path_packet(block.timestamp, block.payload)
                if path_packet and path_packet.waypoints:
                    tracker.update(path_packet)
                    movement_packets.append(path_packet)
    
    print(f"    ✓ Blocks parsés: {total_blocks}")
    print(f"    ✓ Packets mouvement: {len(movement_packets)}")
    
    # 4. Générer snapshots de positions
    print("  [4/4] Génération snapshots positions...")
    
    # Créer snapshots chaque seconde
    game_duration = metadata.game_len / 1000  # en secondes
    snapshots = []
    
    for timestamp in range(int(game_duration)):
        positions = tracker.get_all_positions(float(timestamp))
        
        if positions:
            snapshot = {
                "timestamp": float(timestamp),
                "entities": [
                    {
                        "id": entity_id,
                        "pos": [round(pos[0], 2), round(pos[1], 2)]
                    }
                    for entity_id, pos in positions.items()
                ]
            }
            snapshots.append(snapshot)
    
    print(f"    ✓ Snapshots générés: {len(snapshots)}")
    
    # 5. Construire output JSON
    output_data = {
        "metadata": {
            "version": metadata.version,
            "game_len": metadata.game_len,
            "winning_team": metadata.winning_team,
            "players": [
                {
                    "name": p.name,
                    "skin": p.skin,
                    "team": p.team,
                    "position": p.position
                }
                for p in metadata.players
            ]
        },
        "players_state": snapshots,
        "stats": {
            "total_chunks": len(chunks),
            "total_blocks": total_blocks,
            "movement_packets": len(movement_packets)
        }
    }
    
    # 6. Sauvegarder
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Output sauvegardé: {output_path}")
    print(f"   📊 {len(snapshots)} timestamps avec positions")
    
    return output_data


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_positions.py <fichier.rofl> [output.json]")
        sys.exit(1)
    
    rofl_path = Path(sys.argv[1])
    
    if not rofl_path.exists():
        print(f"❌ Fichier non trouvé: {rofl_path}")
        sys.exit(1)
    
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('data/parsed') / f"{rofl_path.stem}.json"
    
    try:
        extract_positions_from_rofl(rofl_path, output_path)
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
