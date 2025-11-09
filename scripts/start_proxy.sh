#!/bin/bash
# Lancer le proxy Python côté Windows depuis WSL

echo "=================================="
echo "🚀 Lancement proxy LoL API"
echo "=================================="
echo

# Convertir chemin WSL → Windows
SCRIPT_PATH="/home/gabaid/workspace/minimap-viewer/scripts/lol_api_proxy.py"
WINDOWS_PATH=$(wslpath -w "$SCRIPT_PATH")

echo "Script: $WINDOWS_PATH"
echo

# Vérifier si Python3 existe côté Windows
if ! cmd.exe /c "python3 --version" 2>/dev/null | grep -q "Python"; then
    echo "⚠️  Python3 non trouvé côté Windows"
    echo "   Essai avec 'python'..."
    
    if ! cmd.exe /c "python --version" 2>/dev/null | grep -q "Python"; then
        echo "❌ Python non trouvé côté Windows"
        echo
        echo "💡 Installer Python Windows:"
        echo "   https://www.python.org/downloads/"
        echo "   OU depuis Microsoft Store"
        exit 1
    fi
    
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

echo "✅ Python Windows trouvé: $PYTHON_CMD"
echo

# Lancer proxy en background Windows
echo "🎧 Lancement proxy..."
echo "   (Le proxy va tourner en background Windows)"
echo

# Utiliser cmd.exe pour lancer Python Windows
cmd.exe /c "start /B $PYTHON_CMD \"$WINDOWS_PATH\""

# Attendre que proxy démarre
echo "⏳ Attente démarrage (3s)..."
sleep 3

# Tester connexion
WINDOWS_IP=$(ip route show | grep default | awk '{print $3}')
PROXY_URL="http://$WINDOWS_IP:8765/help"

echo
echo "🔍 Test connexion..."
echo "   URL: $PROXY_URL"
echo

if curl -s -m 2 "$PROXY_URL" > /dev/null 2>&1; then
    echo "✅ Proxy actif !"
    echo
    echo "💡 Utiliser dans vos scripts Python WSL:"
    echo "   base_url = 'http://$WINDOWS_IP:8765'"
    echo
else
    echo "⚠️  Proxy pas encore actif (peut prendre quelques secondes)"
    echo
    echo "💡 Vérifier manuellement:"
    echo "   curl $PROXY_URL"
    echo
    echo "💡 Voir processus Windows:"
    echo "   tasklist.exe | grep python"
fi

echo
echo "🛑 Pour arrêter le proxy:"
echo "   taskkill.exe /F /IM python.exe"
echo
