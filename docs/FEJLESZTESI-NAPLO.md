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

## 2026-11-21 · Nyelvi döntés (D-3.2) + 3. fázis elindítva — 1. szelet 🔵

- **Nyelvi döntés (a projektgazda kérésére, D-3.2):** a prototípus nyelve **angol** — a magyar nagy helyet foglal és bonyolult, az angol egyszerűbb morfológiával több szót enged el a 224 tartalmi tokenbe; a magyar a kiforrott modell utáni finomítási fázisban tér vissza (a 0x20–0x3B toldalék-sáv akkor vált magyar ragrendszerre). A ZX81 csak nagybetűt tartalmaz → minden szöveg nagybetűs ASCII, a motor ASCII→ZX81 táblája fordít printkor; a PERSIST mágia egyszerűsítve ASCII „P”, „C”. Rögzítve: `docs/fazis-2-terveles.md` új 3.4 fejezet.
- **3. fázis, 1. szelet elkészült** (`eszkozok/`, `motor/`, `tudas/`, `kazetta/`):
  - `eszkozok/crc16.py` — CRC-16/CCITT-FALSE, önteszt a szabványos 0x29B1 vektorral;
  - `tudas/alap_korpusz_en.txt` — angol prototípus-korpusz (59 sor: üdvözlet, állapot, rajz, BASIC, emlékeztető, hangulat, vita);
  - `eszkozok/tokengen.py` → `kazetta/adat/szotar.bin` (pontosan 2304 B): 19 funkciószó (0x20+) + 126 tartalmi szó (0x3C+) + 16 betű (0xF0+), rekordterület 723/1144 B, **250/250 trigram**, korpusz-lefedettség 100% (betűesés a maradékra); ember-olvasható lista: `tudas/szotar_en_lista.txt`;
  - `eszkozok/alapmag_gen.py` → `alapmag.bin` (2048 B, 32 slot × 64 B, 32 angol vázsablon hangulat-bitekkel);
  - `eszkozok/z80asm.py` — mini Z80 assembler, **57 kézzel ellenőrzött kódolás + DB/DW/címke önteszt**; két átmenet, méret-mód előre-hivatkozásokhoz, unáris mínusz;
  - `motor/boot.asm` — **1. szakasz** (képernyő-nullázás 792 B, PERSIST init mágia+verzió+nullázás+CRC, blokk-betöltő a ROM **IN-BYTE 0x034C** hívásával, típus→célcím táblával) → `boot.bin` **262 B** a 382-es korlát alatt (120 B ráhagyás);
  - `motor/motor0.asm` — **2. szakasz** (hátralévő blokkok betöltése, splash, főciklus-váz, print-tölcsér + ASCTBL) → `motor0.bin` 155 B (0x4600);
  - `eszkozok/epites.py` — assemble + korlát-ellenőrzés (stage-1 < 0x4200!);
  - `eszkozok/csomaggen.py` → `kazetta/pioco-0.1.tape` (**5 blokk, 4863 B**: PIOCOBOOT 262 → PIOCOMOT 155 → PIOCOSZO 2304 → PIOCOALAP 2048 → PIOCOPACK 64; minden blokk: 4 B fejléc + CRC-16; **visszatöltés-teszt: minden CRC OK**).
- **Hitelesített ROM-anchorgok** (forrás: ZX81 ROM listing / Timex Sinclair / andrivet): IN-BYTE = 0x034C (bájt a C-ben), LOAD = 0x0340, gépi kód belépés = 16514 (0x4082, REM sor), billentyűzet: `IN r,(C)` a B-felső címvonalakkal (A8–A15 sorkiválasztás, port 0xFE).
- **Architektúra-javítás a méretmérésből:** az eredeti egyfokozatú BOOT-kód (520 B) átnőtt volna a 0x4200-as D_FILE-zónába → **két szakaszos indítás** (karcsú betöltő ≤ 382 B + stage-2 a 0x4600-ra töltve), ami egyébként is a fázis-2 blokktervének felel meg (PIOCOBOOT → PIOCOMOT).
- **Nyílt tételek a következő körre** (emulátor-ellenőrzéssel): a szalag **pulse-rétege** (a `.tape` most a saját 6.2 blokkformátum nyers bájtja — a `.p`/`.T81` burkolás és a pilot/sync csak emulátor-igazolással készül el, nem találgatással); ASCTBL tartalma (ROM-karaktertábla); IN-BYTE regiszter-megőrzése; INPUT-döntés (ROM INPUT vs KSCAN).
- **Következő:** 2. szelet — emulátoros futás (EightyOne/z81), INPUT + Agent-kör váza, majd a 14.4 lista szerint tovább.

