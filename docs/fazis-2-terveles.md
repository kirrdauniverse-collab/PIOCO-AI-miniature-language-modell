# PIOCO AI — 2. fázis: Tervezés, működés és dizájn

**Projekt:** PIOCO AI miniature language modell
**Célplatform:** Sinclair ZX81 · 16 KB RAM · Z80 @ 3,25 MHz · egyetlen, több betöltési sávot tartalmazó `.T81` kazettafájl
**Dátum:** 2026-11-21
**Repó:** `github.com/kirrdauniverse-collab/PIOCO-AI-miniature-language-modell`
**Előzmény:** `docs/fazis-1-koncepcio.md` (1. fázis, a mesterprompt-kiegészítéssel együtt)

> Ez a dokumentum a tervezés véglegesítése: minden ottani „javaslat" itt **döntéssé** válik, címszámokkal és bájtpontos elrendezéssel — a 3. fázis kódja ezeket nem találhatja ki újra. Minden bontást Python-számítás ellenőrzött (`scripts/pio_f2_calc.py`); a platformtények (karakterkód-tartományok, PLOT-terület, rendszerváltozók) a dokumentum végén felsorolt forrásokból származnak — nem találmányok.

---

## 1. A fázis céljai és a meghozott döntések

A 2. fázis a következő nyitott pontokat zárta le — mindegyik részletesen a hivatkozott fejezetben:

1. **Végleges memóriatérkép belső bontásokkal** — „ki írhatja" jogosultsági oszlop, SYSVARS-farok tervezett mezői, MUNKATERÜLET-véglegesítés (a rajzvászon **és** a BASIC-puffer bent van a 768 B-ban) — lásd 2.
2. **Szótár-véglegesítés és egy őszinte korrekció** — az 1 bájtos token-ID miatt a szótár 256 ID-re korlátozódik; a fázis-1-es „kb. 400–460 token" becslés ebben a formában nem tartható, a végleges szótár **224 tartalmi token** — lásd 3.
3. **Bitmezők végleges bontása** — PERSIST_BLOCK bájtszintű elrendezése: mágia, FLAGS, 64 darab 1 bites tény (STATE[8] + STATE_DAY[8] elavulással), 4 emlékeztető, vitakövető, CRC — lásd 4.
4. **Karaktertábla és a 0x76-szabály végrehajtása** — forrás-hitelesített tartományok, D_FILE-elrendezés (792 B), „print-tölcsér", önteszt — lásd 5.
5. **.T81 sávformátum** — elnevezett blokkok (PIOCOBOOT … SAVEnnnn), belső fejléc + saját CRC (a ROM LOAD checksumot nem ad!), multiload-lánc — lásd 6.
6. **Képernyőtervek** — hat végleges képkocka, sor-szintű vázlatokkal — lásd 7.
7. **Vezérlők véglegesítése** — a mesterprompt kötelező kiosztása + öt új mód-billentyű, ütközésmentesen — lásd 8.
8. **Agent-parancsnyelv** — 14 belső parancs a képernyőre nem kerülhető token-tartományban — lásd 9.
9. **Rajzolás és BASIC alrendszer** — vászon-zónák és fix alakzat-területek, csak-hozzáadó mód; BASIC szerkesztési műveletek — lásd 10–11.
10. **Emlékeztető-modul** — FRAMES-alapú időzítés, SLOW-döntés, elavulás — lásd 12.
11. **A generálási lánc futásidőben** — a hőmérséklet top-k leképezése és a válasz-hossz szabály — lásd 13.

A memóriatérkép tíz zónája és minden **zónaszintű** bájtméret az 1. fázisból változatlanul át lett véve (0x4000–0x7FFF, folytonos, pontosan 16 384 B, ellenőrzött) — ez a dokumentum a zónák **belsejét** teszi pontossá.

## 2. Végleges memóriatérkép

### 2.1 A tíz zóna és a jogosultságok

| Címtartomány | Zóna | Méret | Ki írhatja |
| --- | --- | ---: | --- |
| 0x4000–0x4081 | Rendszerváltozók + saját állapot (farok) | 130 B | a ROM (a saját területén) + a motor (csak a 2.2 farokmezőit) |
| 0x4082–0x41FF | **BOOT-betöltő sáv** (stage-1 kód + adat) | 464 B | csak betöltéskor; a betöltő saját scratch-e (fejléc-pufferek, táblák) |
| 0x4200–0x45FF | D_FILE + UI puffer | 1024 B | kizárólag a képernyőíró (print-tölcsér, biztonságos kódokkal) |
| 0x4600–0x53FF | MOTOR (kód) | 3584 B | csak betöltéskor |
| 0x5400–0x5CFF | SZÓTÁR + súlytömb | 2304 B | betöltéskor; futás közben **csak olvasható** |
| 0x5D00–0x62FF | CHAT history | 1536 B | motor (körbuffer) |
| 0x6300–0x6AFF | ALAPMAG | 2048 B | betöltéskor; futás közben csak olvasható |
| 0x6B00–0x7AFF | CSOMAGTERÜLET (overlay-k) | 4096 B | overlay-csere |
| 0x7B00–0x7DFF | MUNKATERÜLET | 768 B | motor; a nem-vászon rész minden válasz előtt újrahasználható |
| 0x7E00–0x7EFF | TARTALÉK | 256 B | a 0.1-ben üresen marad |
| 0x7F00–0x7FFF | **PROFIL / PERSIST_BLOCK** | 256 B | csak a BOOT sáv és a mentés/visszatöltés; minden más sáv **átugorja** |

Ha a 3. fázis mérése a motort sürgeti, először a TARTALÉK, majd a CHAT fara ad helyet — a PERSIST_BLOCK akkor sem mozdul.

