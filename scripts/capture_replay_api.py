#!/usr/bin/env python3
"""
Capture de données depuis League Client API pendant lecture replay
API accessible via HTTP local quand LoL tourne
"""

import requests
import json
import time
import base64
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
import urllib3

# Désactiver warnings SSL (API local utilise certificat self-signed)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class PlayerState:
    """État d'un joueur à un instant t"""
    timestamp: float
    champion: str
    team: str
    position: tuple  # (x, y)
    level: int
    gold: int
    health: float
    mana: float


class LeagueClientAPI:
    """Interface avec League Client API"""
    
    def __init__(self):
        self.base_url = None
        self.auth_header = None
        self.session = requests.Session()
        self.session.verify = False  # Ignorer SSL pour localhost
    
    def connect(self) -> bool:
        """
        Se connecte à l'API du client LoL
        Lit les credentials depuis lockfile
        """
        # Chercher lockfile (créé quand LoL tourne)
        lockfile_paths = [
            Path("/mnt/c/Riot Games/League of Legends/lockfile"),
            Path(f"/mnt/c/Users/{Path.home().name}/AppData/Local/Riot Games/League of Legends/lockfile"),
        ]
        
        lockfile = None
        for path in lockfile_paths:
            if path.exists():
                lockfile = path
                break
        
        if not lockfile:
            print("❌ Lockfile non trouvé. Le client LoL est-il lancé ?")
            return False
        
        # Parse lockfile
        # Format: name:pid:port:password:protocol
        try:
            content = lockfile.read_text().strip()
            parts = content.split(':')
            
            if len(parts) != 5:
                print(f"⚠️  Format lockfile invalide: {content}")
                return False
            
            _, pid, port, password, protocol = parts
            
            # Construire auth
            auth_token = base64.b64encode(f"riot:{password}".encode()).decode()
            self.auth_header = f"Basic {auth_token}"
            
            # WSL → Windows : utiliser IP Windows au lieu de 127.0.0.1
            import subprocess
            try:
                windows_ip_result = subprocess.run(
                    ['bash', '-c', 'ip route show | grep default | awk \'{print $3}\''],
                    capture_output=True, text=True, timeout=2
                )
                windows_ip = windows_ip_result.stdout.strip()
                
                if not windows_ip:
                    windows_ip = '127.0.0.1'  # Fallback si pas WSL
            except:
                windows_ip = '127.0.0.1'  # Fallback
            
            self.base_url = f"https://{windows_ip}:{port}"
            
            # Configurer session avec headers
            # IMPORTANT: Spoofer Host et Origin pour contourner CORS de l'API LoL
            self.session.headers.update({
                'Authorization': self.auth_header,
                'Host': f'127.0.0.1:{port}',  # Spoof pour CORS
                'Origin': f'https://127.0.0.1:{port}'  # Spoof pour CORS
            })
            
            print(f"✅ Connecté à League Client API (port {port})")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lecture lockfile: {e}")
            return False
    
    def _request(self, endpoint: str, method: str = "GET") -> Optional[Dict]:
        """Requête API générique"""
        if not self.base_url:
            return None
        
        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": self.auth_header}
        
        try:
            if method == "GET":
                response = self.session.get(url, headers=headers, timeout=2)
            elif method == "POST":
                response = self.session.post(url, headers=headers, timeout=2)
            else:
                return None
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except:
            return None
    
    def get_replay_info(self) -> Optional[Dict]:
        """
        Récupère infos sur le replay en cours
        Endpoint: /lol-replays/v1/metadata
        """
        return self._request("/lol-replays/v1/metadata")
    
    def get_replay_playback(self) -> Optional[Dict]:
        """
        État de la lecture (play/pause, timeline, vitesse)
        Endpoint: /lol-replays/v1/playback
        """
        return self._request("/lol-replays/v1/playback")
    
    def get_game_stats(self) -> Optional[Dict]:
        """
        Statistiques de la partie
        Endpoint: /lol-end-of-game/v1/state/stats
        """
        return self._request("/lol-gameflow/v1/session")
    
    def record_replay_data(self, output_file: Path, duration_seconds: int = 300, interval: float = 1.0):
        """
        Enregistre les données du replay pendant sa lecture
        
        Args:
            output_file: Fichier JSON de sortie
            duration_seconds: Durée max d'enregistrement
            interval: Intervalle entre captures (secondes)
        """
        print(f"\n📹 Enregistrement replay data...")
        print(f"   Durée max: {duration_seconds}s")
        print(f"   Intervalle: {interval}s")
        print(f"   Output: {output_file}")
        
        if not self.connect():
            print("❌ Impossible de se connecter à l'API")
            return
        
        data_points = []
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration_seconds:
                # Capturer état actuel
                playback = self.get_replay_playback()
                
                if playback:
                    data_point = {
                        'timestamp': time.time() - start_time,
                        'game_time': playback.get('time', 0),
                        'paused': playback.get('paused', False),
                        'speed': playback.get('speed', 1.0),
                    }
                    
                    # Ajouter stats si disponibles
                    stats = self.get_game_stats()
                    if stats:
                        data_point['stats'] = stats
                    
                    data_points.append(data_point)
                    
                    print(f"   [{len(data_points)}] t={data_point['game_time']:.1f}s (speed={data_point['speed']}x)")
                
                time.sleep(interval)
        
        except KeyboardInterrupt:
            print("\n⚠️  Enregistrement interrompu")
        
        # Sauvegarder
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump({
                'metadata': self.get_replay_info(),
                'data_points': data_points
            }, f, indent=2)
        
        print(f"\n✅ {len(data_points)} points enregistrés dans {output_file}")


def main():
    """Test de l'API"""
    api = LeagueClientAPI()
    
    print("🔍 Recherche client LoL actif...")
    
    if not api.connect():
        print("\n💡 Lancez d'abord un replay avec:")
        print("   python scripts/launch_replay.py")
        return
    
    # Test requêtes
    print("\n📊 Informations replay:")
    
    replay_info = api.get_replay_info()
    if replay_info:
        print(f"   Version: {replay_info.get('gameVersion', 'N/A')}")
        print(f"   Durée: {replay_info.get('gameLength', 0) / 1000:.1f}s")
    
    playback = api.get_replay_playback()
    if playback:
        print(f"\n⏯️  État lecture:")
        print(f"   Temps: {playback.get('time', 0):.1f}s")
        print(f"   Pause: {playback.get('paused', False)}")
        print(f"   Vitesse: {playback.get('speed', 1.0)}x")
    
    print("\n💡 Pour enregistrer les données:")
    print("   api.record_replay_data(Path('output.json'), duration_seconds=60)")


if __name__ == '__main__':
    main()
