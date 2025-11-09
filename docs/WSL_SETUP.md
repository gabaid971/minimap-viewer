# 🌉 WSL → Windows LoL API - Guide de Configuration

## 🔍 Problème Identifié

L'API League of Legends écoute sur `127.0.0.1` (localhost Windows uniquement).  
Depuis WSL, `127.0.0.1` = localhost WSL, **pas Windows** → connexion impossible.

## ✅ Solutions Testées

### Solution 1: Port Proxy Windows (Recommandé)

**Avantages:**
- Native Windows, pas besoin d'installer quoi que ce soit
- Performance maximale
- Configuration persistante

**Inconvénients:**
- Nécessite privilèges administrateur Windows
- Configuration manuelle requise

#### 📋 Étapes

1. **Ouvrir PowerShell en ADMINISTRATEUR** (Windows)
   - Clic droit sur menu Démarrer → "Terminal (Admin)" ou "PowerShell (Admin)"

2. **Exécuter depuis WSL pour obtenir les commandes:**
   ```bash
   ./scripts/setup_portproxy.sh
   ```

3. **Copier-coller les commandes dans PowerShell ADMIN:**
   ```powershell
   # Configurer port proxy
   netsh interface portproxy add v4tov4 listenaddress=<IP_WINDOWS> listenport=<PORT_LOL> connectaddress=127.0.0.1 connectport=<PORT_LOL>
   
   # Autoriser firewall
   New-NetFirewallRule -DisplayName 'WSL LoL API Proxy' -Direction Inbound -LocalPort <PORT_LOL> -Protocol TCP -Action Allow
   
   # Vérifier
   netsh interface portproxy show all
   ```

4. **Tester depuis WSL:**
   ```bash
   WINDOWS_IP=$(ip route show | grep default | awk '{print $3}')
   LOL_PORT=$(cat "/mnt/c/Riot Games/League of Legends/lockfile" | cut -d: -f3)
   PASSWORD=$(cat "/mnt/c/Riot Games/League of Legends/lockfile" | cut -d: -f4)
   
   curl -k -u "riot:$PASSWORD" "https://$WINDOWS_IP:$LOL_PORT/help"
   ```

### Solution 2: Proxy Python Windows

**Avantages:**
- Plus simple si vous avez déjà Python Windows
- Pas besoin d'admin
- Flexible

**Inconvénients:**
- Nécessite Python installé côté Windows
- Un processus supplémentaire qui tourne

#### 📋 Étapes

1. **Installer Python Windows** (si pas déjà fait)
   - https://www.python.org/downloads/
   - OU Microsoft Store → Python 3.12

2. **Installer requests depuis PowerShell Windows:**
   ```powershell
   python -m pip install requests urllib3
   ```

3. **Lancer proxy depuis WSL:**
   ```bash
   # Convertir chemin et lancer
   PROXY_PATH=$(wslpath -w "/home/gabaid/workspace/minimap-viewer/scripts/lol_api_proxy.py")
   cmd.exe /c "start python \"$PROXY_PATH\""
   ```

4. **Tester:**
   ```bash
   WINDOWS_IP=$(ip route show | grep default | awk '{print $3}')
   curl "http://$WINDOWS_IP:8765/help"
   ```

### Solution 3: SSH Tunnel

**Avantages:**
- Sécurisé
- Standard

**Inconvénients:**
- Nécessite OpenSSH Server Windows
- Plus complexe

```bash
# Installer OpenSSH Server Windows puis:
ssh -L 54858:127.0.0.1:54858 <USER>@localhost
```

## 🔧 Scripts de Diagnostic

```bash
# Diagnostic complet
python scripts/diagnose_wsl_connection.py

# Configuration portproxy guidée
./scripts/setup_portproxy.sh
```

## 📝 Modification du Code

Une fois le port proxy configuré, modifier `capture_replay_api.py`:

```python
def connect(self) -> bool:
    # ... existing code ...
    
    # CHANGEMENT: Utiliser IP Windows au lieu de 127.0.0.1
    import subprocess
    windows_ip_result = subprocess.run(
        ['bash', '-c', 'ip route show | grep default | awk \'{print $3}\''],
        capture_output=True, text=True
    )
    windows_ip = windows_ip_result.stdout.strip()
    
    self.base_url = f"https://{windows_ip}:{port}"  # Au lieu de 127.0.0.1
```

## 🧹 Nettoyage

```powershell
# PowerShell ADMIN - Supprimer port proxy
netsh interface portproxy delete v4tov4 listenaddress=<IP_WINDOWS> listenport=<PORT>

# Supprimer règle firewall
Remove-NetFirewallRule -DisplayName 'WSL LoL API Proxy'

# Lister tous les port proxy
netsh interface portproxy show all
```

## 🐛 Troubleshooting

### "Connection refused"
- Vérifier que LoL est lancé
- Vérifier lockfile existe: `ls "/mnt/c/Riot Games/League of Legends/lockfile"`
- Vérifier port proxy: `powershell.exe -Command "netsh interface portproxy show all"`

### "Timeout"
- Vérifier firewall Windows
- Tester sans firewall temporairement
- Vérifier IP Windows: `ip route show | grep default | awk '{print $3}'`

### "Certificate error"
- Normal, utiliser `-k` avec curl ou `verify=False` avec requests
- L'API LoL utilise certificat self-signed

## 📊 Résumé Connexions

```
┌──────────────┐              ┌──────────────┐              ┌──────────────┐
│     WSL      │              │   Windows    │              │  LoL Client  │
│  (Python)    │──────────────▶│ Port Proxy   │──────────────▶│     API      │
│              │   HTTPS      │  :54858      │   HTTPS      │  127.0.0.1   │
│ 172.26.x.x   │ 172.26.112.1 │              │              │  :54858      │
└──────────────┘              └──────────────┘              └──────────────┘
```
