# PIOCO AI — 2. fázis: Tervezés, működés és dizájn

**Projekt:** PIOCO AI miniature language modell
**Platform:** Sinclair ZX81 · 16 KB RAM · Z80 @ 3,25 MHz · egy `.T81`
**Dátum:** 2026-11-21
**Állapot:** tervezési döntések rögzítve — a 3. fázis ezekből kódol

Ez a dokumentum lezárja az 1. fázis nyitott pontjait. Ami itt „döntés”, azt a kód nem találhatja ki újra.

---

## 1. Végleges memóriatérkép

A zónák folytonosak, 0x4000–0x7FFF, pontosan 16 384 bájt. A 3. fázis nem tolja el a határokat mérés nélkül; ha a motor túlnő, először a TARTALÉK, aztán a CHAT farából veszünk (a PROFIL-t soha).

| Cím | Zóna | Méret | Ki írhatja |
| --- | --- | ---: | --- |
| 0x4000–0x40FF | SYSVARS + saját állapot | 256 B | ROM + motor (csak a saját farok) |
| 0x4100–0x41FF | **PERSIST_BLOCK** | 256 B | csak a BOOT és a mentés; multiload **átugorja** |
| 0x4200–0x45FF | D_FILE + UI | 1024 B | csak a képernyőíró (biztonságos kódokkal) |
| 0x4600–0x53FF | MOTOR | 3584 B | kód, betöltéskor |
| 0x5400–0x5CFF | SZÓTÁR + súlyok | 2304 B | betöltéskor, futás közben csak olvasható |
| 0x5D00–0x62FF | CHAT | 1536 B | motor |
| 0x6300–0x6AFF | ALAPMAG | 2048 B | csak olvasható |
| 0x6B00–0x7AFF | CSOMAGTERÜLET | 4096 B | overlay-csere |
| 0x7B00–0x7DFF | MUNKATERÜLET | 768 B | motor, minden válasz előtt újrahasználható a nem-vászon rész |
| 0x7E00–0x7FFF | TARTALÉK | 512 B | üresen marad a 0.1-ben |

### 1.1 SYSVARS farok (0x4070–0x40FF) — saját állapot, nem a ROM területe

A ZX81 rendszerváltozói 0x4000-től kb. 0x403C-ig élnek (RAMTOP, D_FILE, VARS, E_LINE, stb.). A motor **nem ír** 0x4000–0x406F közé, kivéve amit a ROM maga vár (D_FILE mutató, hogy a saját képernyőnkre mutasson).

| Cím | Mező | Méret |
| --- | --- | ---: |
| 0x4070 | `MODE` 0=BOOT, 1=CHAT, 2=DRAW, 3=BASIC, 4=HELP | 1 |
| 0x4071 | `TEMP` 1..4 | 1 |
| 0x4072 | `REASON` 0/1 | 1 |
| 0x4073 | `CHAT_HEAD` körbuffer író index | 2 |
| 0x4075 | `CHAT_VIEW` görgetési offset | 2 |
| 0x4077 | `TOK_IN` / `TOK_OUT` utolsó üzenet tokenszáma | 1+1 |
| 0x4079 | `TICKS` utolsó válasz ideje (FRAMES/50, max 255 s) | 1 |
| 0x407A | `CLOCK_H` `CLOCK_M` a felhasználó által megadott óra, majd FRAMES-ből léptetve | 1+1 |
| 0x407C | `FRAME_ANCHOR` a megadott perc FRAMES-értéke (3 bájt) | 3 |
| 0x407F | `SPARE_SYS` | 1 |
| 0x4080–0x40FF | szabad a 0.1-ben (128 B) | 128 |

### 1.2 PERSIST_BLOCK (0x4100–0x41FF, 256 B) — soha nem írja felül a multiload

| Offszet | Mező | Méret | Szabály |
| ---: | --- | ---: | --- |
| 0x00 | mágia `P` `C` (0x35, 0x2A — ZX81 kód, nem ASCII) | 2 | ha nem egyezik, a blokk üres |
| 0x02 | verzió = 1 | 1 | |
| 0x03 | név, max 12 ZX81 karakter, jobbról 0x00-val töltve | 12 | csak 0x00–0x3F |
| 0x0F | `FLAGS` (lásd 2.1) | 1 | XOR 0xA5-tel tárolva |
| 0x10 | születés év (1900-tól, 0–127) | 1 | |
| 0x11 | születés hónap 1–12 | 1 | |
| 0x12 | születés nap 1–31 | 1 | |
| 0x13 | munkamenet év (2000-től, 0–99) | 1 | |
| 0x14 | munkamenet hónap, nap | 2 | |
| 0x16 | munkamenet óra, perc (a BOOT-kor beírt „pontos idő”) | 2 | |
| 0x18 | `REMIND[4]` — 4 emlékeztető × 4 bájt | 16 | lásd 6. |
| 0x28 | `STATE[8]` állapotbájtok, XOR 0xA5 | 8 | lásd 2.2 |
| 0x30 | `STATE_DAY[8]` minden állapot napja a munkamenet-dátumhoz képest (0–255) | 8 | elavulás |
| 0x38 | vita: téma-token (1) + álláspont-kód (1) + 14 bájt kulcstoken | 16 | |
| 0x48–0xFF | tartalék (184 B) | 184 | 0x00-val töltve |

