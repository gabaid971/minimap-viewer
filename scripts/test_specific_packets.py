#!/usr/bin/env python3
"""Test parsing spécifique de packets candidats"""

import sys
import struct
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from lol_fog_predictor.parser import parse_rofl, ChunkParser, BlockParser, parse_path_packet
from lol_fog_predictor.parser.position_extractor import sign_extend


def test_packet_type(packet_id: int, rofl_path: Path):
    """Test un packet_id spécifique"""
    print(f"\n{'='*80}")
    print(f"🔍 TEST PACKET 0x{packet_id:04x}")
    print(f"{'='*80}\n")
    
    metadata, chunks_data = parse_rofl(rofl_path)
    chunk_parser = ChunkParser(chunks_data)
    chunks = chunk_parser.parse_all_chunks()
    
    # Collect blocks de ce packet_id
    target_blocks = []
    for chunk in chunks:
        if chunk.payload:
            block_parser = BlockParser(chunk.payload)
            blocks = block_parser.parse_all_blocks()
            target_blocks.extend([b for b in blocks if b.packet_id == packet_id])
    
    print(f"📦 {len(target_blocks)} blocks trouvés pour packet 0x{packet_id:04x}\n")
    
    if not target_blocks:
        return
    
    # Tester différents offsets
    offset_tests = [
        (7358, 7412),  # Original
        (0, 0),
        (-7358, -7412),
        (14000//2, 14000//2),
        (7500, 7500),
        (10000, 10000),
        (5000, 5000),
    ]
    
    print(f"🧪 Test avec différents offsets de décodage:\n")
    
    for offset_x, offset_y in offset_tests:
        valid_count = 0
        total_tested = 0
        sample_positions = []
        
        for block in target_blocks[:100]:  # Test sur 100 premiers
            path = parse_path_packet(block.timestamp, block.payload)
            
            if path and path.waypoints:
                total_tested += 1
                
                # Recalculer avec offsets testés
                # Note: parse_path_packet utilise les offsets hardcodés
                # On va le refaire manuellement
                try:
                    payload = block.payload
                    cursor = 0
                    
                    parsing_type = struct.unpack('<H', payload[cursor:cursor+2])[0]
                    cursor += 2
                    entity_id = struct.unpack('<I', payload[cursor:cursor+4])[0]
                    cursor += 4
                    speed = struct.unpack('<f', payload[cursor:cursor+4])[0]
                    cursor += 4
                    
                    if (parsing_type & 1) != 0:
                        cursor += 1
                    
                    unk = (parsing_type >> 1) & 0xFF
                    if unk == 0 or unk > 20:
                        continue
                    
                    # Parse premier waypoint
                    if cursor + 4 <= len(payload):
                        x_enc = struct.unpack('<H', payload[cursor:cursor+2])[0]
                        y_enc = struct.unpack('<H', payload[cursor+2:cursor+4])[0]
                        
                        x = sign_extend(x_enc, 16) * 2.0 + offset_x
                        y = sign_extend(y_enc, 16) * 2.0 + offset_y
                        
                        if 0 <= x <= 15000 and 0 <= y <= 15000:
                            valid_count += 1
                            if len(sample_positions) < 5:
                                sample_positions.append((block.timestamp, entity_id, x, y, unk))
                except:
                    continue
        
        if total_tested > 0:
            success_rate = (valid_count / total_tested) * 100
            status = "✅" if success_rate > 50 else "⚠️ " if success_rate > 10 else "  "
            print(f"   {status} offset=({offset_x:6d}, {offset_y:6d}): {valid_count:3d}/{total_tested:3d} valid ({success_rate:5.1f}%)")
            
            if sample_positions:
                for ts, eid, x, y, nwp in sample_positions[:3]:
                    print(f"      t={ts:6.1f}s entity {eid}: ({x:7.1f}, {y:7.1f}) [{nwp} waypoints]")


def main():
    replay = Path('data/raw/replays/EUW1-7595508345.rofl')
    
    # Test les packets candidats
    candidates = [
        0x0152,  # 72k, 17.3 bytes
        0x0240,  # 38k, 24.8 bytes
        0x0017,  # 4.3k, 24.3 bytes  
        0x0021,  # 4.2k, 59.2 bytes
        0x01be,  # 44k, 66.5 bytes
    ]
    
    for pid in candidates:
        test_packet_type(pid, replay)


if __name__ == '__main__':
    main()
