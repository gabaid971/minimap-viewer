#!/usr/bin/env python3
"""
Script pour extraire les métadonnées basiques d'un fichier .rofl
Sans nécessiter les patch files (lecture simple, pas de positions détaillées)
"""

import json
import struct
import sys
from pathlib import Path


def parse_rofl_metadata(rofl_path: Path) -> dict:
    """
    Parse les métadonnées de base d'un fichier .rofl
    (header, stats JSON, mais PAS les positions frame-by-frame)
    """
    with open(rofl_path, 'rb') as f:
        # Lire header
        magic = f.read(6).decode('utf-8', errors='ignore')
        
        # Lire les offsets des sections
        f.seek(262)  # Offset vers metadata length
        metadata_offset = struct.unpack('<I', f.read(4))[0]
        metadata_length = struct.unpack('<I', f.read(4))[0]
        
        # Lire metadata JSON
        f.seek(metadata_offset)
        metadata_bytes = f.read(metadata_length)
        
        # Décoder JSON
        metadata_str = metadata_bytes.decode('utf-8', errors='ignore')
        
        # Nettoyer et parser
        # Le JSON peut contenir des null bytes
        metadata_str = metadata_str.replace('\x00', '')
        
        try:
            metadata = json.loads(metadata_str)
        except json.JSONDecodeError as e:
            print(f"Erreur parsing JSON: {e}")
            # Essayer de trouver le JSON dans la chaîne
            start = metadata_str.find('{')
            end = metadata_str.rfind('}') + 1
            if start != -1 and end > start:
                metadata = json.loads(metadata_str[start:end])
            else:
                raise
        
        return metadata


def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_rofl_basic.py <fichier.rofl>")
        sys.exit(1)
    
    rofl_path = Path(sys.argv[1])
    
    if not rofl_path.exists():
        print(f"❌ Fichier non trouvé: {rofl_path}")
        sys.exit(1)
    
    print(f"📂 Parsing: {rofl_path.name}")
    
    try:
        metadata = parse_rofl_metadata(rofl_path)
        
        print("\n✅ Métadonnées extraites:")
        print(f"  - Version: {metadata.get('gameVersion', 'N/A')}")
        print(f"  - Durée: {metadata.get('gameLength', 0) / 1000:.1f}s")
        print(f"  - Chunks: {metadata.get('lastGameChunkId', 'N/A')}")
        print(f"  - KeyFrames: {metadata.get('lastKeyFrameId', 'N/A')}")
        
        # Parser stats JSON si présent
        if 'statsJson' in metadata:
            stats = json.loads(metadata['statsJson'])
            print(f"\n👥 Joueurs: {len(stats)}")
            
            for i, player in enumerate(stats, 1):
                print(f"  {i}. {player.get('NAME', 'Unknown'):20s} - {player.get('SKIN', 'Unknown'):15s} (Team {player.get('TEAM', '?')})")
        
        # Sauvegarder metadata
        output_path = Path('data/parsed') / f"{rofl_path.stem}_metadata.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Métadonnées sauvegardées: {output_path}")
        print("\n⚠️  NOTE: Ce parser basique n'extrait PAS les positions frame-by-frame")
        print("   Pour cela, le binaire ROFL Rust nécessite les fichiers patch correspondants.")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
