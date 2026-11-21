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

## 2026-11-21 · 2. fázis — Tervezés, működés és dizájn ✅

- `docs/fazis-2-terveles.md` elkészült (14 fejezet). **Megjegyzés:** a repóba közben feltöltött párhuzamos 2. fázis-váz (commit `947f060`) beolvadt — a legjobb elemek egyesítve, az ütköző számokat egyetlen, `scripts/pio_f2_calc.py`-val ellenőrzött elrendezés váltotta fel.
- Végleges döntések (részletesen a dokumentumban):
  - **MUNKATERÜLET (768 B):** rajzvászon 352 + token-puffer 128 + reasoning verem 32 + **BASIC-puffer 256** — a vászon és a BASIC-puffer egyszerre él (D-2.1); a bemenet külön bufferét elhagytuk (a ROM INPUT a képernyősorra olvas);
  - **SYSVARS-farok:** tervezett mezők (MODE, TEMP, REASON, CHAT_HEAD, CHAT_VIEW, TOK_IN/OUT, TICKS, CLOCK_H/M, FRAME_ANCHOR) — a pontos kezdőcím a 3. fázisban a ROM-listából;
  - **SZÓTÁR (2304 B):** 1144 B tokenrekord + 16 B betűtábla + 1000 B trigram súlytömb (250 rekord × 4 B) + 144 B tartalék;
  - **őszinte korrekció** (D-3.1): 1 bájtos token-ID → max 256 ID → a végleges szótár 224 tartalmi token (180 szó + 28 toldalék + 16 betű); a fázis-1-es „400–460 token" becslés javítva;
  - **PERSIST_BLOCK (256 B):** mágia „P","C", verzió, FLAGS (korosztály a születési évből), név (12), születés, munkamenet dátum+óra, **STATE[8] + STATE_DAY[8]** (64 darab 1 bites tény, napi elavulás 7 napos küszöbbel), **REMIND[4] × 6 B**, vitakövető (16 B), tartalék, **CRC-16** + **XOR 0xA5 maszk + „76-kerülő"**;
  - **ZX81 karaktertábla forrás-hitelesítve** (0x00–0x3F + 0x80–0xBF engedélyezett; 0x40–0x75 keyword-tokenek, 0x76 NEWLINE, 0x77+, 0xC0+ tiltott) + **D_FILE elrendezés: 24 × 33 = 792 B a 0x4200-on, 232 B 0x76-mentes scratch** + **print-tölcsér** (egyetlen kiírási kapu, tiltott bájt → szóköz) + boot scrub és SHIFT+K önteszt;
  - **.T81 blokkformátum:** elnevezett blokkok (`PIOCOBOOT`, `PIOCOMOT`, `PIOCOSZO`, `PIOCOALAP`, `PIOCOPACK`, `PACK####`, `SAVEnnnn`), 4 bájtos belső fejléc (típus/verzió/hossz) + **CRC-16 (0x1021/0xFFFF)** — mert a ROM LOAD checksumot nem ad; mentés mindig **szalagvég-re, `SAVEnnnn`**; impulzusszintű kódolás a 3. fázisra;
  - **6 képernyőterv sor-szintű vázlatokkal** (K1 splash – pörgő karakterekkel, K2 csevegő – inverz fejlécekkel + ROM INPUT/KSCAN fallback-döntés, K3 gondolkodási sáv, K4 rajz, K5 BASIC, K6 emlékeztető-riasztás); plot-terület 64×44 = felső 22 sor (forrás-hitelesítve);
  - **vezérlők véglegesítve:** a mesterprompt 5 kötelező + 5 új mód-billentyű (SHIFT+D/B/M/K/T), saját nyers billentyű-szkenneléssel;
  - **Agent-parancsnyelv: 14 parancs** (SAY, ASK, SETBIT, REMIND, DRAW, DRAWCLR, BASIC, BASICEDIT, MOOD, STANCE, LOADPACK, SAVE, WAKE, STOP) a **nem printelhető 0x10–0x1F token-tartományban** + példafolyamok;
  - **rajz alrendszer:** vászon-zónák (ég/táj/előtér) + fix alakzat-területek (ház x16–47/y16–40, ablak x22–30/y22–30, fa x50–60/y18–40), **csak-hozzáadó (OR) mód, törlés csak DRAWCLR**;
  - **BASIC alrendszer:** sorszám-csere/beszúrás/törlés, ~14–16 soros puffer; futtatás-átlépés nyitott a 3. fázisra;
  - **emlékeztető-modul:** FRAMES 50 Hz, 3 bájtos számláló (1 nap = 4 320 000 frame), **D-12.1: futás csak SLOW-ban** (FAST-ba esés → visszakapcsolás, perc-léptetés szünetel);
  - **generálási lánc futásidőben:** max 4 reasoning lépés, 1 Agent-parancs, hőmérséklet top-k leképezés (1→legnagyobb; 2→top2, R-bit; 3→top4; 4→top8, R+FRAMES), válasz max 4 sor + `TOVABB?`;
  - a 3. fázis „nem dönt újra" listája + **első öt futtatható szelet** (BOOT → üres csevegő → tokenizáló+SAY → SETBIT/REMIND/DRAW/BASIC → mentés/visszatöltés).
- Minden bontást `scripts/pio_f2_calc.py` ellenőrzött; a platformtények forrás-hitelesítve (Wikipedia ZX81 character set, Timex Sinclair Video Display System, ZX81 ROM listing, reids4fun PLOT-méret, andrivet memóriatérkép).
- **Következő:** 3. fázis — kódolás és csomagolás (Z80 motor, PC-s eszközök, első futó `.T81`, turbo OFF), a 14.4 szeletei szerint.
