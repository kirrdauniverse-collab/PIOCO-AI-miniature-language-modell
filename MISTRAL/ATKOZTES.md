# ÁTKÖZTES — új repó: micro-ai-models-for-retro-computers

A MISTRAL-fejlesztés új otthona a **`kirrdauniverse-collab/micro-ai-models-for-retro-computers`** repó.
Rend: modell-felül, gép-alul → `mistral/zx-81/` (28 gép-almappa minden modellnél, javított nevekkel:
macintosh, playstation, commodore-64, nintendo-nes, colecovision stb. — l. `UJ_REPO_README_TERV.md`).

## Mi maradt itt?
Ez a repó = archívum. Amikor a tartalma biztonságosan ott van az új repóban, ide `TÖRÖLHETŐ.TXT` kerül.

## Új session teendője (egylépéses migráció)
1. `git clone` az új repót; nyiss ágat: `vibe/mistral1-720f86`
2. `MISTRAL/` teljes tartalma → `mistral/zx-81/` (96 fájl)
3. váz-generátor: `python3 eszkozok/uj_repo_vaz_generator.py` → 17 modell × 28 gép README-keret + fő README
4. vizsgálandó v0.1: e repó `vibe/glm-munkakonyvtar-e224bc` ágából: `GLM/zx81/16k/GLM_v065_RT16_TOPICS.t81` → `mistral/zx-81/vizsgalando/MISTRAL_v001.t81` (259 813 B, sha256: 16187115…)
5. PR → merge → ide: `TÖRÖLHETŐ.TXT`
