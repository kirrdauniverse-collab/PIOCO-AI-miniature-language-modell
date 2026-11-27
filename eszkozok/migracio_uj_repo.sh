#!/usr/bin/env bash
# Migráció a micro-ai-models-for-retro-computers repóba.
# Ahol futtatni kell: az ÚJ repó Codespace-ében (vagy klónjában), a repo gyökerében.
set -e
RAW="https://raw.githubusercontent.com/kirrdauniverse-collab/PIOCO-AI-miniature-language-modell/refs/heads/vibe/pico-ai-mistral-720f86"
echo "== 1/4 vázgenerátor (17 modell x 28 gép) =="
curl -sL "$RAW/eszkozok/uj_repo_vaz_generator.py" -o /tmp/gen.py
python3 /tmp/gen.py
echo "== 2/4 MISTRAL anyag átmasolása (mistral/zx-81) =="
git clone --depth 1 -b vibe/pico-ai-mistral-720f86 https://github.com/kirrdauniverse-collab/PIOCO-AI-miniature-language-modell.git /tmp/pico
mkdir -p mistral/zx-81
cp -r /tmp/pico/MISTRAL/. mistral/zx-81/
echo "== 3/4 fő README =="
cp mistral/zx-81/UJ_REPO_README_TERV.md README.md
echo "== 4/4 commit + push =="
git add -A
git commit -m "MISTRAL migracio: mistral/zx-81 teljes anyag + 17x28 vaz + fo README" || echo "(semmi uj)"
git push -u origin HEAD
echo "== KÉSZ: frissítsd a repó oldalát! =="