A multiload betöltő címtartománya **soha** nem metszi a 0x4100–0x41FF-et. A S2 a motort 0x4600-ra, a szótárat 0x5400-ra, az ALAPMAG-ot 0x6300-ra tölti.

### 1.3 MUNKATERÜLET (0x7B00–0x7DFF, 768 B) — döntés a szűkösségre

| Cím | Használat | Méret |
| --- | --- | ---: |
| 0x7B00–0x7C5F | **vászon** 64×44 bit = 44×8 | 352 |
| 0x7C60–0x7CDF | token-puffer (bejövő + kimenő, max 128 token) | 128 |
| 0x7CE0–0x7CFF | reasoning verem (8 lépés × 4 bájt) | 32 |
| 0x7D00–0x7DFF | BASIC-puffer, max 256 bájt tokenizált sor | 256 |

**Döntés:** a vászon és a BASIC-puffer **egyszerre** él. Egyik sem törli a másikat. Ha egy BASIC program 256 bájtnál hosszabb kellene, a motor kimondja, hogy ennyi fér, és a legrégebbi sort ajánlja fel törlésre — nem nyúl a CSOMAGTERÜLET-hez a 0.1-ben.

---

## 2. Bitmezők

Minden bitmező **tároláskor XOR 0xA5**. A képernyőre csak a kibontott, szöveggé alakított jelentés kerülhet. A 0xA5 XOR bármely 0x00–0xFF bájt ritkán ad 0x76-ot; ha a tárolt bájt mégis 0x76 lenne, a motor mentés előtt +1-et ad a tartalék bitre (bit7), amíg a tárolt érték nem 0x76. Ez a „76-kerülő”.

### 2.1 FLAGS (1 bájt)

| Bit | Jelentés |
| --- | --- |
| 0 | nem: 0 = férfi, 1 = nő |
| 1–2 | kor: 00 gyerek (<14), 01 fiatal, 10 felnőtt, 11 60+ — születési évből számolja a BOOT, nem kérdezi külön |
| 3 | útmutatót kért (1 = igen) |
| 4 | reasoning alapból be (BOOT után 1) |
| 5 | óra megadva és érvényes |
| 6 | profil kész (BOOT lefutott) |
| 7 | 76-kerülő tartalék, jelentés nélkül |

### 2.2 STATE[8] — 64 darab 1 bites tény

A 0.1 csak az első 16 bitet használja, a többi 0.

| Bájt.bit | Tény |
| --- | --- |
| 0.0 | fáj a fej |
| 0.1 | fáradt |
| 0.2 | beteg |
| 0.3 | éhes |
| 0.4 | dolgozik ma |
| 0.5 | otthon van |
| 0.6 | mérges (utolsó üzenet hangulata) |
| 0.7 | viccel (utolsó üzenet hangulata) |
| 1.0–1.7 | tartalék a 0.1-ben |
| 2–7 | későbbi témacsomagok (egészség, munka, …) |

Minden használt bithez tartozik `STATE_DAY[i]`: hány napja íródott, a munkamenet dátumához képest. **7 nap** után a bit elavult: a motor rákérdez, és csak az új válasz után írja felül. Nem találgat.

---

## 3. Karaktertábla — mit szabad a képernyőre írni

A D_FILE minden megjelenő bájtja **csak** ezek közül kerülhet ki:

| Tartomány | Jelentés | Szabad? |
| --- | --- | --- |
| 0x00–0x0B | számjegyek, írásjelek egy része a ZX81 készletben | igen |
| 0x0C–0x25 | A–Z (a ZX81 nagybetűs) | igen |
| 0x26–0x3F | szóköz-környéki jelek és blokkgrafika | igen |
| 0x40–0x75 | token / parancskód a programtárban | **tilos** a képernyőn |
| 0x76 | sorzáró (HALT) | **tilos**, kivéve a sor végét, amit csak a képernyőíró tesz ki, soronként egyet |
| 0x77–0x7F | további tokenek | **tilos** |
| 0x80–0xBF | az előző 0x00–0x3F inverze (fejléc, kiemelés) | igen |
| 0xC0–0xFF | inverz tokenek | **tilos** |