**D-3.3 korrekció (2026-11-21, mért ütközés):** az eredeti terv a PERSIST_BLOCK-ot a 0x4100–0x41FF-re tette. A 3. fázis végpont-tesztje (Z80-szimuláció) azonban mérte, hogy a REM-sorba rejtett boot-kód a 0x4082-től nő felfelé, és a 126 bájtos hely (0x4082–0x40FF) kevés — a stage-1 betöltő már 262 B, a PERSIST-init nullázó ciklusa így saját magát törölné ki. Ezért a PERSIST_BLOCK a RAM tetejére, a **0x7F00–0x7FFF**-re költözött (a TARTALÉK 256 B-ra zsugorodott), a **0x4082–0x41FF pedig a BOOT-betöltő saját sávája** lett (kód + fejléc-pufferek + típus→cél tábla). Ez az egyetlen címzóna-kihagyás a mesterprompt memóriatérkép-követelménye alól, indoka tiszta mérés.

### 2.2 SYSVARS-farok — a motor saját állapotmezői

A ZX81 rendszerváltozói 0x4000-től folynak; a motor a saját állapotait **a ROM sysvars-vége utáni első szabad tartományba** teszi (a pontos kezdőcímet a 3. fázis rögzíti a ROM-listából — címet itt nem kötünk le). Tervezett mezők:

| Mező | Méret | Jelentés |
| --- | ---: | --- |
| `MODE` | 1 | 0 = BOOT, 1 = CSEVEGŐ, 2 = RAJZ, 3 = BASIC, 4 = ÚTMUTATÓ |
| `TEMP` | 1 | hőmérséklet 1–4 |
| `REASON` | 1 | gondolkodás-megjelenítés 0/1 |
| `CHAT_HEAD` | 2 | a chat körbuffer íróindexe |
| `CHAT_VIEW` | 2 | görgetési offset (`SHIFT+5/6`) |
| `TOK_IN` / `TOK_OUT` | 1 + 1 | az utolsó üzenet tokenjei (fejléchez) |
| `TICKS` | 1 | az utolsó válasz ideje (FRAMES/50, max 255 s) |
| `CLOCK_H`, `CLOCK_M` | 1 + 1 | a BOOT-kor megadott óra/perc, FRAMES-ből léptetve |
| `FRAME_ANCHOR` | 3 | az utolsó perclépés FRAMES-értéke |

### 2.3 MUNKATERÜLET belső bontása — a vászon + BASIC döntés (D-2.1)

| Cím | Tartalom | Méret | Megjegyzés |
| --- | --- | ---: | --- |
| 0x7B00 | **rajzvászon** 64×44 bit | 352 B | 44 sor × 8 bájt; csak-hozzáadó mód (10. fejezet) |
| 0x7C60 | token-puffer (bejövő + kimenő) | 128 B | max 128 token — egy 32 karos bemenet legfeljebb ~25 token |
| 0x7CE0 | reasoning verem | 32 B | 8 lépés × 4 bájt (a generálás max 4 lépést használ) |
| 0x7D00 | **BASIC program-puffer** | 256 B | kb. 14–16 rövid programsor (11. fejezet) |

Összesen 768 B, folytonos, ellenőrzött. A bemeneti szöveg külön bufferét elhagytuk: a ROM `INPUT` a képernyősorra olvas, a tokenizáló onnan veszi át a szöveget — így nincs duplikáció. **D-2.1 döntés:** a vászon és a BASIC-puffer **egyszerre él**, egyik nem törli a másikat. Ha egy BASIC program 256 bájtnál hosszabb kellene, a motor kimondja, hogy ennyi fér, és felajánlja a program szalagra mentését, illetve — ha éppen nincs overlay betöltve — a CSOMAGTERÜLET szabad farára helyezését (a következő overlay felülírja, a motor előre jelzi). A TARTALÉK zónát ez nem érinti.

### 2.4 SZÓTÁR belső bontása

| Tartalom | Méret | Megjegyzés |
| --- | ---: | --- |
| tokenrekordok (hossz-prefix, ID-sorrendben) | 1144 B | kb. 208 rekord × 5,5 B (szó + toldalék) |
| betűtábla | 16 B | a 16 leggyakoribb magyar betű (0xF0–0xFF ID-khoz) |
| trigram súlytömb | 1000 B | 250 rekord × 4 B: k1, k2, k3 + súlynibble (3.3) |
| tartalék (bigram-bővítés + ráhagyás) | 144 B | a 50–150 B tartalékelv itt is teljesül |
| **Összesen** | **2304 B** | pontosan, ellenőrzött |

## 3. Tokenrendszer véglegesítése

### 3.1 Token-ID bontás (1 bájt, 0–255)

