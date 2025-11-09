"""
Parser pour chunks ZSTD dans les replays LoL
"""

import struct
import zstandard as zstd
from typing import Iterator, Optional, List
from dataclasses import dataclass


@dataclass
class Chunk:
    """Représente un chunk dans le replay"""
    id: int
    type_: int
    id_2: int
    uncompressed_len: int
    compressed_len: int
    payload: Optional[bytes] = None


class ChunkParser:
    """Parse les chunks compressés ZSTD"""
    
    def __init__(self, chunks_data: bytes):
        self.data = bytearray(chunks_data)
        self.cursor = 0
        self.chunks: List[Chunk] = []
    
    def parse_all_chunks(self) -> List[Chunk]:
        """
        Parse tous les chunks du replay
        """
        chunks = []
        
        while self.cursor < len(self.data):
            chunk = self._parse_next_chunk()
            if chunk is None:
                break
            chunks.append(chunk)
        
        self.chunks = chunks
        return chunks
    
    def _parse_next_chunk(self) -> Optional[Chunk]:
        """Parse le prochain chunk"""
        if self.cursor + 17 > len(self.data):
            return None
        
        # Header: 17 bytes
        # id: u32 (4 bytes)
        # type: u8 (1 byte)
        # id_2: u32 (4 bytes)
        # uncompressed_len: u32 (4 bytes)
        # compressed_len: u32 (4 bytes)
        
        chunk_id = struct.unpack('<I', self.data[self.cursor:self.cursor+4])[0]
        self.cursor += 4
        
        chunk_type = self.data[self.cursor]
        self.cursor += 1
        
        id_2 = struct.unpack('<I', self.data[self.cursor:self.cursor+4])[0]
        self.cursor += 4
        
        uncompressed_len = struct.unpack('<I', self.data[self.cursor:self.cursor+4])[0]
        self.cursor += 4
        
        compressed_len = struct.unpack('<I', self.data[self.cursor:self.cursor+4])[0]
        self.cursor += 4
        
        # Si compressed_len == 0, skip uncompressed_len bytes (pas de décompression)
        if compressed_len == 0:
            # Skip uncompressed_len bytes
            self.cursor += uncompressed_len
            chunk = Chunk(
                id=chunk_id,
                type_=chunk_type,
                id_2=id_2,
                uncompressed_len=uncompressed_len,
                compressed_len=0,
                payload=None  # Pas de payload
            )
            return chunk
        
        # Payload compressé
        if self.cursor + compressed_len > len(self.data):
            # Pas assez de données
            return None
        
        compressed_payload = bytes(self.data[self.cursor:self.cursor+compressed_len])
        self.cursor += compressed_len
        
        # Décompresser avec ZSTD
        try:
            dctx = zstd.ZstdDecompressor()
            # Essayer avec max_output_size plus large
            max_size = max(uncompressed_len * 10, 10 * 1024 * 1024)  # Au moins 10MB
            uncompressed_payload = dctx.decompress(compressed_payload, max_output_size=max_size)
        except zstd.ZstdError as e:
            # Si content size error, essayer sans limit
            try:
                uncompressed_payload = dctx.decompress(compressed_payload)
            except Exception as e2:
                print(f"⚠️  Erreur décompression chunk {chunk_id}: {e2}")
                uncompressed_payload = compressed_payload  # Fallback
        except Exception as e:
            print(f"⚠️  Erreur décompression chunk {chunk_id}: {e}")
            uncompressed_payload = compressed_payload  # Fallback
        
        chunk = Chunk(
            id=chunk_id,
            type_=chunk_type,
            id_2=id_2,
            uncompressed_len=uncompressed_len,
            compressed_len=compressed_len,
            payload=uncompressed_payload
        )
        
        return chunk
    
    def get_keyframe_chunks(self) -> List[Chunk]:
        """
        Retourne seulement les chunks de type KeyFrame (type == 1)
        """
        return [chunk for chunk in self.chunks if chunk.type_ == 1]
    
    def get_chunk_chunks(self) -> List[Chunk]:
        """
        Retourne seulement les chunks de type Chunk (type == 2)
        """
        return [chunk for chunk in self.chunks if chunk.type_ == 2]
