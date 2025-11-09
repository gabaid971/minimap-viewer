#!/usr/bin/env python3
"""
Explorer les endpoints de League Client API
"""

import sys
from pathlib import Path
import requests
import json
from urllib3.exceptions import InsecureRequestWarning

# Désactiver warnings SSL
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

sys.path.insert(0, str(Path(__file__).parent))
from capture_replay_api import LeagueClientAPI


def explore_endpoints(api: LeagueClientAPI):
    """Tester différents endpoints pour voir ce qui est disponible"""
    
    endpoints = [
        # Replay endpoints
        '/lol-replays/v1/metadata',
        '/lol-replays/v1/playback',
        '/lol-replays/v1/configuration',
        '/lol-replays/v1/rofls/scan',
        
        # Game endpoints
        '/lol-gameflow/v1/session',
        '/lol-gameflow/v1/gameflow-phase',
        
        # Game data
        '/lol-game-data/assets/v1/champion-summary.json',
        
        # Swagger docs
        '/swagger/v2/swagger.json',
        '/swagger/v3/openapi.json',
        
        # Help
        '/help',
    ]
    
    print(f"\n{'='*80}")
    print("🔍 EXPLORATION API ENDPOINTS")
    print(f"{'='*80}\n")
    
    results = {}
    
    for endpoint in endpoints:
        try:
            response = api.session.get(
                f"{api.base_url}{endpoint}",
                timeout=5
            )
            
            status = "✅" if response.status_code == 200 else "❌"
            print(f"{status} {endpoint}")
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   Type: {type(data).__name__}")
                    
                    if isinstance(data, dict):
                        print(f"   Keys: {list(data.keys())[:10]}")
                    elif isinstance(data, list):
                        print(f"   Length: {len(data)}")
                    
                    results[endpoint] = data
                    
                except Exception as e:
                    print(f"   Data: {response.text[:100]}")
                    results[endpoint] = response.text
            
            print()
            
        except Exception as e:
            print(f"❌ {endpoint}")
            print(f"   Error: {e}\n")
    
    return results


def save_api_docs(api: LeagueClientAPI, output_dir: Path):
    """Télécharger la documentation Swagger de l'API"""
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    swagger_endpoints = [
        ('/swagger/v2/swagger.json', 'swagger_v2.json'),
        ('/swagger/v3/openapi.json', 'swagger_v3.json'),
        ('/help', 'help.html'),
    ]
    
    print(f"\n{'='*80}")
    print("📚 TÉLÉCHARGEMENT DOCUMENTATION API")
    print(f"{'='*80}\n")
    
    for endpoint, filename in swagger_endpoints:
        try:
            response = api.session.get(f"{api.base_url}{endpoint}", timeout=10)
            
            if response.status_code == 200:
                output_file = output_dir / filename
                
                if filename.endswith('.json'):
                    data = response.json()
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2)
                else:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                
                print(f"✅ {filename}")
                print(f"   Sauvegardé: {output_file}\n")
            else:
                print(f"❌ {endpoint} - Status {response.status_code}\n")
                
        except Exception as e:
            print(f"❌ {endpoint} - Error: {e}\n")


def list_all_endpoints(api: LeagueClientAPI):
    """Lister tous les endpoints disponibles depuis swagger"""
    
    try:
        response = api.session.get(f"{api.base_url}/swagger/v2/swagger.json", timeout=10)
        
        if response.status_code != 200:
            print("❌ Impossible de récupérer swagger.json")
            return
        
        swagger = response.json()
        
        print(f"\n{'='*80}")
        print("📋 TOUS LES ENDPOINTS DISPONIBLES")
        print(f"{'='*80}\n")
        
        # Grouper par tag
        endpoints_by_tag = {}
        
        for path, methods in swagger.get('paths', {}).items():
            for method, details in methods.items():
                if method in ['get', 'post', 'put', 'delete', 'patch']:
                    tags = details.get('tags', ['Other'])
                    tag = tags[0] if tags else 'Other'
                    
                    if tag not in endpoints_by_tag:
                        endpoints_by_tag[tag] = []
                    
                    endpoints_by_tag[tag].append({
                        'method': method.upper(),
                        'path': path,
                        'summary': details.get('summary', ''),
                    })
        
        # Afficher par catégorie
        for tag in sorted(endpoints_by_tag.keys()):
            print(f"\n## {tag}")
            print(f"{'-'*80}")
            
            for endpoint in sorted(endpoints_by_tag[tag], key=lambda x: x['path']):
                print(f"  {endpoint['method']:6} {endpoint['path']}")
                if endpoint['summary']:
                    print(f"         → {endpoint['summary']}")
        
        print(f"\n{'='*80}")
        print(f"Total: {sum(len(v) for v in endpoints_by_tag.values())} endpoints")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")


def main():
    api = LeagueClientAPI()
    
    if not api.connect():
        print("❌ Impossible de se connecter à l'API")
        return
    
    print(f"✅ Connecté\n")
    
    # 1. Tester quelques endpoints
    results = explore_endpoints(api)
    
    # 2. Télécharger docs
    docs_dir = Path('data/api_docs')
    save_api_docs(api, docs_dir)
    
    # 3. Lister tous les endpoints
    list_all_endpoints(api)
    
    # 4. Sauvegarder résultats exploration
    output_file = Path('data/api_exploration.json')
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Résultats sauvegardés: {output_file}")


if __name__ == '__main__':
    main()
