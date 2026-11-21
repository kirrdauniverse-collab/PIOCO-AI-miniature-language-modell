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

## 2026-11-21 · Mesterprompt-kiegészítés beépítve (1. fázis v1.1) ✅

- `MASTERPROMPT.md` új 5. fejezete rögzíti a projektgazda kiegészítését (fogalmak, tömörítés, D_FILE-buktatók, viselkedési példák) — hű, szöveghű változatban.
- `docs/fazis-1-koncepcio.md` frissült (v1.1):
  - új **2.1 Fogalomtár** (motor vs. tudástár; token; paraméter/súly; temperature; reasoning),
  - **4 bites kvantálás (`-8..+7`, bájtonként 2 súly)** beépül a generálásba és a PC-s tréning eszközbe,
  - temperature = Z80 **R regiszter + FRAMES (50 Hz)** entropiaforrás,
  - reasoning a **`[THINK_START]` / `[THINK_END]`** jelöléssel, hangulat-felismeréssel (ingerlés/humor/vita),
  - **PERSIST_BLOCK** (védett tartós blokk) és **BOOT** (indító sáv) elnevezés, overlay-k,
  - új **7. fejezet — viselkedési képességek**: humor/ingerlés/vitakövetés, **rajzolás 64×44-en hozzáadó módban** (352 B vászon a MUNKATERÜLET-ben), **BASIC-írás és utólagos módosítás**, **időzített emlékeztető** FRAMES-sel,
  - **pörgő karakterek** effekt biztonságos tartományra szűrve,
  - memóriatérkép-zónák leírása frissült (a bájtösszegek és a 16 384 B-es folytonos lefedés **változatlan**, újraszámolva),
  - fázisterv (2. fázis bővült: rajzvászon/BASIC-puffer/elhelyezés, emlékeztető-modul) és a kockázati lista **6. ponttal** bővült.
