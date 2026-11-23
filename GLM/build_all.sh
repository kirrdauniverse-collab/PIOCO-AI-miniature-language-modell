#!/bin/sh
# ZX81 AI micro language modell - GLM: teljes, itt futtathato build + ellenorzes.
set -e
cd "$(dirname "$0")"

echo "== 1/5 Z80 asm-motor (PIOCO vonal) assemble =="
python3 eszkozok/epites.py

echo "== 2/5 Multiload sáv + adatblokkok (PIOCO vonal) =="
python3 eszkozok/csomaggen.py

echo "== 3/5 Rezidens .P (PIOCO vonal) =="
python3 eszkozok/pgen.py

echo "== 4/5 16K multiload .T81 szalag-ellenőrzés (GLM_v064) =="
python3 tools/t81verify.py zx81/16k/GLM_v064_RT16_TOPICS.t81

echo "== 5/5 RTLOAD01 shell betöltő + v065 kazetta (RAMTOP-előkészítés) =="
python3 tools/rtlbuild.py
python3 tools/t81verify.py zx81/16k/GLM_v065_RT16_TOPICS.t81

echo "OK: minden lépés hibátlanul lefutott."
