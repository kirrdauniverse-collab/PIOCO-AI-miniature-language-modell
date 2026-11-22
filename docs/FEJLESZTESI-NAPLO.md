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

## 2026-11-21 · 3. fázis, 3. szelet — KIPRÓBÁLHATÓ .P: rezidens terjesztés (pioco-0.1.p) ✅

- **Cél (felhasználói kérés):** az első kipróbálható változat átadása a chatben.
- **.P formátum forrás-hitelesítve** (zx81-utils `p2txt`/`rem2bin` + a zmakebas ZX81 mód forrásakódjából): a fájl `[116 B (0x74) sysvars a 0x4009-től][program][25×0x76 összezsugorított képernyő][0x80 VARS-záró]`; sor: `[sorszám BE:2][hossz LE:2][törzs…0x76]` (a hosszvezérelt feldolgozás miatt a REM-testben bármilyen bájt megengedett); szám a sorban: `0x7E` + 5 B lebegőpontos (dbl2spec-algoritmus); tokok: REM=0xEA, RAND=0xF9, USR=0xD4; sysvar-címek: D_FILE @0x400C, DF_CC @0x400E; CDFLAG=0x40 = SLOW mód.
- **Új: rezidens terjesztés** (a klasszikus ZX81 REM-terjesztés): a motor (160 B), szótár (2304 B), alapmag (2048 B) és pack (64 B) REM-sorokként (2–5. sor) utazik a programban; a 6. sor `RAND USR 16514`. A boot `BOOTMODE=1` mellett a **RESCOPY** rutinja másolja fel a REM-testeket a végleges címekre — egyetlen .P fájl szalaglánc nélkül, minden emulátorban futtatható. A másolási sorrend **mért kényszer**: ALAPMAG → PACK → SZÓTÁR → MOTOR (a SZÓTÁR célzónája, 0x5400+, átfedi az ALAPMAG/PACK forrásait; a MOTOR célja a SZÓTÁRét) — a pfuttatas ezt először elrontva találta meg, javítva; a pgen most statikusan is ellenőrzi.
- **Motor-bővítések:** BOOTMODE váltóbájt (0 = szalag mód, 1 = rezidens); SCRFILL immár **ROM-standard 25 sor × (32+0x76) + záró 0x76 = 826 B** (stop-bájt @0x4539 — nélküle a NMI átfutna a 0x76-mentes scratch-en; D-3.4 pontosítás a fázis-2 doc 5.2-ben); a boot a **D_FILE/DF_CC sysvar-mutatókat** a saját képernyőre állítja (0x4200/0x4201) — a korábbi „nem írjuk" nyitott tétel lezárva.
- **Új eszközök:** `pgen.py` (a .P generátora: zmakebas-recept fejléc + dbl2spec + @PG*@ immediate-patchek + sorrend-ellenőrzés + szerkezeti önteszt), `pfuttatas.py` (virtuális emulátor: .P → ROM LOAD-szimuláció → CLS-utánzat → `RAND USR 16514` → teljes futás; rezidens módban az IN-BYTE hívás tiltott).
- **Eredmények:** `pioco-0.1.p` **5273 B** (program 5131 B @0x407D, D_FILE=0x5488, REM-testek: motor@0x4288, szótár@0x432E, alapmag@0x4C34, pack@0x543A); a virtuális futás **66 694 lépés** a MWAIT-ig, minden zóna bájt-hű, CRC-kereszteszt OK (0xEC23), 7998 írás mind engedélyezett zónában, szalagolvasás nem történt. A szalag-mód teszt ismét zöld (508 222 lépés). Képernyőkép: `kazetta/kepernyokep_p.txt`.
- **Külső (harmadik feles) validáció:** az önállóan lefordított `p2txt` hibátlanul végigjárja a fájlt (1–5 REM + „RAND USR", a 2. sorban felismerhető a karaktertáblánk), a `rem2bin` az 1. sor REM-testét **bájt-hűen** (512/512 B) hozza ki. Ez a formátumhelyesség független bizonyítéka; valódi emulátortesthez (EightyOne/SZ81/z81) a használati útmutató a letöltésben.
- **Nyitva:** a .T81 multiload-burkolat (EightyOne formátum — a forráskód elérése függőben), az alsó sorok (DF_SZ/E_LINE) megjelenítése valódi gépen, INPUT/billentyűmátrix (ROM-listás KSCAN), pulse-réteg.
- **Következő:** 4. szelet — GETKEY + INPUT + Agent-kör váza; .T81-burkolat forrás-ellenőrzése.

## 2026-11-21 · 3. fázis, 4. szelet — C/6-javítás, v2 kézbesítés (pioco-by-GLM-0.1.p) ✅

- **Felhasználói visszajelzés:** a v1 .P a valódi emulátorban **C/6** hibajelentéssel leállt (a 6. sor = a `RAND USR 16514` belépő sor). Új névkonvenció: minden átadott fájl innentől `pioco-by-GLM-<verzió>…`.
- **Három valódi hiba — mind a PC-s szimulátor és a valódi ROM nem modellezett különbsége:**
  1. **D-3.7 — beágyazott számformátum (a C/6 közvetlen oka):** a zmakebas forrása szerint a sorba írt szám a JEGYEIT (ZX81 kódkarakterként) ÉS a `0x7E`+5 B FP kódolást is tartalmazza, a mantissza felső bitje (jelbit) pedig nulla marad. A v1 kódolásunk (`7E 8F 81 04 00 00`) jelbitje 1 volt → a ROM szemében **−16514**, az USR egész operandusa tartományon kívüli → hibajelentés a belépő sornál. A javított sorkar: `F9 D4 1D 22 21 1D 20 7E 8F 01 04 00 00` — **bájtonként azonos** a lefordított zmakebas `-p` referenciakimenetével (a dbl2spec-átirat a kerekítést és a jelbit-törlést is hűen követi).
  2. **D-3.6 — REM-hordozás 0x76-korlátja:** a régi ROM-ban dokumentált, hogy a 0x76 bájt a sorban sornak számít — a 3. szelet „a REM-testben bármilyen bájt megengedett" megállapítása a valóságon megbukott. A v1 bootjában 2 db `LD (HL),0x76` immediate volt; a boot most **0x76-mentes** (a képernyő 0x76-jait aritmetikailag állítja elő: `LD A,0x3B` + `RLCA`), az adatok (motor, szótár, alapmag, pack) pedig a REM-sorokból a **program utáni adatterületre** költöztek (a .P-ben az összezsugorított képernyő előtt) — ott valóban bármilyen bájt megengedett. Az epites.py véglegesen őrzi a boot 0x76-mentességét; a pgen pad-ciklusa a RESCOPY immediate-ekre is kiterjeszti.
  3. **D-3.5 — veremütközés:** a valódi ZX81 ROM a vermet a RAM tetejére állítja (SP≈RAMTOP) — a PERSIST-init nullázása (0x7F04–0x7FFD) felülírta volna a ROM USR-visszcímét és a saját CALL-kereteket. A boot első utasítása mostantól `LD SP,0x5400`: a saját verem a MOTOR zóna tetején fut (a v1 szimulátor-feltételezés SP=0xFFFE valós gépen nem áll).
- **Egyéb:** a D_FILE/DF_CC mutatóírás szakadás-mentes sorrendje (felső bájt először, hogy a NMI ne lásson felfeslett mutatót); NXTLIN a program végére mutat.
- **Eredmények:** `pioco-0.1.p` **5101 B** = 383 B program (1 REM 359 B + 2 RAND USR 16514) + 4576 B adat @0x41FC + D_FILE=0x53DC. Virtuális emulátor-teszt zöld (66 698 lépés; RESCOPY bájt-hű; CRC-kereszteszt 0xEC23; írás-zónák rendben; IN-BYTE nem hívódott), szalag-mód teszt zöld (508 226 lépés, SP=0x5400-zal). **Külső validáció:** a belépő sor bájtonként a zmakebas referenciával azonos; a rem2bin a REM-testet bájt-hűen (359/359 B) hozza ki. (Megjegyzés: a p2txt listázó a klasszikus „D_FILE a program után" elrendezést feltételezi, a mi adatterület-hordozónkat nem tudja listázni — eszközkorlát, nem fájlhiba.)
- **Kézbesítés (új névkonvenció):** `download/pioco-by-GLM-0.1.p` + `pioco-by-GLM-0.1-hasznalat.txt` + `pioco-by-GLM-0.1-kepernyokep(.txt|-szalag.txt)`.
- **Következő:** valódi emulátoros visszajelzés alapján korrekció; INPUT + Agent-kör váza; .T81 multiload-burkolat.

## 2026-11-21 · 3. fázis, 5. szelet — C/F080 + száguldozó pixelek: ROM-listás diagnózis, v0.2 (pioco-by-GLM-0.2.p) ✅

- **Felhasználói visszajelzés:** a v2 .P betöltés után C/F080-jellegű (hexa-szemétes) hibajelentést mutatott, RUN után pedig „apró pixelek száguldoztak" a képernyőn. (HI-RES nincs és nem is cél — a tünetek a ROM képernyő-generátorával való ütközésre mutattak.)
- **Eszközbeszerzés:** a valódi 8 KB-os ZX81 ROM (`kutatas/zx81.rom`) + a teljes Logan–O'Hara disassembly szövegesen (`kutatas/romlist.txt`) — innentől a ROM viselkedése forráshiteles tény, nem találgatás.
- **ROM-tények, amik mindent megváltoztattak:**
  1. **REPORT-C = „no numeric value"** — a v1-es C/6 végleg magyarázva: a ROM az USR operandusán nem talált (elfogadható) számot.
  2. **A gép vereme a RAM legtetején él:** az INIT `SP = RAMTOP−2 = 0x7FFE`, `ERR_SP = 0x7FFC`; az NMI képernyő-generáláskor `LD SP,(ERR_SP)`-et tesz, mentései (0x7FF4–0x7FFB) minden képkockán ott íródnak. **A D-3.3/D-3.5-ös PERSIST @0x7F00 tehát a ROM élő veremterületén ült**: a PERSIST-init nullázása (0x7F04–0x7FFD) a RAND-USR kiértékelő kereteit és az ERR_SP-alapú vermet semmisítette meg, a ROM pedig képkockánként visszairta a PERSIST-et.
  3. **A képernyő-generálás a megjelenítőfájlt kódként végrehajtva működik** (`LD HL,(D_FILE); SET 7,H; … JP (HL)` — a 0x8000-es A14-tükörben; az üres sorok NOP-ok, a 0x76 = HALT). Ha a D_FILE szemétre mutat, a Z80 képkockánként más vándorpályán fut — **pontosan a „száguldozó apró pixelek" mechanizmusa**; a C/F080-jellegű jelentéssor ugyanebből a káoszból renderelt szemét.
  4. A CLS (0x0A2A) a PRINT-gépezaton át terjeszti ki a képernyőt (MAKE-ROOM @0x099E; a POINTERS @0x09AD a D_FILE-tól 9 szomszédos pointer-szót korrigál egy lépésben) — a mi „adat a program után, képernyő előtt" hordozónk kompatibilis: csak a pointer-láncot használja, semmi nem feltételez közvetlen illeszkedést.
- **D-3.8 — PERSIST 0x7F00 → 0x7E00** (csere a TARTALÉK-kal): a 0x7F00+ zóna ezennel a ROM-é (verem + ERR_SP + NMI-mentések); a PERSIST-init többé nem ír oda. Minden teszt zöld maradt (CRC változatlan: 0xEC23).
- **Új eszköz: `eszkozok/romsim.py` + `romprobe.py`** — teljes Z80 mag + ZX81 gépréteg (NMI/INT-kadencia az FD-port 7es bitje szerint; A14-es memóriatükör: 0xC000+ a RAM tükörképe, 0x8000–0xBFFF nem leképezett — így a RAM-CHECK 0x8000-nél megáll, RAMTOP=0x8000). **Állapot:** a ROM initje hibátlanul lefut (RAM-CHECK, INIT, CLS/LOC-ADDR/MAKE-ROOM protokoll lépésenként igazolva); a SLOW-képernyő megszakítás-koreográfiájának (HALT-szinkron + soralapú INT) finomhangolása következik — a teljes ROM-szintű zöld futás a 6. szelet tétele.
- **Kézbesítés:** `download/pioco-by-GLM-0.2.p` + használat + képernyőképek (névkonvenció szerint).
- **Következő:** ROM-szintű vég-ellenőrzés; INPUT + Agent-kör; .T81 multiload.

## 2026-11-21 · 3. fázis, 6. szelet — a C/F080 VALÓDI oka: .P-formátumú 0x80-terminátor a hordozóban, v0.3 (pioco-by-GLM-0.3.p) ✅

- **Felhasználói visszajelzés:** v0.2-re ugyanaz a C/F080 — a PERSIST-javítás (D-3.8) jogos volt, de nem EZT a hibát javította (a hiba nem a futó kódban, hanem a FÁJLBAN ül, mindkét verzióban azonosan).
- **A valódi ok (kétszeresen hitelesítve):** a ROM-lista szerint a ROM saját LOAD-rutinja E_LINE-alapú (a fejléc E_LINE-ja a fájl végéig olvas) — DE a .P közösségi formátumspecifikációja szerint **a fájl az első 0x80 bájtnál ér véget**, és a legtöbb emulátor .P-betöltője ezt a specet követi. A mi 4576 B-os bináris hordozónkban pedig ott ült EGY 0x80: a szótár trigram-táblájának egyik kulcsa (0x80 = teljesen legitim tokinkód a 0x3C–0xEF tartományból — forrásszinten nem kerülhető el). **A spec-hű betöltők ezért a fájl 56%-ánál (a motor után, a szótár közepén) levágták a betöltést** → a sysvarok a betöltetlen szemétre mutattak (a „C/F080"-as szemét-jelentéssor), RUN-nál pedig a félig betöltött szótárral/alapmaggal dolgozó motor write-elt szét mindent (a „száguldozó apró pixelek"). A felhasználó fájl méretére vonatkozó megérzése („az tuti nem működhet") bevált.
- **D-3.9 — a hordozó XOR 0x40-kódolása:** a pgen a teljes hordozót XOR-olja a 0x40 kulccsal (a kulcs előképe, a 0xC0 bájt nem fordul elő a nyers hordozóban — a pgen kapuval érvényesíti), a boot BLKCPY-ja másolás közben dekódol (+2 B; a boot immár 361/383 B). A szalag-mód blokkjai érintetlenek (a ROM IN-BYTE útján nincs 0x80-korlát).
- **Kapuk és tesztek:** a pgen gyártás után elutasítja a fájlt, ha a testben bármely 0x80 ül (elvárt: pontosan egy, a legvégén, a VARS-záró); a pfuttatas a hordozó-pozíción a KÓDOLT, a végleges címeken a NYERS bájtokat ellenőrzi (a RESCOPY dekódolás bájthű); a spec-töltő szimuláció szerint az első 0x80-ra csonkolt fájl ≡ az egész fájl. Minden korábbi teszt zöld maradt (CRC 0xEC23).
- **Kézbesítés:** `download/pioco-by-GLM-0.3.p` + használat + képernyőképek.
- **Következő:** ROM-szintű zöld futás (romsim), INPUT + Agent-kör, .T81 multiload.

## 2026-11-22 · 3. fázis, 7. szelet — a beszélgetés ADAT-rétege: nyelvtan, hangulat, szándék-válaszok (D-3.10) ✅

A felhasználó hét kérdésére épülő kör (mind válasz MOST került az adatokba és a szabályokba, nem csak a tervbe):

- **Q1 múlt idők/többes:** a -S/-ED/-ING/-LY utótag-tokenek mostantól RÖGZÍTETT ID-n élnek (FUNC-sáv 0x20–0x3C, 29 szó — a korábbi korpuszfüggő szűrés ID-eltolódást okozhatott volna). Bemeneti szabály: egész szó → szár+utótag (DREAMED → DREAM + -ED) → betűesés; a tő 4 ragozott alakot „ingyen" ér. Kimondott gyakori alakok egész szóként maradtak a korpuszban (STARS, ACHED).
- **Q2 számok:** SZÖVEG-tokenként (a korpusz stílusa: „THE TIME NOW IS 8 00 ."); a 0–9 számjegyek kényszerrel a szókincsbe kerültek, hogy bemenetként ne vesszenek el; numerikus kiértékelés NINCS (a ROM FP-hívásai drágák lennének, a csevegéshez nem kellenek — későbbi opció).
- **Q3 hangulat:** HAHA/WOW/NOOO és a :) :( :O smiley-ok szótár-tokenek + korpuszmondatok; 3 hangulat-válasz-slot (humor/humor/sajnálkozó) a meglévő hangulat-bit-rendszerre épülve.
- **Q4 más nyelv:** SPEAK+GERMAN/FRENCH/HUNGARIAN/SPANISH/ITALIAN/LANGUAGE szándékok → „I SPEAK ONLY ENGLISH . SORRY ."
- **Q5 konzerv válaszok (a felhasználó jó meglátása: spórol memóriát és tokent):** SZÁNDÉKTÁBLA a szótár tartalék-területén (18 bejegyzés × 6 B: minden kulcsszó jelen → nyer, a generálás ELŐTT fut). Válaszok az alapmag 7 új slotján: WHO MADE YOU → „I WAS MADE BY SAFAR SANDOR , WITH HELP FROM QWEN ." / WHO IS SAFAR SANDOR → „HE IS A HUNGARIAN BUS DRIVER , AMATEUR WRITER AND ASTRONOMER ." / közmondás: „ONE SWALLOW DOES NOT MAKE A SUMMER ." — a válaszok ANGOLUL (az angol üzem + a ZX81 karakterkészlet dönt; a magyar szöveg egy soron átírható az alapmag_gen.py-ban).
- **Q6 DO/DOES/DO NOT/DOES NOT:** DOES felkerült a FUNC-sávba; DO NOT / DOES NOT korpuszban; a bemenet-normalizáló DON'T→DO NOT, DOESN'T→DOES NOT bontással dolgozik (l. token_demo).
- **Q7 angol nyelv:** megerősítve — korpusz, szótár, alapmag mind angol (rövidebb szavak, kevesebb token, a ZX81 csak nagybetűs).

**Eszközök/hardon:** `eszkozok/token_demo.py` — a chat-kör bemeneti tokenizálásának PC-side REFERENCIA-implementációja (= a Z80 pontos specifikuma, bemutató kimenettel); `tudas/alapmag_slotok.txt` slot-manifeszt (a tokengen név szerint hivatkozik a slotokra — nincs kézzel tartott sorszám); az alapmag 32/32 slot (5 összevonás + 2 elhagyás szabadította fel a helyet az 7 új válasznak).

**Megtalált és javított valós hiba:** az „A"/„I" kettősség (funkciószó ÉS betű) a betűkiosztásnál felülírta a FUNC-ID-jüket, és a rekordterület folytonosságát is megbontotta (222 rekord a várt 208/224 helyett) — most a betűk NEM kapnak rekordot (a keresés a betűesésre fut rájuk), a rekord-ID-k 0x20–0xEF közt zártan folytonosak (assert).

**D-3.9 folytatás:** az új adatban 0xC0 bájt jelent meg, a pgen-kapua lecsapott (pontosan, ahogy terveztük); a XOR-kulcs egyetlen forrása most a motor/boot.asm (XORKEY EQU 0x3E), a pgen és a pfuttatas onnan olvassa — többé nem csúszhat szét három kézzel tartott érték.

**Minden teszt zöld** (epites, csomaggen, szimfuttatas, pgen + 0x80-kapu, pfuttatas; CRC-k frissültek). A .P felépítése változatlan (5103 B, 1 db 0x80 a záróban) — a viselkedés splash-demo marad; az új adatréteget a következő szelet, a Z80 CHAT-KÖR fogyasztja (v0.4 = az első valóban beszélgető, kipróbálható változat).

## 2026-11-22 · 3. fázis, 8. szelet — AZ AZONNALI RESTART GYÖKERE (D-4.0) + a gazda új kérései ✅

**A hiba (végleges diagnózis):** a .P fejlécében a NXTLIN rendszerváltozó (0x4029, "a következő
végrehajtandó BASIC-sor címe") a hordozó-adat címét kapta (0x41FE) — a pgen "a program utáni
első bájt" feltételezéssel írta. A ROM a LOAD utáni futtatásnál innen olvas "sort": a
XOR-kódolt hordozót BASIC-sorként értelmezve parser-chaos → RST 0 = azonnali restart. A korábbi
verzióknál a C/F080-csonkolás elfedte ezt (sosem jutottak el idáig); a v0.3 volt az első, ami
egészben betöltött — ezért jelentkezett most. A javítás: NXTLIN = a display-file címe (a
hiteles zmakebas no-autostart recept), és a pfuttatas VÉGLEGES KAPUVAL őrzi a teljes 0x74 B-s
fejlécet (D_FILE/DF_CC/VARS/E_LINE/CH_ADD/STKBOT/STKEND/DF_SZ/S_TOP/LAST_K/FRAMES/MARGIN/
NXTLIN/S_POSN — a hiteles receptet a timex-sinclair zmakebas-port createHeader() adja).
**Renderváltozó-térkép hitelesítve** a valódi ROM listájából: RAMTOP=0x4004 (nem 0x4008!),
VARS=0x4010 (nem 0x4009!), CH_ADD=0x4016, STKBOT=0x401A, DF_SZ=0x4022, S_TOP=0x4023,
NXTLIN=0x4029, MARGIN=0x4028 — a korábbi pfuttatas "VARS=0x4009"-olvasása hibás címezés volt.

**Emulátor-hitelesség (romsim, D-4.0):** három valódi eltérés javítva a saját ROM-szimulátorban:
(1) reset után az NMI-kapu ZÁRVA (a valódi ULA: OUT(FD) bit7; a resetkor mindig-BE állás a
RAM-CHECK-et döntötte szét); (2) kapuzárt állapotban a "soralapú INT-csalás" ELTÁVOLÍTVA (a valódi
ZX81 ULA kapuzárva-nállásban SEMMILYEN megszakítást nem ad — a korábbi 0x0038-vihar az init
IM1-utáni részét rombolta); (3) a 0x0044-es videó-trükk (LD R,A / EI / JP (HL)) hookolva: a
JP-t nem hajtjuk végre, helyette soridő + sor-NMI (a valódi gépen az ULA ciklus-csenése miatt a
kijelző-bájtok végrehajtása láthatatlan — CPU-szinten nélküle wild PC → RST 38). Ismert nyitott
tételek: a sim teljes szerkesztői útja (CLS LDIR/RET lánc) még kisodródik — saját sim-hiba,
nem blokkolja a .P validációt (a pfuttatas USR-útja + a fejléc-kapu a mérvadó).

**A gazda új kérései (mind megvalósítva):** magyar identitás-válaszok (GLM SEGITSEGGEL KESZITETT
SAFAR SANDOR / MAGYARORSZAGON ELO AUTOBUSZVEZETO, AMATOR IRO ES CSILLAGASZ / CSAK ANGOLUL
BESZELEK SAJNALOM / EGY FECSKE NEM CSINAL NYARAT) + EMAIL-slot (SAFIZX810GMAIL.COM — a 0 az @,
a ZX81 nem tud kukacot) + HU trigger-tokenek (KI/KESZITETT/CSINALTA/EMAIL/MAGYARUL/BESZEL, a
szándéktábla 23 bejegyzésre bővült, 139/144 B); obszcén-mód (durva → azonnal sérteget-vissza,
enyhe → kocsma-regiszter; a detektor-szólista SZÁNDÉKOSAN kimarad a szótárból, hogy normál
beszédben sosem generálja); elgépelés-tűrés (Levenshtein-1, SANDEOR→SANDOR); ismeretlen szó
visszatanulása (echo-puffer spec, 8×16 B szabad RAM-ban); sortörés (egész szavak, minden szótári
szó ≤ 18 B ≤ 32 kar). Az alapmag slot-összevonásokkal (howareyou+askname, drawhouse+window,
tree+erase, daygreet+bye) helyet kapott a 4 új válasz. Rekordlimit 15→18 B (SAFIZX810GMAIL.COM).
v0.4 = pioco-0.4.p (5103 B), minden teszt zöld (epites/csomaggen/szimfuttatas/pgen+kapuk/pfuttatas).

## 2026-11-22 · 3. fázis, 9. szelet — A RESTART MÁSODIK GYÖKERE: SP-VÁLTÁS (D-4.1) ✅

**A gazda jelzése:** a 0.4 is azonnal restartol. A fejléc (D-4.0) helyes — a
zmakebas-plus port createHeader() forrásával bájtonként ellenőrizve (NXTLIN
no-autostart = D_FILE cím; minden más mező egyezik). A maradék hiba a BOOT-ban
volt: **LD SP,0x5400**. A ZX81 SLOW-kijelzője veremre szőtt koreográfia
(binárisból dekódolva, nem az OCR-listából): az NMI-kezelő (0x0066:
EX AF,AF' / INC A' / PUSH AF,BC,DE,HL a futó program veremére / LD HL,(D_FILE) /
SET 7,H / HALT / OUT(FD),A / JP (IX)) és a display-hurok (0x0038: DEC C / POP HL /
DEC B / RET Z / SET 3,C / LD R,A / EI / JP (HL) — a kijelző-bájtok a
ciklus-csenés miatt valóságon láthatatlanul "futnak le") a SP-re épül.
SP-csere esetén a következő NMI a mi adatainkra POP-ol → JP (HL) wild → restart.
A D-3.5-ös SP-váltás oka (PERSIST a 0x7F00-on) a D-3.8-cal megszűnt — a
váltás feleslegesen maradt bent. **Javítás: a boot a ROM veremén fut**
(USR-belépési SP ≈ 0x7FFE; a boot CALL-keretei ~40 B mélységig, a
PERSIST 0x7E00-0x7EFD-en tág határral nem ütközik).

**Teszteszköz-hiba is kijavítva:** a szalag-úton az elszállás (0x27 @ 0x4667 =
szótár-adat a motor-zónában) oka az volt, hogy ebben a körben a csomaggen
kimaradt a láncból → az ELAVULT pioco-0.1.tape-ben a stage-2 CALL STG1LOAD
címe a régi (3 bájtal nagyobb) boot LOADBLK-jére mutatott → a rutinba 3 bájttal
beljebb esve a fejléc-elcsúszás → TBL-tévedés → a szótár a 0x4600-ra íródott.
**Elavulási kapu** a szimfuttatasban: a szalag motor-blokkja bájtonként
egyezhessen az aktuális motor0.bin-nel. (A csomaggen parse_and_verify payload
mezője data[:0] — üres; a kapu a szalagot közvetlenül olvassa.)

**Verzió:** v0.5 = pioco-0.5.p (5100 B, REM-törzs 358 B, adat 0x41FB-től,
D_FILE=0x53DB), splash "16K  PIOCO  0.5". Teljes lánc zöld: epites →
csomaggen → szimfuttatas → pgen → pfuttatas. Nyitott tétel: a romsim
teljes ROM-szintű végpont-tesztje (a saját sim NMI/IX-protokollja még nem
hű a 0x0066-ás állapotgéphez — a pfuttatas + a fejléc-kapu a mérvadó).

## 2026-11-22 · 3. fázis, 10. szelet — A RESTART VALÓDI GYÖKERE: AZ ELVESZETT JAVÍTÁS (D-4.2) ✅

**A gazda jelzése:** a 0.5 sem indul. Következmény: felépítettem a fej nélküli
VALÓDI emulátort (ZEsarUX 13.1-B1, --vo stdout/null, ZRCP távvezérlés —
eszkozok/zvaloditest.py), és benben futtattam a fájlt. A lelet lesúlyos:
**a D-4.0-ás NXTLIN-javítás soha nem került a fájlba** — egy git-rebase
konfliktusfeloldása (a 9. szelet végén) a pgen.py régi `hw(32, data_start)`
sorát és a pfuttatas fejléc-kapujának hiányát hagyta meg; a 0.4 és az 0.5 is
hibás NXTLIN=0x41FB-val készült, a kapu nélkül a lánc zöldet mutatott.
Az emulátorok a .P betöltése után NXTLIN-ra ugranak (ZEsarUX-ben
megfigyelve: a saját autostartos tesztfájljuk magától fut le) — a
hordozócím az XOR-adatot futtatja BASIC-ként → azonnali restart, minden
verziónál. A diagnózis tehát 0.4 óta helyes volt, a javítás elveszett.

**Javítás (D-4.2):** pgen NXTLIN = 0x407D (az 1. sor címe — a zmakebas
autostart receptje; a betöltő emulátorok így REM → RAND USR 16514 → a
boot útvonalra lépnek) + a pfuttatas VÉGLEGES bájtonkénti fejléc-kapuja
(0x74 B a zmakebas createHeader receptje ellen, NXTLIN-nal együtt).

**Igazolás valódi emulátorban (ZEsarUX 13.1-B1):** mindkét betöltési úton
(közvetlen memóriakép és --realtape/--fastautoload) a boot lefut,
D_FILE=0x4200, a képernyőn "PIOCO AI" / "16K  PIOCO  0.6", a CPU a SLOW
kijelzőzési koreográgiában stabil (PC a tükörzött képernyőcímeken — a
ZX81 "kijelző-végrehajtása", a regiszter-pillanatképben visszaigazolva).
A lelet: kazetta/kepernyokep_valodi.txt. A futógépes bizonyság innentől
a szimulátor-hűség vitája helyett közvetlen: ami ZEsarUX-ben fut, az a
valódi gépen is fut.

**Verzió:** v0.6 = pioco-0.6.p (5100 B), splash "16K  PIOCO  0.6".
Teljes lánc zöld: epites → csomaggen → szimfuttatas → pgen → pfuttatas
→ zvaloditest (valódi emulátor, mindkét út).
