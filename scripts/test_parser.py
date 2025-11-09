#!/usr/bin/env python3
"""
Script de test pour parser les replays .rofl
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from lol_fog_predictor.parser import parse_rofl, ChunkParser, BlockParser, parse_path_packet, PositionTracker


def test_replay(rofl_path: Path):
    """Test complet du parsing d'un replay"""
    print(f"\n{'='*60}")
    print(f"📂 Parsing: {rofl_path.name}")
    print(f"{'='*60}\n")
    
    # === 1. Parser Metadata ===
    print("🔍 Étape 1: Extraction métadonnées...")
    try:
        metadata, chunks_data = parse_rofl(rofl_path)
        print(f"✅ Métadonnées extraites:")
        print(f"   Version: {metadata.version}")
        print(f"   Durée: {metadata.game_len / 1000:.1f}s ({metadata.game_len / 60000:.1f}min)")
        print(f"   Équipe gagnante: {metadata.winning_team}")
        print(f"\n👥 Joueurs ({len(metadata.players)}):")
        for i, player in enumerate(metadata.players, 1):
            print(f"   {i}. {player.name:20s} - {player.skin:15s} ({player.team:4s} - {player.position})")
        print(f"\n📦 Chunks data: {len(chunks_data)} bytes")
    except Exception as e:
        print(f"❌ Erreur metadata: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # === 2. Parser Chunks ===
    print(f"\n🔍 Étape 2: Décompression chunks ZSTD...")
    try:
        chunk_parser = ChunkParser(chunks_data)
        chunks = chunk_parser.parse_all_chunks()
        print(f"✅ {len(chunks)} chunks parsés")
        
        keyframes = chunk_parser.get_keyframe_chunks()
        chunk_chunks = chunk_parser.get_chunk_chunks()
        print(f"   - KeyFrames: {len(keyframes)}")
        print(f"   - Chunks: {len(chunk_chunks)}")
        
        if chunks:
            sample = chunks[0]
            print(f"\n   Exemple chunk #0:")
            print(f"     Type: {sample.type_}")
            print(f"     Compressé: {sample.compressed_len} bytes")
            print(f"     Décompressé: {len(sample.payload) if sample.payload else 0} bytes")
    except Exception as e:
        print(f"❌ Erreur chunks: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # === 3. Parser Blocks ===
    print(f"\n🔍 Étape 3: Extraction blocks...")
    try:
        all_blocks = []
        movement_packets = []
        
        # Parser tous les chunks (keyframes ET chunks normaux)
        test_chunks = (keyframes + chunk_chunks)[:10]  # Test sur 10 premiers chunks
        
        for i, chunk in enumerate(test_chunks):
            if chunk.payload:
                block_parser = BlockParser(chunk.payload)
                blocks = block_parser.parse_all_blocks()
                all_blocks.extend(blocks)
                
                # Chercher packets de mouvement (packet_id typiquement 0x0061, 0x0064, etc.)
                for block in blocks:
                    # Test parsing mouvement
                    path_packet = parse_path_packet(block.timestamp, block.payload)
                    if path_packet and path_packet.waypoints:
                        movement_packets.append(path_packet)
        
        print(f"✅ {len(all_blocks)} blocks parsés ({len(test_chunks)} chunks testés)")
        print(f"   - Packets de mouvement trouvés: {len(movement_packets)}")
        
        if all_blocks:
            print(f"\n   Exemple block:")
            sample = all_blocks[0]
            print(f"     Timestamp: {sample.timestamp:.2f}s")
            print(f"     Packet ID: 0x{sample.packet_id:04x}")
            print(f"     Length: {sample.length} bytes")
        
        if movement_packets:
            print(f"\n   Exemple mouvement:")
            sample = movement_packets[0]
            print(f"     Entity ID: {sample.entity_id}")
            print(f"     Speed: {sample.speed:.1f}")
            print(f"     Waypoints: {len(sample.waypoints)}")
            if sample.waypoints:
                print(f"     Position start: ({sample.waypoints[0][0]:.1f}, {sample.waypoints[0][1]:.1f})")
    except Exception as e:
        print(f"❌ Erreur blocks: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # === 4. Track Positions ===
    print(f"\n🔍 Étape 4: Tracking positions...")
    try:
        tracker = PositionTracker()
        
        for packet in movement_packets[:50]:  # Test sur 50 premiers
            tracker.update(packet)
        
        # Get positions à différents timestamps
        test_timestamps = [10.0, 30.0, 60.0, 120.0]
        
        print(f"✅ Tracker initialisé avec {len(tracker.last_packets)} entités")
        print(f"\n   Positions à différents timestamps:")
        
        for ts in test_timestamps:
            positions = tracker.get_all_positions(ts)
            print(f"     t={ts:.0f}s: {len(positions)} entités")
            if positions:
                entity_id, pos = list(positions.items())[0]
                print(f"       Exemple entity {entity_id}: ({pos[0]:.1f}, {pos[1]:.1f})")
    except Exception as e:
        print(f"❌ Erreur tracking: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"\n{'='*60}")
    print(f"✅ Test complet terminé !")
    print(f"{'='*60}\n")


def main():
    """Test sur les deux replays"""
    replay_dir = Path(__file__).parent.parent / 'data' / 'raw' / 'replays'
    
    replays = list(replay_dir.glob('*.rofl'))
    
    if not replays:
        print("❌ Aucun replay trouvé dans data/raw/replays/")
        return
    
    print(f"🎮 Replays trouvés: {len(replays)}")
    
    for replay in sorted(replays):
        test_replay(replay)


if __name__ == '__main__':
    main()