| ID-tartomány | Szám | Rendeltetés |
| --- | ---: | --- |
| 0x00–0x0F | 16 | vezérlőtokenek: szóhatár, mondatvége, választerv-jelölők |
| 0x10–0x1F | 16 | **Agent-parancs-tokenek** (9. fejezet) — a képernyőre nem kerülhető tartomány (5.1), ezért programhiba esetén sem íródhatnak ki |
| 0x20–0x3B | 28 | toldalék/funkció-tokenek (angol prototípus: THE, A, AND, IS, ARE, I, YOU, NOT stb. + utótagok: -S, -ED, -ING, -LY, 'S — D-3.2) |
| 0x3C–0xEF | 180 | szótokenek (a korpusz leggyakoribb tartalmi szavai — angol prototípus) |
| 0xF0–0xFF | 16 | betűtokenek (ismeretlen szó betűesése) |

### 3.2 Korrekció a fázis-1-es becsléshez képest (D-3.1)

Az 1. fázis „kb. 400–460 token" becslést adott, de minden token-ID 1 bájtos — így **legfeljebb 256 különböző ID** lehet. A végleges döntés: **224 tartalmi token** (180 szó + 28 toldalék + 16 betű) + 32 vezérlő/Agent ID. A lefedettséget ez adja: a leggyakoribb ~180 magyar szó a köznyelvi szövegek jelentős részét fedezi, a toldaléktokenek a ragrendszert, a betűesés a maradékot (ismeretlen szó betűnkénti tokenizálása). Ez a kompromisszum tudatos: a szótár így kisebb és gyorsabban szkennelhető, a szabad kapacitás a súlytömbnek jut. A 3. fázis méri a tényleges lefedettséget; ha szükséges, a CSOMAGTERÜLET témafüggetlen szó-bővítést kaphat (a betöltött overlay saját szólistával egészíti ki a modellt).

### 3.3 A trigram súlytömb

A nyelvi modell magja a 2–3 szó kontextusú trigram-táblázat **4 bites egész súlyokkal** (`-8..+7`, bájtonként kettő csomagolva — itt rekordonként 1 súlynibble + 1 tartaléknibble). Rekord: `k1, k2, k3, [súly|tartalék]` = 4 bájt; 250 rekord = 1000 B. A súlyok a PC-s csomagépítőben kvantálódnak: a korpusz-számítás 16 bites, a kvantálás után a motoroldali keresés egészszámos (`nibble → előjeles bővítés → összegzés`), lebegőpontos művelet nélkül. A keresés: kontextus `(k1,k2)` illesztése → talált trigramok súly szerinti rangsorolása → hőmérséklet szerinti top-k → választás (13. fejezet).

### 3.4 Nyelvi irány: angol prototípus (D-3.2 — a projektgazda döntése, 2026-11-21)

A prototípus nyelve **angol**: a magyar nyelv nagy helyet foglal és bonyolult (törzs + gazdag ragozás), míg az angol egyszerűbb morfológiával **több szót** enged befogadni a 224 tartalmi tokenbe — a kiforrott modell után pedig visszatérhetünk a magyar finomítására (a toldaléktoken-sáv, 0x20–0x3B, akkor a magyar ragrendszerre vált át). A ZX81 karakterkészlete csak **nagybetűs** karaktereket tartalmaz, ezért minden szöveg nagybetűs ASCII-ben él a szótárban, és a motor **ASCII→ZX81 kódtáblája** fordít printkor — a tábla tartalma nyílt tétel a ROM-listából; rossz tábla esetén a print-tölcsér csak szóközt ad, a `0x76`-biztonság nem sérül. Ehhez kapcsolódó egyszerűsítés: a PERSIST mágia ASCII „P", „C" (0x50, 0x43), a korábbi „ZX81-kód" felvetés helyett. Az eszközök (tokengen) már ezt az angol irányt implementálják.

## 4. Bitmezők végleges bontása

### 4.1 PERSIST_BLOCK elrendezés (0x7F00–0x7FFF — D-3.3 korrekció, korábban 0x4100–0x41FF)

A teljes blokk **XOR 0xA5 maszkkal** tárolódik, **CRC-16** (polinom 0x1021, kezdőérték 0xFFFF) zárja, és minden bitmezőre igaz a **„76-kerülő"**: mentéskor, ha a maszkolt bájt mégis éppen `0x76` lenne, a motor a tartalék bitet átbillenti, amíg a tárolt érték nem `0x76` — így a maszk ellenére sem állhat elő a sorszáró kód. A mágia két bájtja az ASCII „P", „C" (0x50, 0x43 — a D-3.2 nyelvi döntéssel egyszerűsítve); hibás mágia vagy CRC esetén a blokk üresnek számít, és a motor a BOOT-sávos újrakérdezéssel áll helyre.

| Offset | Méret | Tartalom |
| --- | ---: | --- |
| 0x00 | 2 | mágia „P", „C" (ASCII 0x50, 0x43) — érvénytelen mágia → üres profil |
| 0x02 | 1 | verzió (0x01) |
| 0x03 | 1 | FLAGS (4.2) |
| 0x04 | 1 | hőmérséklet alapérték (alsó 2 bit, 1–4) + tartalék |
| 0x05 | 12 | név (max 12 ZX81-karakter — a BOOT szűri a 0x00–0x3F tartományra) |
| 0x11 | 3 | születés: év (1900+, 1 B) + hónap (1) + nap (1) |
| 0x14 | 5 | munkamenet dátum + óra: éé (1) hó (1) nap (1) óra (1) perc (1) — a BOOT kérdezi, a motor FRAMES-ből lépteti |
| 0x19 | 8 | **STATE[8]** — 64 darab 1 bites tény (4.3) |
| 0x21 | 8 | **STATE_DAY[8]** — minden bit hány napja íródott (0–255, elavulás) |
| 0x29 | 24 | **REMIND[4]** — 4 emlékeztető × 6 B (4.4) |
| 0x41 | 16 | vitakövető: téma-ID, álláspont-ID + 14 bájt kulcstoken (4.5) |
| 0x51 | 171 | tartalék (bővítés) |
| 0xFC | 2 | CRC-16 (0x1021, init 0xFFFF) |
| 0xFE | 2 | tartalék |

Összesen 256 B, folytonos, ellenőrzött. A multiload betöltő címtartománya **soha** nem metszi a 0x7F00–0x7FFF-et (a BOOT betöltője betöltéskor is ellenőrzi: fejléc-cél a védett tartományba → betöltés megtagadva).

### 4.2 FLAGS (1 bájt)

| Bit | Jelentés |
| --- | --- |
| 0 | nem: 0 = férfi, 1 = nő |
| 1–2 | korosztály (00 gyerek, 01 fiatal, 10 felnőtt, 11 60+) — **a születési évből számolja a BOOT, nem kérdezi külön** |
| 3 | útmutatót kért (1 = igen) |
| 4 | reasoning alapból bekapcsolva (BOOT után 1) |
| 5 | splash-effekt bekapcsolva |
| 6 | óra megadva és érvényes |
| 7 | profil kész (a BOOT lefutott) |

### 4.3 STATE[8] + STATE_DAY[8] — 64 darab 1 bites tény

A 0.1 csak az első 16 bitet használja, a többi tartalék (későbbi témacsomagok: egészség, munka, …):

| Bájt.bit | Tény |
| --- | --- |
| 0.0 | fáj a fej |
| 0.1 | fáradt |
| 0.2 | beteg |
| 0.3 | éhes |
| 0.4 | dolgozik ma |
| 0.5 | otthon van |
| 0.6 | mérges (az utolsó üzenet hangulata) |
| 0.7 | viccel (az utolsó üzenet hangulata) |

Minden használt bithez tartozik `STATE_DAY[i]`: hány napja íródott, a munkamenet-dátumhoz képest. **7 nap** után a bit elavult: a motor rákérdez, és csak az új válasz után írja felül — nem találgat. Példa a mesterprompt keddi „fáj a fejem" esete: `0.0` bit = 1, `STATE_DAY[0]` = 0 (kedd = a lerakás napja); a következő beszélgetésen, ha a nap-számláló a küszöb alatti, a motor releváns kérdésben utal rá („a kedden fájó fejed, hogy van?").

