#!/usr/bin/env python3
"""
Script pour lancer automatiquement des replays .rofl avec le client LoL
depuis WSL en contrôlant Windows
"""

import subprocess
import time
import json
from pathlib import Path, PureWindowsPath
from typing import Optional


class LoLReplayLauncher:
    """Lance et contrôle les replays LoL depuis WSL"""
    
    def __init__(self, lol_path: Optional[str] = None):
        """
        Args:
            lol_path: Chemin vers League of Legends (détection auto si None)
        """
        if lol_path is None:
            # Chemins standards
            possible_paths = [
                "/mnt/c/Riot Games/League of Legends",
                "/mnt/c/Program Files/Riot Games/League of Legends",
                "/mnt/d/Riot Games/League of Legends",
            ]
            
            for path in possible_paths:
                if Path(path).exists():
                    self.lol_path = Path(path)
                    break
            else:
                raise FileNotFoundError("LoL installation non trouvée. Spécifiez lol_path.")
        else:
            self.lol_path = Path(lol_path)
        
        self.league_client = self.lol_path / "LeagueClient.exe"
        
        if not self.league_client.exists():
            raise FileNotFoundError(f"LeagueClient.exe non trouvé dans {self.lol_path}")
        
        print(f"✅ LoL trouvé: {self.lol_path}")
    
    def wsl_path_to_windows(self, wsl_path: Path) -> str:
        """
        Convertit un chemin WSL vers chemin Windows
        Ex: /mnt/c/Users/... -> C:\\Users\\...
        """
        path_str = str(wsl_path.absolute())
        
        # /mnt/c/... -> C:\...
        if path_str.startswith('/mnt/'):
            drive = path_str[5].upper()  # c, d, etc.
            rest = path_str[6:].replace('/', '\\')
            return f"{drive}:{rest}"
        
        # Déjà un chemin Windows
        return path_str
    
    def launch_replay(self, rofl_path: Path, wait: bool = True) -> subprocess.Popen:
        """
        Lance un replay .rofl avec le client LoL
        
        Args:
            rofl_path: Chemin vers le fichier .rofl
            wait: Si True, attend que le processus démarre
        
        Returns:
            Processus lancé
        """
        if not rofl_path.exists():
            raise FileNotFoundError(f"Replay non trouvé: {rofl_path}")
        
        # Convertir chemin WSL -> Windows
        rofl_windows = self.wsl_path_to_windows(rofl_path)
        league_client_windows = self.wsl_path_to_windows(self.league_client)
        
        print(f"\n🎮 Lancement replay:")
        print(f"   Replay: {rofl_windows}")
        print(f"   Client: {league_client_windows}")
        
        # Lancer avec cmd.exe (depuis WSL)
        cmd = [
            'cmd.exe', '/c', 'start', '',
            league_client_windows,
            rofl_windows
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if wait:
            print("⏳ Attente démarrage client LoL (5s)...")
            time.sleep(5)
        
        print("✅ Replay lancé !")
        return process
    
    def is_lol_running(self) -> bool:
        """Vérifie si le client LoL est en cours d'exécution"""
        try:
            result = subprocess.run(
                ['tasklist.exe'],
                capture_output=True,
                text=True
            )
            return 'LeagueClient.exe' in result.stdout or 'League of Legends.exe' in result.stdout
        except:
            return False
    
    def wait_for_lol_close(self, timeout: int = 3600):
        """
        Attend que LoL se ferme (fin du replay)
        
        Args:
            timeout: Timeout en secondes (défaut 1h)
        """
        print(f"\n⏳ Attente fermeture LoL (timeout {timeout}s)...")
        
        start = time.time()
        was_running = False
        
        while time.time() - start < timeout:
            running = self.is_lol_running()
            
            if running:
                was_running = True
            elif was_running:
                # LoL était ouvert, maintenant fermé
                print("✅ LoL fermé")
                return True
            
            time.sleep(2)
        
        print("⚠️  Timeout atteint")
        return False
    
    def kill_lol(self):
        """Force la fermeture du client LoL"""
        print("🔪 Fermeture forcée LoL...")
        subprocess.run(['taskkill.exe', '/F', '/IM', 'LeagueClient.exe'], 
                      capture_output=True)
        subprocess.run(['taskkill.exe', '/F', '/IM', 'League of Legends.exe'], 
                      capture_output=True)
        time.sleep(2)
        print("✅ Processus terminés")


def main():
    """Test du launcher"""
    launcher = LoLReplayLauncher()
    
    # Trouver un replay
    replay_dir = Path('data/raw/replays')
    replays = list(replay_dir.glob('*.rofl'))
    
    if not replays:
        print("❌ Aucun replay trouvé dans data/raw/replays/")
        return
    
    replay = replays[0]
    print(f"\n📂 Replay sélectionné: {replay.name}")
    
    # Lancer
    launcher.launch_replay(replay)
    
    print("\n💡 Le replay est ouvert dans LoL !")
    print("   - Vous pouvez le contrôler manuellement")
    print("   - Ou utiliser League Client API pour capturer les données")
    print("\n⚠️  Fermez LoL quand vous avez fini")
    
    # Optionnel: attendre fermeture
    # launcher.wait_for_lol_close()


if __name__ == '__main__':
    main()
