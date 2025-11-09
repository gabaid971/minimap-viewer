#!/bin/bash
# Configurer Windows Port Proxy pour rediriger WSL → LoL API
# NÉCESSITE: Exécution PowerShell en ADMIN

echo "========================================================================"
echo "🔧 CONFIGURATION PORT PROXY WINDOWS"
echo "========================================================================"
echo
echo "⚠️  ATTENTION: Nécessite privilèges administrateur Windows"
echo

# Récupérer infos LoL
LOCKFILE="/mnt/c/Riot Games/League of Legends/lockfile"

if [ ! -f "$LOCKFILE" ]; then
    echo "❌ Lockfile LoL non trouvé"
    echo "   Le client LoL est-il lancé ?"
    echo "   Chemin: $LOCKFILE"
    exit 1
fi

LOL_PORT=$(cat "$LOCKFILE" | cut -d: -f3)
WSL_IP=$(hostname -I | awk '{print $1}')
WINDOWS_IP=$(ip route show | grep default | awk '{print $3}')

echo "📊 Configuration détectée:"
echo "   LoL API Port: $LOL_PORT"
echo "   Windows IP: $WINDOWS_IP"
echo "   WSL IP: $WSL_IP"
echo

# Générer commandes PowerShell
PORTPROXY_CMD="netsh interface portproxy add v4tov4 listenaddress=$WINDOWS_IP listenport=$LOL_PORT connectaddress=127.0.0.1 connectport=$LOL_PORT"
FIREWALL_CMD="New-NetFirewallRule -DisplayName 'WSL LoL API Proxy' -Direction Inbound -LocalPort $LOL_PORT -Protocol TCP -Action Allow"

echo "========================================================================"
echo "📋 COMMANDES À EXÉCUTER (PowerShell ADMIN Windows)"
echo "========================================================================"
echo
echo "# 1. Configurer port proxy"
echo "$PORTPROXY_CMD"
echo
echo "# 2. Autoriser firewall"
echo "$FIREWALL_CMD"
echo
echo "# 3. Vérifier configuration"
echo "netsh interface portproxy show all"
echo
echo "========================================================================"
echo

read -p "🤖 Voulez-vous que je tente de configurer automatiquement ? (y/N) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Tentative configuration automatique..."
    echo
    
    # Essayer avec powershell.exe (peut échouer si pas admin)
    echo "Exécution: $PORTPROXY_CMD"
    
    if powershell.exe -Command "Start-Process powershell -Verb RunAs -ArgumentList '-Command $PORTPROXY_CMD'" 2>/dev/null; then
        echo "✅ Portproxy configuré"
        
        echo "Exécution: $FIREWALL_CMD"
        powershell.exe -Command "Start-Process powershell -Verb RunAs -ArgumentList '-Command $FIREWALL_CMD'" 2>/dev/null
        echo "✅ Firewall configuré"
        
        echo
        echo "⏳ Attente 2s..."
        sleep 2
        
        # Vérifier
        echo
        echo "🔍 Vérification configuration..."
        powershell.exe -Command "netsh interface portproxy show all"
        
    else
        echo "❌ Échec - privilèges admin requis"
        echo
        echo "💡 Ouvrir PowerShell en ADMIN et copier-coller les commandes ci-dessus"
    fi
else
    echo "💡 Ouvrir PowerShell en tant qu'administrateur Windows et copier-coller les commandes ci-dessus"
fi

echo
echo "========================================================================"
echo "🧪 TEST CONNEXION"
echo "========================================================================"
echo

TEST_URL="https://$WINDOWS_IP:$LOL_PORT/help"
echo "Test: $TEST_URL"
echo

# Récupérer password depuis lockfile
LOL_PASSWORD=$(cat "$LOCKFILE" | cut -d: -f4)

if curl -k -u "riot:$LOL_PASSWORD" -s -m 2 "$TEST_URL" > /dev/null 2>&1; then
    echo "✅ API accessible depuis WSL !"
    echo
    echo "💡 Utiliser dans capture_replay_api.py:"
    echo "   self.base_url = f'https://$WINDOWS_IP:{LOL_PORT}'"
else
    echo "❌ API non accessible"
    echo
    echo "💡 Solutions:"
    echo "   1. Vérifier que commandes PowerShell ont été exécutées"
    echo "   2. Vérifier firewall Windows"
    echo "   3. Redémarrer WSL: wsl --shutdown"
fi

echo
echo "🛑 Pour supprimer port proxy:"
echo "   netsh interface portproxy delete v4tov4 listenaddress=$WINDOWS_IP listenport=$LOL_PORT"
echo
