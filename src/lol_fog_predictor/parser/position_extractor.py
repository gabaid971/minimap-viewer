"""
Extraction des positions des joueurs depuis les packets de mouvement
"""

import struct
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass


@dataclass
class PathPacket:
    """Packet de mouvement d'une entité (joueur/mob)"""
    timestamp: float
    entity_id: int
    speed: float
    waypoints: List[Tuple[float, float]]
    
    def get_position_at(self, timestamp: float) -> Tuple[float, float]:
        """
        Calcule la position interpolée à un timestamp donné
        """
        if not self.waypoints:
            return (0.0, 0.0)
        
        if len(self.waypoints) == 1:
            return self.waypoints[0]
        
        delta = timestamp - self.timestamp
        
        if delta <= 1.0:
            return self.waypoints[0]
        
        remaining_time = delta
        
        for i in range(len(self.waypoints) - 1):
            x1, y1 = self.waypoints[i]
            x2, y2 = self.waypoints[i + 1]
            
            distance = ((x1 - x2)**2 + (y1 - y2)**2)**0.5
            dt = distance / self.speed if self.speed > 0 else 0
            
            if remaining_time <= dt:
                t = remaining_time / dt if dt > 0 else 0
                x = x1 + (x2 - x1) * t
                y = y1 + (y2 - y1) * t
                return (x, y)
            
            remaining_time -= dt
        
        return self.waypoints[-1]


def sign_extend(value: int, bits: int) -> int:
    """Étend le signe d'un entier"""
    sign_bit = 1 << (bits - 1)
    return (value & (sign_bit - 1)) - (value & sign_bit)


def parse_path_packet(timestamp: float, payload: bytes) -> Optional[PathPacket]:
    """
    Parse un packet de mouvement (waypoints)
    Basé sur le code Rust PathPacket::parse
    """
    if len(payload) < 10:
        return None
    
    try:
        cursor = 0
        
        # Parse header
        parsing_type = struct.unpack('<H', payload[cursor:cursor+2])[0]
        cursor += 2
        
        entity_id = struct.unpack('<I', payload[cursor:cursor+4])[0]
        cursor += 4
        
        speed = struct.unpack('<f', payload[cursor:cursor+4])[0]
        cursor += 4
        
        # Skip byte si parsing_type & 1
        if (parsing_type & 1) != 0:
            cursor += 1
        
        # Calculer nombre de waypoints
        unk = (parsing_type >> 1) & 0xFF
        if unk == 0:
            return None
        
        if unk > 1:
            unk2 = ((unk - 2) >> 2) + 1
            cursor += unk2
        
        # Parse waypoints encodés
        encoded_coords = []
        v10 = 0
        v13 = 0
        y_coord = 0
        x_coord = 0
        
        while v10 < unk:
            v14 = 2
            v15 = 2
            
            if v10 != 0:
                # Compression delta (complexe)
                v16 = v13
                v17 = v13 & 7
                if v13 < 0:
                    v16 = v13 + 7
                    v17 -= 8
                
                if cursor + (v16 >> 3) < len(payload):
                    v18 = payload[cursor + (v16 >> 3)]
                    v19 = v13 + 1
                    v20 = -((1 << v17) & v18)
                    v21 = (v13 + 1) & 7
                    v14 = 2 - (v20 != 0)
                    
                    if v19 < 0:
                        v19 = v13 + 8
                        v21 -= 8
                    
                    if cursor + (v19 >> 3) < len(payload):
                        v15 = 2 - (((1 << v21) & payload[cursor + (v19 >> 3)]) != 0)
                
                v13 += 2
            
            # Parse X coordinate
            if v14 == 1:
                if cursor < len(payload):
                    x_coord = (x_coord + payload[cursor]) & 0xFFFF
                    cursor += 1
                else:
                    break
            else:
                if cursor + 2 <= len(payload):
                    x_coord = struct.unpack('<H', payload[cursor:cursor+2])[0]
                    cursor += 2
                else:
                    break
            
            # Parse Y coordinate  
            if v15 == 1:
                if cursor < len(payload):
                    y_coord = (y_coord + payload[cursor]) & 0xFFFF
                    cursor += 1
                else:
                    break
            else:
                if cursor + 2 <= len(payload):
                    y_coord = struct.unpack('<H', payload[cursor:cursor+2])[0]
                    cursor += 2
                else:
                    break
            
            encoded_coords.append(x_coord)
            encoded_coords.append(y_coord)
            
            v10 += 1
        
        # Décoder waypoints
        waypoints = []
        for i in range(0, len(encoded_coords), 2):
            x_encoded = encoded_coords[i]
            y_encoded = encoded_coords[i + 1]
            
            # Sign extend et scale
            x = (sign_extend(x_encoded, 16) * 2.0 + 7358.0)
            y = (sign_extend(y_encoded, 16) * 2.0 + 7412.0)
            
            waypoints.append((x, y))
        
        return PathPacket(
            timestamp=timestamp,
            entity_id=entity_id,
            speed=speed,
            waypoints=waypoints
        )
    
    except Exception as e:
        # Parsing échoué
        return None


class PositionTracker:
    """Track les positions des entités au fil du temps"""
    
    def __init__(self):
        # entity_id -> dernier PathPacket
        self.last_packets: Dict[int, PathPacket] = {}
    
    def update(self, packet: PathPacket):
        """Met à jour avec un nouveau packet"""
        self.last_packets[packet.entity_id] = packet
    
    def get_position(self, entity_id: int, timestamp: float) -> Optional[Tuple[float, float]]:
        """Récupère la position d'une entité à un timestamp"""
        if entity_id not in self.last_packets:
            return None
        
        packet = self.last_packets[entity_id]
        return packet.get_position_at(timestamp)
    
    def get_all_positions(self, timestamp: float) -> Dict[int, Tuple[float, float]]:
        """Récupère toutes les positions à un timestamp"""
        positions = {}
        for entity_id, packet in self.last_packets.items():
            pos = packet.get_position_at(timestamp)
            positions[entity_id] = pos
        return positions
