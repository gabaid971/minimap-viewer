#!/usr/bin/env python3
"""
Proxy HTTP simple pour exposer l'API LoL à WSL
À exécuter côté WINDOWS (pas WSL)

Usage Windows:
  python lol_api_proxy.py

Usage WSL:
  curl http://172.26.112.1:8765/help
"""

import http.server
import socketserver
import requests
import base64
import json
from pathlib import Path
from urllib.parse import urlparse
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class LoLAPIProxyHandler(http.server.BaseHTTPRequestHandler):
    """Proxy qui redirige requêtes vers API LoL locale"""
    
    lol_api_url = None
    lol_auth = None
    
    def do_GET(self):
        """Gérer requêtes GET"""
        self._proxy_request('GET')
    
    def do_POST(self):
        """Gérer requêtes POST"""
        self._proxy_request('POST')
    
    def do_PUT(self):
        """Gérer requêtes PUT"""
        self._proxy_request('PUT')
    
    def do_DELETE(self):
        """Gérer requêtes DELETE"""
        self._proxy_request('DELETE')
    
    def _proxy_request(self, method):
        """Rediriger requête vers API LoL"""
        
        # Construire URL cible
        target_url = f"{self.lol_api_url}{self.path}"
        
        print(f"{method} {self.path} → {target_url}")
        
        try:
            # Préparer headers
            headers = {
                'Authorization': f'Basic {self.lol_auth}'
            }
            
            # Lire body si POST/PUT
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else None
            
            # Faire requête vers API LoL
            response = requests.request(
                method=method,
                url=target_url,
                headers=headers,
                data=body,
                verify=False,
                timeout=10
            )
            
            # Renvoyer réponse
            self.send_response(response.status_code)
            
            # Copier headers
            for header, value in response.headers.items():
                if header.lower() not in ['transfer-encoding', 'connection']:
                    self.send_header(header, value)
            
            self.end_headers()
            self.wfile.write(response.content)
            
            print(f"  ✅ {response.status_code} ({len(response.content)} bytes)")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            error = {
                'error': str(e),
                'target': target_url
            }
            self.wfile.write(json.dumps(error).encode())
    
    def log_message(self, format, *args):
        """Silencer logs automatiques"""
        pass


def get_lol_credentials():
    """Lire lockfile LoL (chemins Windows)"""
    
    lockfile_paths = [
        Path(r"C:\Riot Games\League of Legends\lockfile"),
        Path.home() / r"AppData\Local\Riot Games\League of Legends\lockfile",
    ]
    
    for lockfile in lockfile_paths:
        if lockfile.exists():
            content = lockfile.read_text().strip()
            parts = content.split(':')
            
            if len(parts) == 5:
                _, pid, port, password, protocol = parts
                return {
                    'port': port,
                    'password': password,
                    'auth': base64.b64encode(f"riot:{password}".encode()).decode()
                }
    
    return None


def main():
    print(f"\n{'='*80}")
    print("🌉 LOL API PROXY - Windows → WSL Bridge")
    print(f"{'='*80}\n")
    
    # Lire credentials LoL
    creds = get_lol_credentials()
    
    if not creds:
        print("❌ Lockfile LoL non trouvé. Le client est-il lancé ?")
        print("\n   Chemins testés:")
        print("   - C:\\Riot Games\\League of Legends\\lockfile")
        print(f"   - {Path.home()}\\AppData\\Local\\Riot Games\\League of Legends\\lockfile")
        return
    
    print(f"✅ LoL API détectée (port {creds['port']})")
    
    # Configurer handler
    LoLAPIProxyHandler.lol_api_url = f"https://127.0.0.1:{creds['port']}"
    LoLAPIProxyHandler.lol_auth = creds['auth']
    
    # Démarrer serveur
    PROXY_PORT = 8765
    HOST = '0.0.0.0'  # Écouter sur toutes interfaces
    
    print(f"\n🚀 Démarrage proxy sur {HOST}:{PROXY_PORT}")
    print(f"   API LoL: https://127.0.0.1:{creds['port']}")
    print(f"\n💡 Depuis WSL, utiliser:")
    print(f"   http://<WINDOWS_IP>:{PROXY_PORT}/help")
    print(f"\n   Pour trouver WINDOWS_IP depuis WSL:")
    print(f"   ip route show | grep default | awk '{{print $3}}'")
    print(f"\n{'='*80}\n")
    print("🎧 Proxy actif. Ctrl+C pour arrêter.\n")
    
    with socketserver.TCPServer((HOST, PROXY_PORT), LoLAPIProxyHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n🛑 Arrêt proxy...")


if __name__ == '__main__':
    main()
