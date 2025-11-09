"""
Client API Riot Games pour récupérer les données de match
Documentation: https://developer.riotgames.com/apis
"""

import requests
import time
import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class MatchTimeline:
    """Timeline complète d'un match avec positions"""
    match_id: str
    game_duration: int  # secondes
    frames: List[Dict]  # Frames avec positions toutes les 60s
    participants: List[Dict]  # Info participants


class RiotAPI:
    """Client pour l'API Riot Games"""
    
    # Régions disponibles
    REGIONS = {
        'euw': 'euw1',      # Europe West
        'na': 'na1',        # North America
        'kr': 'kr',         # Korea
        'eun': 'eun1',      # Europe Nordic & East
    }
    
    # Platforms régionales pour l'API match
    REGIONAL_PLATFORMS = {
        'euw': 'europe',
        'na': 'americas',
        'kr': 'asia',
        'eun': 'europe',
    }
    
    def __init__(self, api_key: str, region: str = 'euw'):
        """
        Args:
            api_key: Clé API Riot (obtenir sur developer.riotgames.com)
            region: 'euw', 'na', 'kr', etc.
        """
        self.api_key = api_key
        self.region = self.REGIONS.get(region.lower(), 'euw1')
        self.regional_platform = self.REGIONAL_PLATFORMS.get(region.lower(), 'europe')
        
        self.base_url = f"https://{self.region}.api.riotgames.com"
        self.regional_url = f"https://{self.regional_platform}.api.riotgames.com"
        
        self.headers = {
            'X-Riot-Token': self.api_key
        }
        
        # Rate limiting (clé dev : 20 req/s, 100 req/2min)
        self.request_times = []
        self.max_requests_per_second = 19
        self.max_requests_per_2min = 95
    
    def _rate_limit(self):
        """Respecter les limites de rate limit"""
        now = time.time()
        
        # Limiter à N req/seconde
        self.request_times = [t for t in self.request_times if now - t < 1]
        if len(self.request_times) >= self.max_requests_per_second:
            sleep_time = 1 - (now - self.request_times[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        # Limiter à N req/2min
        self.request_times = [t for t in self.request_times if now - t < 120]
        if len(self.request_times) >= self.max_requests_per_2min:
            sleep_time = 120 - (now - self.request_times[0])
            if sleep_time > 0:
                print(f"⏳ Rate limit: attente {sleep_time:.1f}s...")
                time.sleep(sleep_time)
        
        self.request_times.append(time.time())
    
    def _request(self, url: str, use_regional: bool = False) -> Optional[Dict]:
        """Faire une requête avec rate limiting"""
        self._rate_limit()
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                # Rate limit exceeded
                retry_after = int(response.headers.get('Retry-After', 120))
                print(f"⚠️  Rate limit dépassé, attente {retry_after}s...")
                time.sleep(retry_after)
                return self._request(url, use_regional)
            elif response.status_code == 404:
                print(f"⚠️  Ressource non trouvée: {url}")
                return None
            else:
                print(f"❌ Erreur {response.status_code}: {url}")
                return None
        except Exception as e:
            print(f"❌ Exception: {e}")
            return None
    
    def get_summoner_by_riot_id(self, game_name: str, tag_line: str) -> Optional[Dict]:
        """
        Récupérer infos summoner par Riot ID (nouveau système)
        
        Args:
            game_name: Nom du joueur (ex: "Faker")
            tag_line: Tag (ex: "EUW", "KR1", "T1")
        
        Returns:
            {'id': '...', 'puuid': '...', 'gameName': '...', 'summonerLevel': 123}
        """
        from urllib.parse import quote
        encoded_name = quote(game_name)
        encoded_tag = quote(tag_line)
        
        # 1. D'abord récupérer le PUUID via l'API Account
        account_url = f"https://{self.regional_platform}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_name}/{encoded_tag}"
        account_data = self._request(account_url, use_regional=True)
        
        if not account_data:
            return None
        
        puuid = account_data.get('puuid')
        
        # 2. Puis récupérer les infos summoner via PUUID
        summoner_url = f"{self.base_url}/lol/summoner/v4/summoners/by-puuid/{puuid}"
        summoner_data = self._request(summoner_url)
        
        if summoner_data:
            # Ajouter les infos du compte
            summoner_data['gameName'] = account_data.get('gameName')
            summoner_data['tagLine'] = account_data.get('tagLine')
        
        return summoner_data
    
    def get_match_history(self, puuid: str, count: int = 20, queue: int = None) -> List[str]:
        """
        Récupérer historique des matchs d'un joueur
        
        Args:
            puuid: PUUID du joueur
            count: Nombre de matchs (max 100)
            queue: Type de queue (420=ranked solo, 400=draft, None=tous)
        
        Returns:
            Liste de match IDs
        """
        url = f"{self.regional_url}/lol/match/v5/matches/by-puuid/{puuid}/ids?count={count}"
        
        if queue:
            url += f"&queue={queue}"
        
        matches = self._request(url, use_regional=True)
        return matches if matches else []
    
    def get_match_details(self, match_id: str) -> Optional[Dict]:
        """
        Récupérer détails d'un match
        
        Returns:
            Match data avec info, metadata, participants
        """
        url = f"{self.regional_url}/lol/match/v5/matches/{match_id}"
        return self._request(url, use_regional=True)
    
    def get_match_timeline(self, match_id: str) -> Optional[Dict]:
        """
        Récupérer timeline d'un match avec positions
        
        ⭐ C'EST LA FONCTION CLÉ POUR TON PROJET ⭐
        
        Returns:
            Timeline avec frames toutes les 60s contenant:
            - positions (x, y) de tous les joueurs
            - events (kills, wards, objectives)
            - gold, xp, items
        """
        url = f"{self.regional_url}/lol/match/v5/matches/{match_id}/timeline"
        return self._request(url, use_regional=True)
    
    def download_matches_with_timelines(
        self, 
        puuid: str, 
        count: int = 10,
        output_dir: Path = Path('data/riot_api')
    ) -> List[str]:
        """
        Télécharger plusieurs matchs + timelines et sauvegarder localement
        
        Args:
            puuid: PUUID du joueur
            count: Nombre de matchs à télécharger
            output_dir: Dossier de sortie
        
        Returns:
            Liste des match IDs téléchargés
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n{'='*80}")
        print(f"📥 TÉLÉCHARGEMENT MATCHS")
        print(f"{'='*80}\n")
        
        # 1. Récupérer liste des matchs
        print(f"1️⃣  Récupération historique ({count} matchs)...")
        match_ids = self.get_match_history(puuid, count=count, queue=None)  # Tous types de games
        
        if not match_ids:
            print("❌ Aucun match trouvé")
            return []
        
        print(f"✅ {len(match_ids)} matchs trouvés\n")
        
        # 2. Télécharger chaque match + timeline
        downloaded = []
        
        for i, match_id in enumerate(match_ids, 1):
            print(f"2️⃣  Match {i}/{len(match_ids)}: {match_id}")
            
            match_file = output_dir / f"{match_id}.json"
            timeline_file = output_dir / f"{match_id}_timeline.json"
            
            # Skip si déjà téléchargé
            if match_file.exists() and timeline_file.exists():
                print(f"   ⏭️  Déjà téléchargé")
                downloaded.append(match_id)
                continue
            
            # Télécharger match details
            if not match_file.exists():
                print(f"   📄 Téléchargement match...")
                match_data = self.get_match_details(match_id)
                
                if match_data:
                    with open(match_file, 'w') as f:
                        json.dump(match_data, f, indent=2)
                    print(f"   ✅ Match sauvegardé")
                else:
                    print(f"   ❌ Échec téléchargement match")
                    continue
            
            # Télécharger timeline
            if not timeline_file.exists():
                print(f"   📊 Téléchargement timeline...")
                timeline_data = self.get_match_timeline(match_id)
                
                if timeline_data:
                    with open(timeline_file, 'w') as f:
                        json.dump(timeline_data, f, indent=2)
                    print(f"   ✅ Timeline sauvegardée")
                    
                    # Afficher stats
                    frames = timeline_data.get('info', {}).get('frames', [])
                    print(f"   📈 {len(frames)} frames (≈{len(frames)} minutes)")
                else:
                    print(f"   ❌ Échec téléchargement timeline")
                    continue
            
            downloaded.append(match_id)
            print()
        
        print(f"\n{'='*80}")
        print(f"✅ TÉLÉCHARGEMENT TERMINÉ: {len(downloaded)}/{len(match_ids)} matchs")
        print(f"{'='*80}\n")
        
        return downloaded


def main():
    """Exemple d'utilisation"""
    
    # 1. Configurer API
    print(f"\n{'='*80}")
    print("🔑 CONFIGURATION API RIOT")
    print(f"{'='*80}\n")
    
    # IMPORTANT: Remplacer par ta vraie clé API
    api_key_file = Path('riot_api_key.txt')
    
    if not api_key_file.exists():
        print("❌ Fichier riot_api_key.txt non trouvé")
        print("\n💡 Pour obtenir une clé API:")
        print("   1. Aller sur https://developer.riotgames.com/")
        print("   2. Se connecter avec ton compte LoL")
        print("   3. Créer une application (Development API Key)")
        print("   4. Copier la clé dans riot_api_key.txt")
        print("\n⚠️  La clé de développement expire après 24h")
        return
    
    api_key = api_key_file.read_text().strip()
    api = RiotAPI(api_key, region='euw')
    
    print(f"✅ API initialisée (région: {api.region})\n")
    
    # 2. Trouver un joueur
    print(f"{'='*80}")
    print("👤 RECHERCHE JOUEUR")
    print(f"{'='*80}\n")
    
    # Demander le Riot ID
    import sys
    if len(sys.argv) > 1:
        riot_id = sys.argv[1]
    else:
        riot_id = input("Riot ID (format: NomJoueur#TAG, ex: Faker#EUW): ").strip()
    
    if not riot_id or '#' not in riot_id:
        print("❌ Format invalide. Utilise: NomJoueur#TAG")
        print("💡 Ton Riot ID se trouve dans le client LoL en haut à gauche")
        return
    
    game_name, tag_line = riot_id.split('#', 1)
    print(f"Recherche: {game_name}#{tag_line}...")
    
    summoner = api.get_summoner_by_riot_id(game_name, tag_line)
    
    if not summoner:
        print(f"❌ Joueur '{game_name}#{tag_line}' non trouvé")
        print("\n💡 Vérifie l'orthographe et le tag (ex: Faker#EUW)")
        return
    
    print(f"✅ Joueur trouvé:")
    print(f"   Nom: {summoner.get('gameName')}#{summoner.get('tagLine')}")
    print(f"   Niveau: {summoner['summonerLevel']}")
    print(f"   PUUID: {summoner['puuid'][:20]}...\n")
    
    # 3. Télécharger matchs
    downloaded = api.download_matches_with_timelines(
        puuid=summoner['puuid'],
        count=5,  # 5 matchs pour tester
        output_dir=Path('data/riot_api/matches')
    )
    
    print(f"\n📁 Fichiers sauvegardés dans: data/riot_api/matches/")
    print(f"   - {len(downloaded)} × match.json")
    print(f"   - {len(downloaded)} × match_timeline.json")


if __name__ == '__main__':
    main()