A pörgő effekt csak a 0x08–0x0F és 0x80|ezek halmazból lépked. A képernyőíró minden bájt előtt maszkol: ha a kód nincs a szabad halmazban, szóközt (0x00) ír helyette.

A D_FILE elrendezése a saját UI-ban nem a gyári 24×33, hanem **rögzített 24 sor × (32 karakter + 1 db 0x76)**. A D_FILE mutató 0x4200. Méret: 24×33 = 792 B. A 0x4200–0x45FF maradéka (1024−792 = 232 B) scratch: ideiglenes sorösszeállítás, **nem** jelenik meg, és ide sem kerül 0x76, hogy egy elcsúszott mutató se fagyassza a gépet.

---

## 4. Képernyők

Minden képernyő 32 oszlop × 24 sor. A számok a sor indexei (0–23).

### 4.1 BOOT (Sáv 1)

| Sor | Tartalom |
| --- | --- |
| 0–1 | pörgő, biztonságos blokkgrafika |
| 2–6 | „PIOCO AI” nagy, inverz, középre |
| 7 | „ZX81  16 KB” |
| 8 | üres |
| 9 | „SZIA.” |
| 10 | „UTMUTATO?  I / N” |
| 11–16 | ha I: 6 soros rövid segítség (vezérlők), majd tovább |
| 17 | „NEV?” — ROM INPUT, max 12 karakter, szűrve 0x00–0x3F |
| 18 | „NEM?  F / N” |
| 19 | „SZUL: EE HH NN” (év 00–99 → 1900+, hónap, nap) |
| 20 | „MOST: EE HH NN OO PP” (dátum + óra + perc) |
| 21 | „KESZ. BETOLTOM A MOTORT.” |
| 22–23 | „START” villog, majd Sáv 2 |

Hibás számnál a sor újra kérdez, nem fagy. Üres név nem mehet tovább.

### 4.2 Csevegő

| Sor | Tartalom |
| --- | --- |
| 0 | státusz, inverz: `T1-4 R+  OO:PP` (hőmérséklet, reasoning, óra) |
| 1–20 | üzenetek. Minden üzenet előtt **egy inverz fejlécsor**: `P 12:41 TK214 0.8S` vagy `N 12:42 TK009  --` (P = PIOCO, N = név első betűje) |
| 21 | thinking: üres, vagy `GONDOLKODOM 2/4` |
| 22–23 | bevitel. A kurzor a 23. sorban. ROM `INPUT` csak akkor, ha a D_FILE mutató a saját képernyőnkre mutat és a 23. sor 0x76-ra végződik |

**Döntés a ROM INPUT-ról:** a 0.1 a ROM INPUT-ot használja, de előtte a motor beállítja a D_FILE-t, az E_LINE-t és a 23. sor keretét. Ha a ROM rutin a saját UI-t szétírja (ezt a 3. fázis első tesztje méri), vékony saját bevitel lép a helyére: ugyanaz a sor, ugyanazok a billentyűk, a ROM csak a billentyűolvasást adja (`KSCAN`). A felhasználó ebből semmit nem lát — ugyanaz a sor marad.

Görgetés: `SHIFT+5` / `SHIFT+6` a CHAT körbufferben mozgatja a `CHAT_VIEW`-t, és újrarajzolja az 1–20. sorokat. A beviteli sor nem mozdul.

### 4.3 Rajz mód

| Sor | Tartalom |
| --- | --- |
| 0 | inverz: `RAJZ  HOZZAAD` |
| 1–12 | a 64×44 bitmap ide renderelve (ZX81 plot: 2×2 pixel / karakterhely ≈ 32×22 karakterhelyből a felső 32×11) |
| 13–20 | a modell egy sora: mit rajzolt hozzá („ABLAK A HAZRA”) |
| 21–23 | ugyanaz a thinking + bevitel, mint a csevegőn |

**Hozzáadó szabály:** a vászon bitjei csak 0→1 irányba változnak, amíg a felhasználó ki nem mondja, hogy „töröld a rajzot”. Ablak, fa, ajtó külön fix téglalap a 64×44-en (ház: x 16–47, y 16–40; ablak: x 22–30, y 22–30; fa: x 50–60, y 18–40). A motor ezeket a téglalapokat **OR**-olja a vászonra.

### 4.4 BASIC mód

