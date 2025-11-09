#!/usr/bin/env python3
"""
Test de connexion à l'API LoL depuis WSL
Différentes approches pour contourner le problème 127.0.0.1
"""

import socket
import subprocess
import requests
import base64
from pathlib import Path
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


def get_windows_ip():
    """Récupérer l'IP de Windows depuis WSL"""
    try:
        # Méthode 1: Via route default
        result = subprocess.run(
            ['bash', '-c', 'ip route show | grep -i default | awk \'{print $3}\''],
            capture_output=True,
            text=True
        )
        ip = result.stdout.strip()
        if ip:
            return ip
    except:
        pass
    
    # Méthode 2: Via /etc/resolv.conf
    try:
        with open('/etc/resolv.conf', 'r') as f:
            for line in f:
                if line.startswith('nameserver'):
                    return line.split()[1]
    except:
        pass
    
    return None


def get_lol_credentials():
    """Lire lockfile LoL"""
    lockfile = Path("/mnt/c/Riot Games/League of Legends/lockfile")
    
    if not lockfile.exists():
        return None
    
    content = lockfile.read_text().strip()
    parts = content.split(':')
    
    if len(parts) != 5:
        return None
    
    _, pid, port, password, protocol = parts
    return {
        'port': port,
        'password': password,
        'auth': base64.b64encode(f"riot:{password}".encode()).decode()
    }


def test_connection(host, port, auth):
    """Tester connexion HTTPS"""
    url = f"https://{host}:{port}/help"
    
    print(f"Test: {url}")
    
    try:
        response = requests.get(
            url,
            headers={'Authorization': f'Basic {auth}'},
            verify=False,
            timeout=2
        )
        print(f"  ✅ Status {response.status_code}")
        print(f"  Content-Length: {len(response.content)}")
        return True
    except requests.exceptions.Timeout:
        print(f"  ❌ Timeout")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"  ❌ Connection error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_port_accessible(host, port):
    """Tester si port TCP est accessible"""
    print(f"Test TCP socket: {host}:{port}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        
        if result == 0:
            print(f"  ✅ Port ouvert")
            return True
        else:
            print(f"  ❌ Port fermé (code {result})")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def check_windows_firewall(port):
    """Vérifier règles firewall Windows"""
    print(f"\nVérification firewall Windows pour port {port}...")
    
    try:
        result = subprocess.run(
            ['powershell.exe', '-Command', 
             f'Get-NetFirewallPortFilter | Where-Object {{$_.LocalPort -eq {port}}} | Select-Object -ExpandProperty InstanceID'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.stdout.strip():
            print(f"  ✅ Règle firewall trouvée:\n{result.stdout}")
            return True
        else:
            print(f"  ⚠️  Aucune règle firewall pour port {port}")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_netsh_portproxy():
    """Vérifier si portproxy est configuré"""
    print("\nVérification netsh portproxy...")
    
    try:
        result = subprocess.run(
            ['netsh.exe', 'interface', 'portproxy', 'show', 'all'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        print(f"Portproxy actif:\n{result.stdout}")
        return result.stdout
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


def setup_portproxy(lol_port, wsl_port=None):
    """
    Configurer portproxy Windows pour rediriger WSL → Windows
    
    ATTENTION: Nécessite privilèges admin Windows !
    """
    if wsl_port is None:
        wsl_port = lol_port
    
    windows_ip = get_windows_ip()
    
    print(f"\n{'='*80}")
    print(f"SETUP PORTPROXY (nécessite admin Windows)")
    print(f"{'='*80}")
    print(f"\nCommande à exécuter dans PowerShell ADMIN Windows:\n")
    print(f"netsh interface portproxy add v4tov4 listenaddress={windows_ip} listenport={wsl_port} connectaddress=127.0.0.1 connectport={lol_port}")
    print(f"\nPuis autoriser firewall:")
    print(f"New-NetFirewallRule -DisplayName 'WSL LoL API' -Direction Inbound -LocalPort {wsl_port} -Protocol TCP -Action Allow")
    print(f"\n{'='*80}\n")


def main():
    print(f"\n{'='*80}")
    print("🔍 DIAGNOSTIC CONNEXION WSL → LoL API")
    print(f"{'='*80}\n")
    
    # 1. Récupérer credentials LoL
    print("1️⃣  Lecture lockfile LoL...")
    creds = get_lol_credentials()
    
    if not creds:
        print("  ❌ Lockfile non trouvé ou invalide")
        return
    
    print(f"  ✅ Port: {creds['port']}")
    print(f"  ✅ Auth: {creds['auth'][:20]}...\n")
    
    # 2. Récupérer IP Windows
    print("2️⃣  Détection IP Windows...")
    windows_ip = get_windows_ip()
    
    if not windows_ip:
        print("  ❌ IP Windows non trouvée")
        return
    
    print(f"  ✅ IP Windows: {windows_ip}\n")
    
    # 3. Test TCP socket
    print("3️⃣  Test accessibilité port TCP...\n")
    
    hosts_to_test = [
        ('127.0.0.1', 'localhost WSL'),
        (windows_ip, 'IP Windows'),
        ('localhost', 'localhost alias'),
    ]
    
    accessible = []
    for host, desc in hosts_to_test:
        print(f"  {desc} ({host}):")
        if test_port_accessible(host, creds['port']):
            accessible.append(host)
        print()
    
    # 4. Test HTTPS API
    print("4️⃣  Test API HTTPS...\n")
    
    api_working = []
    for host in accessible:
        if test_connection(host, creds['port'], creds['auth']):
            api_working.append(host)
        print()
    
    # 5. Diagnostic
    print(f"\n{'='*80}")
    print("📊 RÉSUMÉ")
    print(f"{'='*80}\n")
    
    if api_working:
        print(f"✅ API accessible via: {api_working}")
        print(f"\n💡 Utiliser dans capture_replay_api.py:")
        print(f"   self.base_url = f'https://{api_working[0]}:{creds['port']}'")
    else:
        print("❌ API non accessible depuis WSL\n")
        print("📋 SOLUTIONS POSSIBLES:\n")
        
        print("Solution 1: Port Proxy Windows (recommandé)")
        print("-" * 80)
        setup_portproxy(creds['port'])
        
        print("\nSolution 2: SSH Tunnel")
        print("-" * 80)
        print(f"ssh -L {creds['port']}:127.0.0.1:{creds['port']} localhost")
        print("(Nécessite SSH server Windows)\n")
        
        print("Solution 3: Script Python côté Windows")
        print("-" * 80)
        print("Créer un proxy Python qui tourne sur Windows")
        print("et expose l'API sur toutes les interfaces\n")
        
        print("Solution 4: socat")
        print("-" * 80)
        print(f"Installer socat sur Windows et rediriger le port\n")
    
    # 6. Tests supplémentaires
    print(f"\n{'='*80}")
    print("🔧 DIAGNOSTICS COMPLÉMENTAIRES")
    print(f"{'='*80}\n")
    
    test_netsh_portproxy()
    check_windows_firewall(creds['port'])


if __name__ == '__main__':
    main()
