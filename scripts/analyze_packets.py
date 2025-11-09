#!/usr/bin/env python3
"""
Script d'analyse des packets pour identifier les mouvements joueurs
"""

import sys
from pathlib import Path
from collections import defaultdict, Counter

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from lol_fog_predictor.parser import parse_rofl, ChunkParser, BlockParser, parse_path_packet


def analyze_packets(rofl_path: Path):
    """Analyse en profondeur tous les packets"""
    print(f"\n{'='*80}")
    print(f"🔍 ANALYSE APPROFONDIE: {rofl_path.name}")
    print(f"{'='*80}\n")
    
    # Parse metadata
    metadata, chunks_data = parse_rofl(rofl_path)
    print(f"📊 Metadata:")
    print(f"   Version: {metadata.version}")
    print(f"   Durée: {metadata.game_len / 60000:.1f}min")
    print(f"   Joueurs: {len(metadata.players)}")
    
    # Parse chunks
    chunk_parser = ChunkParser(chunks_data)
    chunks = chunk_parser.parse_all_chunks()
    print(f"\n📦 Chunks: {len(chunks)} parsés")
    
    # Analyser TOUS les blocks
    print(f"\n🔍 Analyse des blocks...")
    
    packet_id_counts = Counter()
    packet_id_samples = defaultdict(list)
    all_blocks = []
    
    for chunk in chunks:
        if chunk.payload:
            block_parser = BlockParser(chunk.payload)
            blocks = block_parser.parse_all_blocks()
            all_blocks.extend(blocks)
            
            for block in blocks:
                packet_id_counts[block.packet_id] += 1
                
                # Garder samples (max 3 par packet_id)
                if len(packet_id_samples[block.packet_id]) < 3:
                    packet_id_samples[block.packet_id].append({
                        'timestamp': block.timestamp,
                        'length': block.length,
                        'param': block.param,
                        'payload_start': block.payload[:min(32, len(block.payload))].hex()
                    })
    
    print(f"✅ {len(all_blocks)} blocks totaux parsés")
    print(f"\n📈 Top 20 Packet IDs par fréquence:")
    print(f"   {'Packet ID':12s} {'Count':>8s} {'Avg Len':>10s}")
    print(f"   {'-'*12} {'-'*8} {'-'*10}")
    
    for packet_id, count in packet_id_counts.most_common(20):
        avg_len = sum(b.length for b in all_blocks if b.packet_id == packet_id) / count
        print(f"   0x{packet_id:04x}       {count:>8d} {avg_len:>10.1f}")
    
    # Analyser packets suspects de mouvement
    print(f"\n🎯 Analyse des candidats mouvement (high frequency + medium size):")
    
    movement_candidates = [
        pid for pid, count in packet_id_counts.items()
        if count > 100  # Fréquent
    ]
    
    for pid in sorted(movement_candidates)[:15]:
        samples = packet_id_samples[pid]
        avg_len = sum(b.length for b in all_blocks if b.packet_id == pid) / packet_id_counts[pid]
        
        print(f"\n   📌 Packet 0x{pid:04x} (count: {packet_id_counts[pid]}, avg_len: {avg_len:.1f})")
        
        # Tester parsing mouvement
        test_blocks = [b for b in all_blocks if b.packet_id == pid][:5]
        
        parsed_count = 0
        valid_positions = 0
        
        for block in test_blocks:
            path = parse_path_packet(block.timestamp, block.payload)
            if path and path.waypoints:
                parsed_count += 1
                
                # Check si positions réalistes (0-15000)
                for x, y in path.waypoints:
                    if 0 <= x <= 15000 and 0 <= y <= 15000:
                        valid_positions += 1
                        print(f"      ✅ t={block.timestamp:.1f}s: entity {path.entity_id}, "
                              f"{len(path.waypoints)} waypoints, pos=({x:.0f}, {y:.0f})")
                        break
                else:
                    # Positions hors range
                    if path.waypoints:
                        x, y = path.waypoints[0]
                        print(f"      ⚠️  t={block.timestamp:.1f}s: entity {path.entity_id}, "
                              f"pos OUT OF RANGE=({x:.0f}, {y:.0f})")
        
        if parsed_count > 0:
            print(f"      Stats: {parsed_count}/{len(test_blocks)} parsés, "
                  f"{valid_positions} positions valides")
    
    # Stats finales
    print(f"\n{'='*80}")
    print(f"📊 STATISTIQUES FINALES")
    print(f"{'='*80}")
    print(f"   Total blocks: {len(all_blocks)}")
    print(f"   Packet IDs uniques: {len(packet_id_counts)}")
    print(f"   Chunks analysés: {len(chunks)}")
    print(f"\n   Durée couverte: {all_blocks[-1].timestamp:.1f}s" if all_blocks else "   Aucun block")