A képernyőn a program listája látszik (sorszám + szöveg), alul a bevitel. A pufferben minden sor: 2 bájt sorszám (BCD-szerű, 1–999) + 1 bájt hossz + tokenizált szöveg. Beszúrás: a motor a sorszám szerint a helyére csúsztat. Csere: azonos sorszám felülír. Törlés: hossz = 0, majd tömörítés. A 256 bájt betelése esetén egy soros üzenet, és nem ír tovább.

---

## 5. .T81 sávformátum

Egy fájl, több egymás utáni ZX81 fájlblokk (gyári formátum a 0.1-ben; turbo **ki**).

| Sorrend | Név a kazettán (max 8) | Hova tölt | Méret plafon |
| --- | --- | --- | ---: |
| 1 | `PIOCOBOOT` | 0x4200-tól a splash kód+kép, majd visszaadja a vezérlést; a PROFIL-t 0x4100-ra **írja**, nem tölti felül később | ≤ 2 KB |
| 2 | `PIOCOMOT` | 0x4600, pontosan a motor | ≤ 3584 |
| 3 | `PIOCOSZO` | 0x5400 szótár+súly | ≤ 2304 |
| 4 | `PIOCOALAP` | 0x6300 ALAPMAG | ≤ 2048 |
| 5 | `PIOCOPACK` | 0x6B00 első témacsomag (üres váz a 0.1-ben) | ≤ 4096 |
| + | `PACK####` | ugyanoda, csere | ≤ 4096 |
| M | `SAVEnnnn` | nem a RAM közepére: először 0x5D00 (CHAT) és 0x4100 egy **másolat** a munkaterület szabad részén összefűzve, azt menti | ≤ 1536+256 |

**Kazetta-döntés (lezárva):** középre nem írunk felül. A mentés mindig **új blokk a szalag végén**, neve `SAVE` + négyjegyű sorszám. Visszatöltéskor a motor a legnagyobb sorszámú ép blokkot veszi. A régiek a szalagon maradnak. Külön mentőkazetta nem kell a 0.1-hez.

Minden adatblokk elején 4 bájt saját fejléc a ZX81 név után, a betöltött bájtok között:

| Bájt | Jelentés |
| --- | --- |
| 0 | típus: 1=BOOT, 2=MOTOR, 3=SZÓTÁR, 4=ALAP, 5=CSOMAG, 6=MENTÉS |
| 1 | verzió |
| 2–3 | hasznos hossz (little-endian) |

A BOOT betöltő kódja a fejléc típusát nézi, és **megtagadja** a betöltést, ha a célcím metszené a 0x4100–0x41FF-et.

---

## 6. Emlékeztető

Négy fér egyszerre. Egy rekord 4 bájt a PERSIST-ben:

| Bájt | Jelentés |
| --- | --- |
| 0 | bit7 = aktív; bit0–4 = óra 0–23; a felső bitek a 76-kerülővel együtt XOR 0xA5 alatt |
| 1 | perc 0–59 |
| 2 | token: mire emlékeztessen (1 bájt, a szótárból; 0 = „DOLGOZNI”) |
| 3 | a lerakás napja (`STATE_DAY` skálán) |

A motor a BOOT-kor megadott órát tekinti nullának, és a `FRAMES` (50 Hz, a ROM számlálója) alapján lépteti a percet **SLOW** módban. **Döntés:** a 0.1 csak SLOW-ban fut. FAST alatt a képernyő úgyis kikapcsol, a csevegőnek nincs értelme; ha a gép FAST-ba esne, a motor visszakapcsolja SLOW-ra, és a percet nem lépteti addig, amíg az óra újra stabil. Így nem ígérünk másodperc-pontos ébresztést FAST mellett.

Amikor `CLOCK_H:CLOCK_M` eléri a rekordot, a thinking sor helyén egyszer kiírja: `EMLEKEZTETO: <token szövege>`, és a rekord aktív bitjét törli.

---

## 7. Agent-parancsok

A reasoning végén a motor **egy** belső parancsot választ, mielőtt szöveget ír. A felhasználó ezeket nem gépeli; a szövegéből következnek. A 0.1 készlete:

