#!/usr/bin/env bash
set -e

PKG_DIR="$(cd "$(dirname "${BASH_SOURCE}")" && pwd)"
cd "$PKG_DIR"

echo "=== 1. Pulizia residui temporanei ==="
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f \( -name "*.pyc" -o -name "*.log" -o -name "*~" -o -name "*.bak" \) -delete 2>/dev/null || true

echo "=== 2. Controllo file vuoti o corrotti ==="
ERRORI=0
while IFS= read -r -d '' file; do
    if [ ! -s "$file" ]; then
        echo "[ERRORE] File vuoto (0 byte): $file"
        ERRORI=$((ERRORI + 1))
    fi
done < <(find . -type f -print0)

echo "=== 3. Verifica sintassi Python (.py) ==="
while IFS= read -r -d '' pyfile; do
    if python3 -m py_compile "$pyfile" 2>/dev/null; then
        echo "[OK] Python valido: $pyfile"
    else
        echo "[ERRORE] Sintassi corrotta in: $pyfile"
        python3 -m py_compile "$pyfile" || true
        ERRORI=$((ERRORI + 1))
    fi
done < <(find . -type f -name "*.py" -print0)
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

echo "=== 4. Verifica sintassi Bash (.sh) ==="
while IFS= read -r -d '' shfile; do
    # Converte eventuali fine riga Windows CRLF in LF Linux
    sed -i 's/\r$//' "$shfile"
    if bash -n "$shfile" 2>/dev/null; then
        echo "[OK] Bash valido:   $shfile"
    else
        echo "[ERRORE] Sintassi corrotta in: $shfile"
        bash -n "$shfile" || true
        ERRORI=$((ERRORI + 1))
    fi
done < <(find . -type f -name "*.sh" -print0)

if [ "$ERRORI" -gt 0 ]; then
    echo "============================================================"
    echo "[!] Rilevati $ERRORI errori. Correggi prima di impacchettare."
    exit 1
fi

echo "=== 5. Impostazione permessi standard Linux ==="
find . -type d -exec chmod 755 {} +
find . -type f -exec chmod 644 {} +
find . -type f \( -name "*.sh" -o -name "*.desktop" -o -name "OpenSimWheel_Linux_Bridge.py" \) -exec chmod 755 {} +
echo "[OK] Permessi impostati (755 eseguibili/cartelle, 644 risorse/moduli)."

echo "=== 6. Generazione checksum SHA256 e archivio v1.3.0 ==="
rm -f SHA256SUMS.txt ../OpenSimWheel_Linux_Bridge_v1.3.0.tar.gz
find . -type f ! -name "SHA256SUMS.txt" ! -name "verifica_e_impacchetta.sh" -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS.txt
chmod 644 SHA256SUMS.txt

NOME_CARTELLA="$(basename "$PKG_DIR")"
cd ..
tar --exclude="$NOME_CARTELLA/verifica_e_impacchetta.sh" -czf "OpenSimWheel_Linux_Bridge_v1.3.0.tar.gz" "$NOME_CARTELLA"

echo "============================================================"
echo "[SUCCESSO] Release verificata e impacchettata in:"
echo "$(pwd)/OpenSimWheel_Linux_Bridge_v1.3.0.tar.gz"