### 4.4 REMIND[4] — 4 emlékeztető × 6 B

Minden slot: `[óra] [perc] [éé] [hó] [nap] [zászló]` — a zászló: bit0 = aktív, bit1 = napi ismétlés, bit2 = már kiadta. Példa: „emlékeztess 8 órakor, hogy induljak munkába" → `[08] [00] [ma] … [0x01]`. A négy slot egyszerre négy aktív emlékeztetőt enged; a riasztás menete a 12. fejezetben.

### 4.5 Vitakövető (16 B)

Téma-ID (1 B) + álláspont-ID (1 B, a PIOCO nézőpontja) + 14 bájt kulcstoken (a vita fontos szavai) — a motor több körön át ebből építkezik, és a `STANCE` parancs írja. A beszélgetés végi EMEM-mentéssel a vita napokkal később is folytatható.

### 4.6 CHAT bejegyzés-formátum

Minden bejegyzés: `[típus+zászló] [óra] [perc] [tok_lo] [tok_hi] [válaszidő] [hossz] [tartalék]` = 8 bájt fejléc + a tartalom **token-ID-kban** (nem nyers képernyőkódokkal!), átlag ~30 B. Kapacitás: **kb. 40 bejegyzés** (1536 B, 16 B ráhagyással) — a fázis-1-es „30–40 üzenetvált" ígéret ezzel teljesül. A fejléc óra/perc + token-szám + válaszidő mezeje táplálja a képernyő inverz fejléceit (7. fejezet); a válaszidő 0,1 s felbontásban, FRAMES-ből számolva.

## 5. A ZX81 karaktertábla és a 0x76-szabály végrehajtása

### 5.1 Végleges tartományok (forrás-hitelesített)

A ZX81 karakterkészlete 64 glifet tartalmaz a 0x00–0x3F tartományban (szóköz, írásjelek, számok, betűk és a 16 blokkgrafika-karakter); a legfelső bit bekapcsolása (0x80–0xBF) **inverz videót** ad; a `0x76` (118) a **sorzáró (NEWLINE)** kód, saját kijelző-viselkedéssel; a 0x40 fölötti tartomány a ROM **keyword/function tokenjeit** (PRINT, RETURN, GOTO stb.) tartalmazza, nem nyomtatható karaktereket. A biztonsági terv ezért **tartomány szintű**, nem egyes-kód szintű szabályokat ad — a pontos egyes-kód táblázatot a 3. fázis rögzíti a források alapján. Források: Wikipedia „ZX81 character set" (64 glif 0–63, MSB = inverz), Timex Sinclair „ZX-81 Video Display System" (0–63, 118 és 128–191 nem standard; a keyword-tokenek külön kódkészlet).

| Tartomány | Státusz a D_FILE-ban / kiírásban | Használat a PIOCO-ban |
| --- | --- | --- |
| 0x00–0x3F | **Engedélyezett** | minden szöveg, szám, egyszerű grafika |
| 0x40–0x75 | **Tiltott** (ROM keyword-tokenek) | csak a belső Agent-token-tartomány vetítkedik ide — nyomtatás soha |
| 0x76 | **Különleges** (NEWLINE) | kizárólag a képernyőíró sorvégén, soronként egyet |
| 0x77–0x7F | **Tiltott** (vezérlőkód-tartomány) | — |
| 0x80–0xBF | **Engedélyezett** (inverz glifek) | inverz fejlécek, splash, státuszsáv, pörgő karakterek |
| 0xC0–0xFF | **Tiltott** (a keyword-tartomány inverze, nem glif) | — |

### 5.2 A D_FILE elrendezése a saját UI-ban

A motor saját képernyője **nem a gyári dinamikus D_FILE**, hanem rögzített elrendezés: **24 sor × (32 karakter + 1 db `0x76`) = 792 bájt**, a D_FILE-mutató a 0x4200-ra állítva. A zóna maradéka (1024 − 792 = **232 B**) scratch: ideiglenes sorösszeállítás — ide is tilos a `0x76`, hogy egy elcsúszott mutató se fagyaszthassa a gépet.

### 5.3 A print-tölcsér (egyetlen kiírási kapu)

A motorban **egyetlen** rutin írhat a képernyőmemóriába; minden más modul (generátor, UI, rajz, BASIC-listázó, emlékeztető) ezen a „tölcséren" át megy. A tölcsér bájt szintű szűrője: ha a bájt nincs a 0x00–0x3F vagy 0x80–0xBF tartományban, **szóközzel (0x00) helyettesíti** (a sor nem sérül, csak a hibás kód nem kerül a képernyőre). A NEWLINE kiadásához külön, engedélyezett hívás való (sorvég, soronként egyet). Ez a terv egyetlen kapuja: programhiba esetén is legfeljebb szóközök jelenhetnek meg — fagyás nem.

### 5.4 Bitmező → képernyő szabályok