| Kód | Név | Mikor | Hatás |
| ---: | --- | --- | --- |
| 0 | `SAY` | sima kérdés, vélemény | szöveget generál |
| 1 | `ASK` | hiányzó adat (név, óra, „még fáj?”) | egy rövid kérdést ír, és vár |
| 2 | `SETBIT` | „fáj a fejem”, „már nem” | STATE bit + nap |
| 3 | `REMIND` | „emlékeztess 8-kor…” | REMIND rekord, ha van szabad hely |
| 4 | `DRAW` | „rajzolj házat / ablakot / fát” | rajz mód, OR a vászonra |
| 5 | `DRAWCLR` | „töröld a rajzot” | vászon nullázás (egyetlen törlő út) |
| 6 | `BASIC` | „írj programot…” | BASIC mód, sorok a pufferbe |
| 7 | `BASICEDIT` | „a 20-as sort cseréld…” | sorszám szerinti csere/beszúrás |
| 8 | `MOOD` | ingerült, dicsérő, vitázó mondat | FLAGS/STATE hangulatbitek + SAY |
| 9 | `LOADPACK` | „beszéljünk csillagokról” | Sáv kérése, CSOMAGTERÜLET csere |
| 10 | `SAVE` | SHIFT+S vagy „mentsd el” | SAVE blokk a szalag végére |
| 11 | `STOP` | SHIFT+SPACE | generálás megszakítása, a sor törlése |

Ha a reasoning nincs bekapcsolva (`SHIFT+9`), a `MOOD` és a többlépéses terv kimarad, de a `DRAW` / `BASIC` / `REMIND` / `SETBIT` akkor is lefut — különben a gép „buta parancsértelmezővé” esne vissza, amit a mesterprompt tilt.

Hangulat a 0.1-ben, saját mondatvázból (nem kész válasz):

- mérges + lassúság → a váz a 3,25 MHz-et és a várakozást említi
- dicséret / „zseni” → a váz a 16 KB-ot említi, öniróniával
- „PC jobb, mint a ZX81” → a vita-blokkba beírja az álláspontot (ZX81 mellett), és a következő körök a CHAT + vita-blokk tokenjeiből építkeznek

---

## 8. Generálás, ahogy a 0.1 tényleg működik

1. INPUT sor → csak 0x00–0x3F karakterek a token-pufferbe.
2. Tokenizálás: szótár (hossz szerint, leghosszabb illesztés), a maradék betűnként.
3. Ha reasoning be van kapcsolva: legfeljebb 4 lépés a thinking sorban (`SZANDEK`, `SZO`, `TUDAS`, `TERV`). Közben `SHIFT+SPACE` megszakít.
4. Egy Agent-kód.
5. Ha `SAY` vagy `MOOD`: a következő tokent a 4 bites súlyok és a hőmérséklet választja.
   - hőmérséklet 1: mindig a legnagyobb súly
   - 2: az első 2 közül, R regiszter bitje dönt
   - 3: az első 4 közül, R+FRAMES alsó 2 bitje
   - 4: az első 8 közül, ugyanez
6. Toldalék-token a magyar egyeztető táblából (a szótár része, nem külön memória).
7. Legfeljebb 4 sor szöveg, aztán `TOVABB?` — a képernyőn nincs hely többre.
8. A CHAT körbufferbe bekerül a fejléc (óra, token, idő) és a szöveg token-ID-kkal, nem nyers képernyőkóddal.

Ismeretlen szóra nem mond „nem értem” sablont: betűnként beolvassa, és a legközelebbi tudás-tokennel válaszol, vagy `ASK`-kal rákérdez.

---

## 9. Amit a 3. fázisnak tilos újradöntenie

- A címtartományok határai, amíg mérés nem kényszeríti (és a PROFIL akkor sem mozdul).
- XOR 0xA5 + 76-kerülő minden bitmezőn.
- Képernyőre csak 0x00–0x3F és 0x80–0xBF, plusz sorvég 0x76.
- Turbo ki.
- Mentés csak szalagvégre, `SAVEnnnn`.
- Vászon csak hozzáad (OR), törlés csak `DRAWCLR`.
- SLOW kötelező a futás alatt.
- Négy emlékeztető, 256 bájtos BASIC-puffer, 12 karakteres név.

## 10. A 3. fázis első szelete (hogy legyen mit futtatni)

Nem az egész motor egyszerre. Sorrend:

1. BOOT képernyő + profil kérdések + PERSIST írás, önálló `.T81`, emulátorban.
2. Üres csevegőkeret: fejléc, INPUT, `SHIFT+1..4` és `SHIFT+9` látszik a státuszsoron.
3. Tokenizáló + egy `SAY`, ami az ALAPMAG-ból rak össze 1–2 sort.
4. `SETBIT` + elavulás, `REMIND`, `DRAW` a három fix alakzattal, `BASIC` egy 4 soros programmal.
5. Mentés / visszatöltés a szalag végéről.

Minden szelet után egy `.T81` a `kazetta/` alatt, és egy sor a fejlesztési naplóban: betöltött-e, fagyott-e, a PROFIL megmaradt-e a második sáv után.

---

*Készült: 2026-11-21 · 2. fázis — tervezés és dizájn.*
