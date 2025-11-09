#!/usr/bin/env python3
"""Dump des payloads bruts pour reverse engineering"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from lol_fog_predictor.parser import parse_rofl, ChunkParser, BlockParser


def dump_packet_samples(packet_id: int, rofl_path: Path, max_samples: int = 10):
    """Dump samples de payloads"""
    metadata, chunks_data = parse_rofl(rofl_path)
    chunk_parser = ChunkParser(chunks_data)
    chunks = chunk_parser.parse_all_chunks()
    
    samples = []
    for chunk in chunks:
        if chunk.payload:
            block_parser = BlockParser(chunk.payload)
            blocks = block_parser.parse_all_blocks()
            for block in blocks:
                if block.packet_id == packet_id and len(samples) < max_samples:
                    samples.append(block)
    
    print(f"\n{'='*80}")
    print(f"📦 PACKET 0x{packet_id:04x} - {len(samples)} samples")
    print(f"{'='*80}\n")
    
    for i, block in enumerate(samples, 1):
        print(f"Sample #{i}:")
        print(f"  Timestamp: {block.timestamp:.2f}s")
        print(f"  Length: {block.length} bytes")
        print(f"  Param: 0x{block.param:08x}")
        print(f"  Payload (hex): {block.payload[:64].hex()}")
        if len(block.payload) > 64:
            print(f"              ... ({len(block.payload)} bytes total)")
        print()


if __name__ == '__main__':
    replay = Path('data/raw/replays/EUW1-7595508345.rofl')
    
    # Top packets par fréquence
    top_packets = [
        0x019d,  # 575k
        0x0361,  # 95k
        0x0198,  # 90k
        0x040f,  # 90k
        0x0152,  # 72k
    ]
    
    for pid in top_packets:
        dump_packet_samples(pid, replay, max_samples=5)