Bináris adat (token-ID, bitmező, cím, CRC) **soha nem kerül nyersen a tölcsérbe**: csak dekódolás és formázás után, számjegyekként/betűkként. A név és a chat-tartalom is szövegként, karakterenkénti szűréssel megy át. A pörgő karakterek effektje kizárólag a biztonságos tartományba szűrt értékeket lépkedi (a generátor minden karakter előtt lefuttatja a tartomány-vizsgálatot).

### 5.5 Önteszt

Bootkor (minden betöltési lánc elején) a motor **scrub tesztet** futtat: végigmegy a saját UI-pufferén, és a tiltott tartományba eső bájtokat szóközzel írja felül, majd a PERSIST CRC-t ellenőrzi. Kézi önteszt `SHIFT+K`: ugyanez plusz a FLAGS/STATE/REMIND slotok érvényességi jele (PASS/FAIL). A teszt eredménye a státuszsorra is kerül, hogy a fejlesztés alatt látható legyen.

## 6. A .T81 sávformátum

### 6.1 Alapok

A `.T81` fájl (az emulátorok, például EightyOne, ZX81 szalagképe) a ZX81 **ROM SAVE rutinja által írt nyers szalagszekvenciákat** tartalmazza — a `.p`/`.81` fájlokhoz hasonlóan. Döntő tény: **a ZX81 ROM LOAD nem ellenőriz checksumot** — a betöltés vakon átveszi az adatot. Ezért a PIOCO **saját CRC-t** visz minden blokkjára. Az impulzusszintű kódolás (pilot/sync hullámforma, bitidőtartamok) véglegesítése a 3. fázisra marad — emulátorral, méréssel.

### 6.2 Blokkok egy `.T81`-en belül

A fejlesztés alatt a **gyári (ROM-kompatibilis) blokkformátum** az alap, elnevezett blokkokkal (név max 8 karakter):

| Sorrend | Név a kazettán | Tartalom / célcím | Méret-plafon |
| --- | --- | --- | ---: |
| 1 | `PIOCOBOOT` | ROM-kompatibilis programblokk (a ROM LOAD kezeli): rövid BASIC + REM-sorba rejtett betöltőgépi kód — splash képernyő, profil-kérdezés, PERSIST írás, majd a további blokkok olvasása | ≤ 2 KB |
| 2 | `PIOCOMOT` | a motor 0x4600-ra | ≤ 3584 |
| 3 | `PIOCOSZO` | szótár + súlytömb 0x5400-ra | ≤ 2304 |
| 4 | `PIOCOALAP` | ALAPMAG 0x6300-ra | ≤ 2048 |
| 5 | `PIOCOPACK` | első témacsomag 0x6B00-ra (a 0.1-ben üres váz) | ≤ 4096 |
| + | `PACK####` | ugyanoda, csere (overlay) | ≤ 4096 |
| M | `SAVEnnnn` | emlékezet-mentés (EMEM) — mindig **új blokk a szalag végén** | ≤ 1536 + 256 |

Minden adatblokkban, a ZX81 blokk-adat kezdete után **4 bájtos saját fejléc** él: `[típus] [verzió] [hossz_lo] [hossz_hi]` (típus: 1 = BOOT, 2 = MOTOR, 3 = SZÓTÁR, 4 = ALAP, 5 = CSOMAG, 6 = MENTÉS; hossz little-endian), majd a hasznos adat, végül **CRC-16** (0x1021, init 0xFFFF) a fejléc + adat felett. A BOOT betöltő kódja a fejléc típusát és a célcímet nézi: **megtagadja** a betöltést, ha a cél metszené a 0x7F00–0x7FFF védett tartományt (D-3.3), vagy CRC hiba van — ilyenkor újrakérést kér.

### 6.3 Multiload-lánc és az emlékezet-mentés

`PIOCOBOOT` (ROM LOAD) → splash + profil → betöltő indul → `PIOCOMOT` → `PIOCOSZO` → `PIOCOALAP` + `PIOCOPACK` → csevegőképernyő. Csomagváltás (`SHIFT+M` menü vagy `LOADPACK` Agent-parancs): prompt → új `PACK####` a CSOMAGTERÜLET-re → folytatás, a RAM-állapot érintetlen. **Kazetta-döntés (lezárva):** középre nem írunk felül — a mentés mindig új blokk a szalag végén, neve `SAVE` + négyjegyű sorszám; visszatöltéskor a motor a **legnagyobb sorszámú ép** (CRC-rendben lévő) blokkot veszi; a régiek a szalagon maradnak. Külön mentőkazetta a 0.1-hez nem kell.

### 6.4 Turbo (gyors szalag)

A terv tartalmazza a gyors szalagrutin specifikációját (sűrűbb impulzusok, saját szinkron), **de a fejlesztés idején konstansszal kikapcsolva** — az emulátorok a gyári formátumot kezelik megbízhatóan. Engedélyezése csak a 4. fázisban, valódi gépen végzett tesztkör után történhet.

## 7. Képernyőtervek (végleges, első változat)

Minden képernyő 32 × 24 karakter; a sorok indexe 0–23. A **plot-terület 64 × 44 pixel** a felső 22 szövegsoron (karakterenként 2×2 pixel) — az alsó 2 sor a prompté marad (ezért a 64×44, nem a lehetséges 64×48-as kiterjesztés; forrás: reids4fun PLOT-mérés). Minden kiírás a print-tölcserén (5.3) át megy.

**K1 — BOOT (splash + profil):** 0–1. sor: pörgő karakter-effekt (biztonságos tartományból); 2–6.: „PIOCO AI" nagy, inverz; 7.: „ZX81 16 KB"; 9.: „SZIA."; 10.: „UTMUTATO? I / N" (I esetén 6 soros rövid segítség); 17.: „NEV?" (ROM INPUT, max 12 karakter, szűrve); 18.: „NEM? F / N"; 19.: „SZUL: EE HH NN"; 20.: „MOST: EE HH NN OO PP"; 21.: „KESZ. BETOLTOM A MOTORT."; 22–23.: „START" villogás, majd Sáv 2. Hibás számnál a sor újra kérdez — nem fagy; üres névvel nem lép tovább.

