#!/bin/sh
# ZX81 AI micro language modell - GLM: teljes, itt futtathato build + ellenorzes.
set -e
cd "$(dirname "$0")"

echo "== 1/4 Z80 asm-motor (PIOCO vonal) assemble =="
python3 eszkozok/epites.py

echo "== 2/4 Multiload sáv + adatblokkok (PIOCO vonal) =="
python3 eszkozok/csomaggen.py

echo "== 3/4 Rezidens .P (PIOCO vonal) =="
python3 eszkozok/pgen.py

echo "== 4/4 16K multiload .T81 szalag-ellenőrzés (GLM_v064) =="
python3 tools/t81verify.py zx81/16k/GLM_v064_RT16_TOPICS.t81

echo "OK: minden lépés hibátlanul lefutott."
