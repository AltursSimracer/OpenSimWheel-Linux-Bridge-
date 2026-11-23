#!/bin/bash
SRC="$(cd "$(dirname "$0")" && pwd)"
DST="$HOME/.local/share/OpenSimWheel"
mkdir -p "$DST"
rsync -av --exclude='.git' --exclude='logs/' --exclude='*.bak' "$SRC/" "$DST/"
echo "Sincronizzato da $SRC -> $DST"
