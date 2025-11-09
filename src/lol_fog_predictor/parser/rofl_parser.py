"""
Parser pour fichiers .rofl (League of Legends Replay)
Implémentation Python basée sur le code Rust de Mowokuma/ROFL
"""

import struct
import json
import zstandard as zstd
from pathlib import Path
from typing import Iterator, Optional, Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class Player:
    """Représente un joueur dans la partie"""
    name: str
    skin: str
    team: str  # "Blue" ou "Red"
    position: str  # "Top", "Jungle", "Mid", "Adc", "Support"


@dataclass
class Metadata:
    """Métadonnées du replay"""
    version: str
    game_len: int  # Durée en millisecondes
    winning_team: str
    players: List[Player]
    raw_json: Dict


class RoflParser:
    """Parser principal pour fichiers .rofl"""
    
    def __init__(self, rofl_path: Path):
        self.path = rofl_path
        with open(rofl_path, 'rb') as f:
            self.buffer = f.read()
        
        self.metadata: Optional[Metadata] = None
        self.chunks_data: Optional[bytes] = None
    
    def parse_metadata(self) -> Metadata:
        """
        Parse les métadonnées du replay (header + JSON stats)
        """
        # Version (offset 0x10, null-terminated string, max 64 bytes)
        version_end = self.buffer.find(b'\x00', 0x10, 0x50)
        if version_end == -1:
            version_end = 0x50
        version_bytes = self.buffer[0x10:version_end]
        version = version_bytes.decode('utf-8', errors='ignore')
        
        # Taille du JSON metadata (last 4 bytes)
        json_size = struct.unpack('<I', self.buffer[-4:])[0]
        
        # JSON metadata
        json_start = len(self.buffer) - 4 - json_size
        json_end = len(self.buffer) - 4
        json_bytes = self.buffer[json_start:json_end]
        json_str = json_bytes.decode('utf-8', errors='ignore')
        
        metadata_json = json.loads(json_str)
        
        # Parse game info
        game_len = metadata_json.get('gameLength', 0)
        stats_json = json.loads(metadata_json.get('statsJson', '[]'))
        
        # Parse players
        players = []
        positions = ["Top", "Jungle", "Mid", "Adc", "Support"]
        
        for i, player_data in enumerate(stats_json):
            name = player_data.get('NAME', 'Unknown')
            skin = player_data.get('SKIN', 'Unknown')
            team_id = player_data.get('TEAM', '100')
            team = "Blue" if team_id == "100" else "Red"
            position = positions[i % 5]
            
            players.append(Player(
                name=name,
                skin=skin,
                team=team,
                position=position
            ))
        
        # Determine winning team
        if stats_json:
            first_player = stats_json[0]
            first_team = first_player.get('TEAM', '100')
            first_win = first_player.get('WIN', 'Fail')
            winning_team = "Blue" if (first_team == "100" and first_win == "Win") else "Red"
        else:
            winning_team = "Unknown"
        
        self.metadata = Metadata(
            version=version,
            game_len=game_len,
            winning_team=winning_team,
            players=players,
            raw_json=metadata_json
        )
        
        return self.metadata
    
    def extract_chunks_data(self) -> bytes:
        """
        Extrait la section des chunks (enlève header, metadata, signature)
        """
        # Calculer taille metadata + 4 bytes
        json_size = struct.unpack('<I', self.buffer[-4:])[0]
        
        # Copier buffer sans metadata et signature
        chunks = bytearray(self.buffer)
        
        # Enlever metadata (derniers json_size + 4 bytes)
        chunks = chunks[:-(json_size + 4)]
        
        # Enlever signature (256 bytes avant metadata)
        chunks = chunks[:-0x100]
        
        # Enlever header ROFL
        chunks = self._skip_rofl_header(chunks)
        
        self.chunks_data = bytes(chunks)
        return self.chunks_data
    
    def _skip_rofl_header(self, buffer: bytearray) -> bytearray:
        """
        Skip le header ROFL variable
        Basé sur le code Rust (très spécifique au format)
        """
        # Skip premiers 0x10 bytes
        buffer = buffer[0x10:]
        
        # Check byte à offset 0xC
        if len(buffer) > 0xC and buffer[0xC] == 1:
            buffer = buffer[0xC:]
        else:
            buffer = buffer[0xD:]
        
        return buffer


def parse_rofl(rofl_path: Path) -> Tuple[Metadata, bytes]:
    """
    Parse un fichier .rofl et retourne metadata + chunks data
    
    Args:
        rofl_path: Chemin vers le fichier .rofl
    
    Returns:
        (metadata, chunks_data): Metadata parsées et données brutes des chunks
    """
    parser = RoflParser(rofl_path)
    metadata = parser.parse_metadata()
    chunks_data = parser.extract_chunks_data()
    
    return metadata, chunks_data