## 2026-11-21 · 3. fázis, 2. szelet — Z80-szimulációs végpont-teszt: MINDEN ZÖLD ✅ (+ D-3.3)

- **Környezet-megjegyzés:** a fejlesztői sandbox újraindult, a helyi munkakönyvtár elveszett — minden visszatöltve a GitHub-repóból (1fc76b4), a binárisok determinisztikusan regenerálva (CRC-azonosság), a letöltési mappába a fázis-dokumentumok pandoc-visszaállított példányai és a képernyőkép kerültek.
- **ASCTBL nyílt tétel LEZÁRVA** (forrás: Wikipedia „ZX81 character set”): szóköz = 0x00, számjegyek 0x1C–0x25, A–Z = 0x26–0x3F, írásjelek a fentiek szerint; **aposztróf és felkiáltójel nincs a ZX81-készletben** (szóközre képeznek). A `motor0.asm` 59 bejegyzéses táblája forráshű.
- **Új eszközök:** `eszkozok/z80sim.py` — Z80-szimulátor (a z80asm utasításkészlete, CALL-hookok, íráskövetés, önugrás-detektálás; 6 mintaprogramos önteszt); `eszkozok/szimfuttatas.py` — **végpont-teszt**: a valódi `boot.bin` fut 0x4082-től, a `.tape` hátralévő 4 blokkja a ROM IN-BYTE (0x034C) szerepét játszó hookon át érkezik; hat ellenőrzés (leállás-mód, szalag-felhasználás, zóna-hűség, PERSIST+CRC, D_FILE-szerkezet+splash, írás-zónák).
- **Eredmény — minden ellenőrzés zöld:** 507 522 lépés a MWAIT-ig; a szalag pontosan elfogy (4594/4594 B); MOTOR/SZÓTÁR/ALAPMAG/PACK bájt-hűen a helyén; PERSIST-mágia „P”„C” + verzió + nullák + **CRC-16 kereszteszt Z80↔Python OK (0xEC23)** — a motor saját CRC-rutinja hitelesítve; D_FILE 24×(32+0x76) szerkezettel és a splash-szövegekkel a helyükön; 44 704 írás, mind az engedélyezett zónákban. A D_FILE dekódolt képe: `kazetta/kepernyokep_szimulacio.txt`.
- **A végpont-teszt három VALÓDI hibát fogott** (ez volt a célja):
  1. `z80asm.py` feltétel-tábla: az NC/C indexek hibásak voltak → a `JR NC` `LD B,B`-vé kódolta magát (az önteszt csak NZ/Z-t fedte le) — javítva, 9 új önteszt-esettel lezárva (66 kódolás);
  2. **D-3.3 korrekció:** a REM-sori boot-kód (0x4082-től nő) átfedte a PERSIST-zónát (0x4100–0x41FF) — a nullázó ciklus saját magát törölte volna ki. **PERSIST → 0x7F00–0x7FFF**, TARTALÉK 256 B-ra zsugorodott, **0x4082–0x41FF a BOOT-betöltő saját sávja** (464 B); a memóriatérkép a fázis-2 dokumentumban korrigálva;
  3. `boot.asm` PZL nullázó ciklus: a számláló-teszt (`LD A,B / OR C`) felülírta az írandó nullát → csökkenő számlálóértékek íródtak a zónába; javítva azonnali operandumú `LD (HL),0`-val.
- **Továbbra is nyitott** (a 3. szelethez): billentyűmátrix (a D0–D4↔gomb táblázat forrása elérhetetlen volt — robotvédelem; ROM-listás KSCAN-ellenőrzéssel zárjuk), a szalag pulse-rétege/.p-burkolás (valódi emulátorban), IN-BYTE regiszter-megőrzés.
- **Következő:** 3. szelet — GETKEY (billentyűzet) + INPUT + Agent-kör váza, szimulátoros billentyű-szkript-teszttel.