**K2 — Csevegő:** 0. sor: inverz státusz (`T1-4 R+ OO:PP` — hőmérséklet, reasoning, óra); 1–20.: üzenetek, mindegyik előtt **egy inverz fejlécsor**: `P 12:41 TK214 0.8S` (modell) vagy `N 12:42 TK009  --` (felhasználó, a név első betűje — a CHAT fejlécből, 4.6); 21.: thinking sor (`GONDOLKODOM 2/4` vagy üres); 22–23.: bevitel, a kurzor a 23. sorban. **ROM INPUT döntés:** a motor beállítja a D_FILE-mutatót a saját képernyőre és a 23. sor keretét; ha a ROM rutin a saját UI-t szétírná (a 3. fázis első tesztje méri), vékony saját bevitel lép a helyére — a ROM csak a billentyűolvasást (`KSCAN`) adná. A felhasználó ebből semmit nem lát. Görgetés: `SHIFT+5/6` a `CHAT_VIEW`-t mozgatja, az 1–20. sorok újrarajzolódnak, a beviteli sor nem mozdul.

**K3 — Gondolkodási sáv:** válasz előtt a 21. sorban `GONDOLKODOM: [2/4] SZANDEK… SZO… TUDAS… TERV…` élőben frissül (`SHIFT+9` ki/be); a lépések a reasoning veremből (0x7CE0) jönnek.

