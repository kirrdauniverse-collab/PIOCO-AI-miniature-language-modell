# Fejlesztési napló — PIOCO AI

> Minden fázis lezárásakor frissül. A részletes anyagok a `docs/` mappában.

## 2026-11-21 · 1. fázis — Ötlet és koncepció ✅

- GitHub repo: `kirrdauniverse-collab/PIOCO-AI-miniature-language-modell` (nyilvános)
- Mesterprompt rögzítve: `MASTERPROMPT.md`
- `docs/fazis-1-koncepcio.md` elkészült, benne:
  - koncepció egy mondatban + realitásvizsgálat (mi fér be 16 KB-ba, mi nem),
  - a valódi generálás láncának terve (tokenizálás → reasoning → generálás → hőmérséklet → állapotfrissítés),
  - modultérkép és **memóriatérkép-javaslat** (0x4000–0x7FFF, folytonos, pontosan 16 384 bájt, 512 B tartalék — Python-számítással ellenőrizve),
  - a kért memória-arányok vs. a valóság: chat 2–3 → 1,5 KB, tudás 7–10 → 6 KB rezidens + multiload,
  - `.T81` sávstruktúra (S1 INDÍTÓ / S2 MOTOR+ALAPTUDÁS / S3..N TÉMACSOMAG / M EMLÉKEZET-MENTÉS) + a kazetta-felülírás korlátjának kezelése,
  - 0x76-/karakterbiztonsági és bitmező-szabályok (XOR-maszk, elavulás-kezelés),
  - vezérlők (SHIFT+1..4, SHIFT+9, SHIFT+5/6, SHIFT+S, SHIFT+SPACE), képernyővázlatok,
  - tréning-eszközterv (PC), fázisterv, kockázati lista.
- Döntések: hivatalos név **PIOCO AI**; turbo/fast tape a fejlesztés alatt **kikapcsolva**; emlékezet-mentés szalagvég-re hozzáfűzéssel, dátumbélyeggel.
- **Következő:** 2. fázis — tervezés és dizájn (végleges memóriatérkép, bitmezők, karaktertábla, sávformátum, képernyők, Agent-parancsok).