def test_offset_calibration(rofl_path: Path):
    """Test différents offsets pour décoder les positions"""
    print(f"\n{'='*80}")
    print(f"🔧 CALIBRATION OFFSETS DE DÉCODAGE")
    print(f"{'='*80}\n")
    
    metadata, chunks_data = parse_rofl(rofl_path)
    chunk_parser = ChunkParser(chunks_data)
    chunks = chunk_parser.parse_all_chunks()
    
    # Récupérer un sample de blocks
    sample_blocks = []
    for chunk in chunks[:5]:
        if chunk.payload:
            block_parser = BlockParser(chunk.payload)
            blocks = block_parser.parse_all_blocks()
            sample_blocks.extend(blocks[:20])
    
    if not sample_blocks:
        print("❌ Pas de blocks à analyser")
        return
    
    print(f"📦 {len(sample_blocks)} blocks échantillons")
    
    # Tester différents offsets (actuels: 7358, 7412)
    offset_tests = [
        (7358, 7412, "Original (v8.22)"),
        (0, 0, "Pas d'offset"),
        (7500, 7500, "7500, 7500"),
        (14000//2, 14000//2, "Milieu map"),
        (-7358, -7412, "Négatif original"),
        (3679, 3706, "Half original"),
    ]
    
    print(f"\n🧪 Test de différents offsets de décodage:\n")
    
    from lol_fog_predictor.parser.position_extractor import sign_extend
    import struct
    
    for offset_x, offset_y, description in offset_tests:
        print(f"   Testing: {description} (offset_x={offset_x}, offset_y={offset_y})")
        
        valid_count = 0
        total_tested = 0
        
        for block in sample_blocks[:30]:
            if block.length < 10:
                continue
            
            try:
                cursor = 0
                payload = block.payload
                
                # Parse header minimal
                if cursor + 10 > len(payload):
                    continue
                
                parsing_type = struct.unpack('<H', payload[cursor:cursor+2])[0]
                cursor += 2
                entity_id = struct.unpack('<I', payload[cursor:cursor+4])[0]
                cursor += 4
                speed = struct.unpack('<f', payload[cursor:cursor+4])[0]
                cursor += 4
                
                if (parsing_type & 1) != 0:
                    cursor += 1
                
                unk = (parsing_type >> 1) & 0xFF
                if unk == 0 or unk > 10:
                    continue
                
                # Essayer de parser au moins 1 waypoint
                if cursor + 4 <= len(payload):
                    x_encoded = struct.unpack('<H', payload[cursor:cursor+2])[0]
                    y_encoded = struct.unpack('<H', payload[cursor+2:cursor+4])[0]
                    
                    # Décoder avec les offsets testés
                    x = sign_extend(x_encoded, 16) * 2.0 + offset_x
                    y = sign_extend(y_encoded, 16) * 2.0 + offset_y
                    
                    total_tested += 1
                    
                    # Check si dans range valide
                    if 0 <= x <= 15000 and 0 <= y <= 15000:
                        valid_count += 1
            
            except:
                continue
        
        if total_tested > 0:
            success_rate = (valid_count / total_tested) * 100
            print(f"      → {valid_count}/{total_tested} positions valides ({success_rate:.1f}%)")
            
            if success_rate > 50:
                print(f"      ✅ CANDIDAT PROMETTEUR !")
        else:
            print(f"      → Aucune position testée")
    
    print()


def main():
    replay_path = Path('data/raw/replays/EUW1-7595508345.rofl')
    
    if not replay_path.exists():
        print(f"❌ Replay non trouvé: {replay_path}")
        return
    
    analyze_packets(replay_path)
    test_offset_calibration(replay_path)


if __name__ == '__main__':
    main()
