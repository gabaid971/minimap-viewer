#!/usr/bin/env python3
"""Debug chunks au niveau bas"""

import sys
import struct
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from lol_fog_predictor.parser import parse_rofl


def debug_chunks_raw(rofl_path: Path):
    """Analyse bas niveau des chunks"""
    metadata, chunks_data = parse_rofl(rofl_path)
    
    print(f"📦 Chunks data: {len(chunks_data)} bytes\n")
    
    cursor = 0
    chunk_num = 0
    
    while cursor + 17 <= len(chunks_data) and chunk_num < 10:
        print(f"Chunk #{chunk_num} @ offset {cursor}")
        
        # Header
        chunk_id = struct.unpack('<I', chunks_data[cursor:cursor+4])[0]
        chunk_type = chunks_data[cursor+4]
        id_2 = struct.unpack('<I', chunks_data[cursor+5:cursor+9])[0]
        uncomp_len = struct.unpack('<I', chunks_data[cursor+9:cursor+13])[0]
        comp_len = struct.unpack('<I', chunks_data[cursor+13:cursor+17])[0]
        
        print(f"  ID: {chunk_id}")
        print(f"  Type: {chunk_type}")
        print(f"  ID2: {id_2}")
        print(f"  Uncompressed: {uncomp_len}")
        print(f"  Compressed: {comp_len}")
        
        cursor += 17
        
        # Payload
        if cursor + comp_len <= len(chunks_data):
            payload_start = chunks_data[cursor:cursor+min(32, comp_len)]
            print(f"  Payload start: {payload_start.hex()}")
            
            # Check ZSTD magic
            if comp_len >= 4:
                magic = struct.unpack('<I', chunks_data[cursor:cursor+4])[0]
                print(f"  Magic: 0x{magic:08x} (ZSTD=0x28B52FFD ou 0xFD2FB528)")
            
            cursor += comp_len
        else:
            print(f"  ⚠️  Pas assez de données pour payload ({comp_len} bytes needed)")
            break
        
        print()
        chunk_num += 1
    
    print(f"Total processed: {cursor} / {len(chunks_data)} bytes")


if __name__ == '__main__':
    debug_chunks_raw(Path('data/raw/replays/EUW1-7595508345.rofl'))