**K4 — Rajzmód:** 0. sor: inverz `RAJZ  HOZZAAD`; 1–22. (felső 22 sor): a 64×44-es bitmap megjelenítve; 13–20.: a modell egy sora, mit rajzolt („ABLAK A HAZRA"); alul thinking + bevitel, mint a csevegőn. A vászon bitjei **csak 0→1 irányba** változnak, amíg a felhasználó nem mondja: „töröld a rajzot" (`DRAWCLR`).

**K5 — BASIC nézet:** a program listája sorszámmal (a pufferből, print-tölcserén át); alul a bevitel: `[L]ista  [S]zerk 10 <törzs>  [M]entés`. Szerkesztés: sorszám szerinti csere/beszúrás/törlés (11. fejezet).

**K6 — Emlékeztető-riasztás:** a célidegnél a thinking sor helyén egyszeri inverz sáv: `EMLEKEZTETO: DOLGOZNI` + I/N (elvetem / napi ismétlés). A riasztás menete a 12. fejezetben.

## 8. Vezérlők (végleges)

A mód-kapcsolók saját, nyers billentyűzet-szkenneléssel működnek (a pontos port-címek a 3. fázis ROM-listájából), a szövegbevitel a **ROM INPUT rutinja**, karakteres módban — így a `SHIFT+1..4` újraértelmezése (hőmérséklet) nem ütközik a ROM keyword-kiosztásával, mert a mód-billentyűket a saját szkennelőről tudjuk, nem a ROM-ról.

| Billentyű | Funkció | Forrás |
| --- | --- | --- |
| `SHIFT+1..4` | Hőmérséklet: 1 = tényszerű … 4 = kreatív | mesterprompt (kötelező) |
| `SHIFT+9` | Reasoning-megjelenítés ki/be | mesterprompt (kötelező) |
| `SHIFT+5` / `SHIFT+6` | Beszélgetés görgetése vissza / előre | mesterprompt (kötelező) |
| `SHIFT+S` | Mentés kazettára (`SAVEnnnn` a szalag végére) | mesterprompt (kötelező) |
| `SHIFT+SPACE` | Válasz / gondolkodás megszakítása | mesterprompt (kötelező) |
| `SHIFT+D` | Rajzmód ki/be (K4) | új (D-8.1) |
| `SHIFT+B` | BASIC nézet ki/be (K5) | új (D-8.1) |
| `SHIFT+M` | Csomagmenü (overlay-választás) | új (D-8.1) |
| `SHIFT+K` | Karakter-/CRC-önteszt (5.5) | új (D-8.1) |
| `SHIFT+T` | Turbo ki/be — **fejlesztői**, alapból OFF | új (D-8.1) |

## 9. Agent-parancsnyelv

### 9.1 Elvek

Az Agent-parancsok **belső tokenek** (ID 0x10–0x1F), a gondolkodási fázis bocsátja ki őket a `[THINK_START]` … `[THINK_END]` blokkban; a felhasználó sosem gépeli őket — a szövegéből következnek. A tartomány szándékosan a **képernyőre nem kerülhető** kódterületen (5.1) van: egy hibás kiírási útvonal is csak szóközt adna. A generálás végén **egy** parancs hajtódik végre (9.3), majd a válasz vagy a módváltás következik. Ha a reasoning nincs bekapcsolva (`SHIFT+9`), a `MOOD` és a többlépéses tervezés kimarad, de a `SETBIT` / `REMIND` / `DRAW` / `BASIC` akkor is lefut — különben a gép „buta parancsértelmezővé" esne vissza, amit a mesterprompt tilt.

### 9.2 A 14 parancs

| Kód | Parancs | Mikor | Hatás |
| ---: | --- | --- | --- |
| 0 | `SAY` | sima kérdés, vélemény | szöveg generálás (váz + súlyok) |
| 1 | `ASK` | hiányzó adat (név, óra, „még fáj?") | rövid kérdés, várakozás |
| 2 | `SETBIT` | „fáj a fejem", „már nem fáj" | STATE bit + `STATE_DAY` írása/nullázása |
| 3 | `REMIND` | „emlékeztess 8-kor…" | REMIND slot, ha van szabad hely |
| 4 | `DRAW` | „rajzolj házat / ablakot / fát" | rajzelem OR-olása a vászonra (10. fejezet) |
| 5 | `DRAWCLR` | „töröld a rajzot" | vászon nullázása (egyetlen törlő út) |
| 6 | `BASIC` | „írj programot…" | program-puffer feltöltése sorokkal |
| 7 | `BASICEDIT` | „a 20-as sort cseréld…" | sorszám szerinti csere/beszúrás/törlés |
| 8 | `MOOD` | ingerült, dicsérő, vitázó mondat | hangulat-állapot + stílusos `SAY` |
| 9 | `STANCE` | „PC jobb, mint a ZX81" | vitakövető írása — több körön át megtartott álláspont |
| 10 | `LOADPACK` | „beszéljünk csillagokról" | csomagmenü / overlay-betöltés kérése |
| 11 | `SAVE` | „mentsd el" | `SAVEnnnn` blokk a szalag végére |
| 12 | `WAKE` | (a motor adja ki) | emlékeztető-riasztás (K6), aktív bit törlése |
| 13 | `STOP` | `SHIFT+SPACE` | generálás megszakítása, a fél sor törlése |

(14 parancs, 16 slotból 2 tartalék — a 3. fázisban bővíthető.)

### 9.3 Példafolyamok

- *„Emlékeztess 8 órakor, hogy induljak munkába."* → `[THINK_START]` szándék = emlékeztető, idő = 08:00, üzenet = dolgozni → `REMIND 8 0 DOLGOZNI` → válaszváz: „Rendben, <NÉV>, <dátum> 8:00-kor emlékeztetlek, hogy indulj munkába." → `[THINK_END]`.
- *„Rajzolj egy házat, majd adj hozzá egy ablakot!"* → `DRAW HAZ` + válaszváz → később: `DRAW ABLAK` — a vászon nem törlődik, az ablak a ház fix területébe OR-olódik.
- *„PC is better than ZX81."* → `MOOD VITA` + `STANCE TEMA_PC 1` → a következő körök a vita-blokk tokenjeiből építkeznek; a motor a ZX81 mellett áll ki, az érvekre visszautal.
- *„You are so slow!"* → `MOOD INGERULT` + `SAY` a 3,25 MHz-et említő vázzal; *„You are a genius!"* → `MOOD HUMOROS` + önironikus váz a 16 KB-ra utalva.

## 10. Rajzolás alrendszer

A 352 bájtos bitmap-vászon (0x7B00) 44 plot-sorát három zónára osztjuk: **ég** (0–15), **táj/objektum** (16–35), **előtér/alap** (36–43). A rajzelemek **fix téglalap-területekre** OR-olódnak a vászonra (a bitcsere csak 0→1 irányba mehet, ezért semmi sem törölhető véletlenül): ház x16–47, y16–40; ablak x22–30, y22–30; ajtó; fa x50–60, y18–40; nap; felhő; kerítés — mindegyik 1 bájtos elem-ID alatt, paraméterezve (méret 1–3). Törlés **csak** a `DRAWCLR` parancssal. A vászon tartalma az EMEM-mentésbe opcionálisan bekerül (zászlóval), így a rajz beszélgetések között is megmarad.

## 11. BASIC alrendszer

A program-puffer (256 B, 0x7D00) saját kompakt formátumban tárol: `[sorszám 2 B, 1–999] [hossz 1 B] [tokenizált szöveg]` soronként — átlag ~15–16 B/sor, azaz **kb. 14–16 rövid sor**. A tokenizáló BASIC-kulcsszó tokenekkel bővül (PRINT, INPUT, FOR, IF, GOTO stb. — saját ID-k, a ROM keyword-kódjaitól függetlenek), a listázás dekódolva, print-tölcserén át történik. Szerkesztési műveletek (a ZX81 sorszámozás előnyeit kihasználva): **csere** (azonos sorszám felülírja a sort), **beszúrás** (a motor a sorszám szerinti helyre csúsztat), **törlés** (hossz = 0, majd tömörítés), **szövegcsere** egy soron belül; a puffer sorszám-rendje mindig rendezett. Betelés esetén a motor egy soros üzenetet ad (K5), és nem ír tovább; a D-2.1 szerint szalag-mentést vagy csomagterület-farot ajánl fel. A futtatás (a program átadása a ROM BASIC-nek) nyitott kérdés marad a 3. fázisra — addig az írás, listázás és mentés támogatott.

## 12. Emlékeztető-modul

Az időzítés alapja a ROM **50 Hz-es FRAMES rendszerváltozója** (kétbájtos számláló; a pontos címe a kódba a 3. fázisban, a ROM-listából kerül). A motor a BOOT-kor megadott órát tekinti nullának, `FRAME_ANCHOR` (2.2) rögzíti az utolsó perclépés FRAMES-értékét, és percenként lépteti a `CLOCK_H:CLOCK_M`-et. Amikor egy `REMIND` slot célideje elérkezik, a motor `WAKE`-t ad ki (K6), és a slot aktív bitjét törli (napi ismétlésnél másnapra újraszámolja). **D-12.1 döntés (SLOW):** a 0.1 **csak SLOW módban fut** — FAST alatt a képernyő úgyis kikapcsol, a csevegőnek nincs értelme; ha a gép FAST-ba esne, a motor visszakapcsol SLOW-ra, és a percet nem lépteti addig, amíg az óra újra stabil. Így nem ígérünk másodperc-pontos ébresztést FAST mellett. A frame-számítás ellenőrzött: egy teljes nap 4 320 000 frame, ami a 3 bájtos belső számlálóba (max 16 777 215) bőven belefér.

## 13. A generálási lánc futásidőben

A 0.1 verzió tényleges futása lépésenként:

1. INPUT sor → csak 0x00–0x3F karakterek jutnak a token-pufferbe (128 B, 2.3).
2. Tokenizálás: szótár-hossz szerinti leghosszabb illesztés; a maradék betűnként (0xF0–0xFF).
3. Reasoning (ha bekapcsolva): **legfeljebb 4 lépés** a thinking sorban (`SZANDEK`, `SZO`, `TUDAS`, `TERV`); közben `SHIFT+SPACE` megszakít.
4. **Egy** Agent-parancs kiválasztása és végrehajtása (9.2).
5. `SAY`/`MOOD` esetén token-kiválasztás a 4 bites súlyokból — a hőmérséklet top-k leképezése:
   - hőmérséklet 1: mindig a legnagyobb súlyú következő token;
   - 2: az első 2 közül — a Z80 **R regiszter** egy bitje dönt;
   - 3: az első 4 közül — R + **FRAMES** alsó 2 bitje;
   - 4: az első 8 közül — ugyanez.
6. Toldalék-token a magyar egyeztető táblából (a szótár része, nem külön memória).
7. A válasz **legfeljebb 4 sor** — utána `TOVABB?` lapozási kérdés (a képernyőn nincs hely többre).
8. A bejegyzés a CHAT körbufferbe kerül: fejléc (óra, token, idő) + a szöveg **token-ID-kban** (4.6).

Ismeretlen szóra nem mond „nem értem" sablont: betűnként beolvassa (3.1), és a legközelebbi tudás-tokennel válaszol, vagy `ASK`-kal rákérdez.

## 14. Fázisterv frissítése, a 3. fázis szabályai és első szeletei

### 14.1 Fázistáblázat

| Fázis | Cél | Kimenet | Állapot |
| --- | --- | --- | --- |
| 1. Ötlet és koncepció | architektúra, realitásvizsgálat | `docs/fazis-1-koncepcio.md` | ✅ |
| 2. Tervezés, működés és dizájn | végleges memóriatérkép, bitmezők, karaktertábla, sávformátum, képernyők, vezérlők, Agent-nyelv, emlékeztető | ez a dokumentum | ✅ |
| 3. Kódolás és csomagolás | Z80 motor, PC-s eszközök, első futó `.T81` (turbo OFF) | `motor/`, `eszkozok/`, `kazetta/pioco-0.1.t81` | ⏳ következik |
| 4. Tudás, tréning, tesztelés | alaptudás + témacsomagok, emulátoros és valódi gépi ellenőrzés | `tudas/`, `kazetta/*.t81`, tesztnapló | ⬜ |

### 14.2 Amit a 3. fázis nem dönt újra

- A címtartományok határai (mérés kényszerítheti elmozdításukat — a PERSIST egyetlen ismert kivétellel: a D-3.3 korrekció a REM-boot mérete miatt a 0x7F00-ra tette).
- XOR 0xA5 maszk + 76-kerülő minden bitmezőn; CRC-16 (0x1021, init 0xFFFF) minden blokkon és a PERSIST-en.
- Képernyőre csak 0x00–0x3F és 0x80–0xBF; sorvég 0x76 csak a képernyőírótól, soronként egyet; minden kiírás a print-tölcserén át.
- Turbo ki a fejlesztés alatt; mentés csak szalagvégre, `SAVEnnnn`.
- Vászon csak hozzáad (OR); törlés csak `DRAWCLR`.
- Futás csak SLOW-ban; négy emlékeztető; 256 bájtos BASIC-puffer; 12 karakteres név.

### 14.3 A 3. fázisra maradó nyitott döntések

1. **Impulzusszintű szalag-kódolás** — pilot/sync/bitidőtartamok emulátorral méréssel; a blokkszintű formátum (6.2) végleges.
2. **A sysvars-farok pontos kezdőcíme és a FRAMES címe** — ROM-listából (2.2, 12. fejezet).
3. **ROM INPUT kompatibilitás mérése** — első teszt dönt: marad a ROM INPUT vagy a `KSCAN`-alapú vékony beviteli réteg (K2).
4. **BASIC futtatás-átlépés** — a saját UI-ból a ROM szerkesztőjébe (11. fejezet).
5. **Szótár-lefedettség mérése** — 224 token tényleges lefedettsége korpuszon; esetenként csomagterületi szó-bővítés.
6. **Motor méretmérése** — a 3,5 KB-os keret betöltése a végleges kóddal; ha szűkös, a fázis-1-es átcsoportosítási terv (CHAT fara, TARTALÉK) lép életbe.

### 14.4 A 3. fázis első szeletei (hogy mindig legyen mit futtatni)

Nem az egész motor egyszerre — sorrend:

1. BOOT képernyő + profil-kérdések + PERSIST írás, önálló `.T81`, emulátorban.
2. Üres csevegőkeret: fejlécek, INPUT, `SHIFT+1..4` és `SHIFT+9` a státuszsoron.
3. Tokenizáló + egy `SAY`, ami az ALAPMAG-ból rak össze 1–2 sort.
4. `SETBIT` + elavulás, `REMIND`, `DRAW` a három fix alakzattal, `BASIC` egy 4 soros programmal.
5. Mentés / visszatöltés a szalag végéről (`SAVEnnnn`).

Minden szelet után egy `.T81` a `kazetta/` alatt és egy sor a fejlesztési naplóban: betöltött-e, fagyott-e, megmaradt-e a PERSIST a második sáv után.

---

*Források (a platformtények ellenőrzéséhez): Wikipedia „ZX81 character set" (64 glif 0–63; MSB = inverz); Timex Sinclair „ZX-81 Video Display System, Part 1" (CHR$ 0–63, 118 és 128–191 nem standard; keyword-tokenek); reids4fun „Exploring Chunky Graphics" (PLOT 64×44 a felső 22 sorban; 48 az alsó 2 sorral); sebastien.andrivet.com „My first computer: Sinclair ZX81" (program/D_FILE 16509-től; .p/.81 = nyers SAVE-adatok); ZX81 ROM listing (FRAMES kétbájtos rendszerváltozó). Minden bontást Python-számítás ellenőrzött: `scripts/pio_f2_calc.py`.*

*Készült: 2026-11-21 · GLM (Z.ai) · 2. fázis — a „Tervezés, működés és dizájn" dokumentuma.*

