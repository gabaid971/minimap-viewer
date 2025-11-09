"""
Parser pour blocks dans les chunks
Extrait timestamp, packet_id, payload
"""

import struct
from typing import Iterator, Optional, List
from dataclasses import dataclass


@dataclass
class Block:
    """Représente un block dans un chunk"""
    length: int
    timestamp: float  # Temps en secondes
    packet_id: int
    param: int
    payload: bytes


class BlockParser:
    """Parse les blocks à l'intérieur d'un chunk"""
    
    def __init__(self, chunk_payload: bytes):
        self.data = bytearray(chunk_payload)
        self.cursor = 0
        
        self.acc_time = 0.0  # Temps accumulé
        self.previous_packet_id = 0
        self.previous_param = 0
    
    def parse_all_blocks(self) -> List[Block]:
        """Parse tous les blocks du chunk"""
        blocks = []
        
        while self.cursor < len(self.data):
            block = self._parse_next_block()
            if block is None:
                break
            blocks.append(block)
        
        return blocks
    
    def _parse_next_block(self) -> Optional[Block]:
        """
        Parse le prochain block
        Format avec marker byte qui indique quels champs sont présents
        """
        if self.cursor >= len(self.data):
            return None
        
        # Marker byte
        marker = self.data[self.cursor]
        self.cursor += 1
        
        # === TIMESTAMP ===
        if marker & 0x80:
            # Timestamp relatif (1 byte en ms)
            if self.cursor >= len(self.data):
                return None
            timestamp_delta = self.data[self.cursor]
            self.cursor += 1
            self.acc_time += timestamp_delta * 0.001
        else:
            # Timestamp absolu (4 bytes float)
            if self.cursor + 4 > len(self.data):
                return None
            self.acc_time = struct.unpack('<f', self.data[self.cursor:self.cursor+4])[0]
            self.cursor += 4
        
        timestamp = self.acc_time
        
        # === BLOCK LENGTH ===
        if marker & 0x10:
            # Length sur 1 byte (u8)
            if self.cursor >= len(self.data):
                return None
            block_len = self.data[self.cursor]
            self.cursor += 1
        else:
            # Length sur 4 bytes (u32)
            if self.cursor + 4 > len(self.data):
                return None
            block_len = struct.unpack('<I', self.data[self.cursor:self.cursor+4])[0]
            self.cursor += 4
        
        # === PACKET ID ===
        if marker & 0x40:
            # Réutilise le packet_id précédent
            packet_id = self.previous_packet_id
        else:
            # Nouveau packet_id (u16)
            if self.cursor + 2 > len(self.data):
                return None
            packet_id = struct.unpack('<H', self.data[self.cursor:self.cursor+2])[0]
            self.cursor += 2
        
        # === PARAM ===
        if marker & 0x20:
            # Param relatif (1 byte offset)
            if self.cursor >= len(self.data):
                return None
            param_delta = self.data[self.cursor]
            self.cursor += 1
            param = param_delta + self.previous_param
        else:
            # Param absolu (u32)
            if self.cursor + 4 > len(self.data):
                return None
            param = struct.unpack('<I', self.data[self.cursor:self.cursor+4])[0]
            self.cursor += 4
        
        # === PAYLOAD ===
        if self.cursor + block_len > len(self.data):
            # Pas assez de données pour le payload
            return None
        
        payload = bytes(self.data[self.cursor:self.cursor+block_len])
        self.cursor += block_len
        
        # Mettre à jour état
        self.previous_packet_id = packet_id
        self.previous_param = param
        
        return Block(
            length=block_len,
            timestamp=timestamp,
            packet_id=packet_id,
            param=param,
            payload=payload
        )
