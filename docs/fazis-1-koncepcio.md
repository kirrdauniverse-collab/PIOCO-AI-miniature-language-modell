# PIOCO AI — 1. fázis: Ötlet és koncepció

**Projekt:** PIOCO AI miniature language modell
**Célplatform:** Sinclair ZX81 · 16 KB RAM · Z80 @ 3,25 MHz · egyetlen, több betöltési sávot tartalmazó `.T81` kazettafájl
**Dátum:** 2026-11-21
**Fejlesztői munkaterület:** `GLM/` (helyi) · **Repó:** `github.com/kirrdauniverse-collab/PIOCO-AI-miniature-language-modell`

> Elnevezési döntés: a mesterprompt „Pico AI”-ként hivatkozik a modellre, a repó neve viszont PIOCO. A **PIOCO AI**-t tekintjük hivatalos névnek — a motorban és az eszközökben egyetlen konstans dönt róla, bármikor cserélhető.

---

## 1. A koncepció egy mondatban

A PIOCO AI egy miniatűr, **valóban generáló** nyelvi modell a Sinclair ZX81-en belül: nem beégetett mondatokat ad vissza, hanem a bejövő szöveget **tokenizálja**, több lépéses **belső gondolkodási folyamaton** (szándék → entitások → tudáslekérés → választerv) visz át, majd a tömörített tudásbázisra és a saját mini nyelvi modelljére (4 bites egész súlyokkal) támaszkodva **maga szerkeszti, toldalékolja és állítja össze a választ**, hőmérséklet-vezérléssel, állapotos emlékezettel és kazettás tudáscsomagokkal — mindezt a 16 KB-os RAM-ban. Emellett **rajzol** (64×44-es plot-vásznon, hozzáadó módban), **rövid ZX81 BASIC programot ír és utólag módosít**, és **időzített emlékeztetőt** tart a FRAMES-számlálóval.

## 2. Realitásvizsgálat: mi fér be a 16 KB-ba?

### 2.1 Fogalmak zsargon nélkül — motor vs. tudástár

A teljes rendszer két, éles különválasztandó részből áll: a **motor (keretprogram)** a gépi kód, ami mindent mozgat (tokenizál, gondolkodik, generál, képernyőt rajzol, szalagot kezel); a **tudástár / memória** viszont az adat, amit a motor feldolgoz (szótár, súlyok, tudáscsomagok, chat, bitek). A későbbi fejezetek minden döntését érdemes ezen a szemüvegen át olvasni: a motor „ami dolgozik”, a tudástár „amin dolgozik”. A kiegészített mesterprompt négy kulcsfogalmát a PIOCO-megvalósítás így értelmezi:

- **Token** — a szöveg feldarabolt építőköve (karakter, gyakori szótag/toldalék, gyakori szó vagy vezérlőjel). A cél, hogy ne betűnként „pötyögjön” a modell (az elviszi a kapacitást), és ne is csak előre megírt mondatokat mondogat, hanem szótagokból/szóelemekből építkezve rakja össze a saját megfogalmazását. A PIOCO szótára kb. **400–460 token**, minden token 1 bájt.
- **Paraméter és weight (súly)** — a paraméter a modell tanulható „állítócsavarja”/kapcsolata, a súly az adott kapcsolat erőssége (pozitív vagy negatív irányú ráhatás). Mivel a ZX81-ben nincs lebegőpontos gyorsító, a PIOCO súlyai **egész számok, 4 bites kvantálással (`-8..+7`)**, és **1 bájton 2 súly** csomagolva tárolódik; a tréning a PC-n figyelembe veszi ezt a szűkítést, hogy a kvantálás után ne essen szét a modell.
- **Temperature (hőmérséklet)** — azt szabályozza, mennyire ragaszkodik a modell a legesélyesebb folytatáshoz (`SHIFT+1..4`), vagy merjen-e váratlanabb, játékosabb megoldást választani — anélkül, hogy szétesne a válasz. A véletlenség forrása a Z80 **`R` regisztere** és a ROM **50 Hz-es `FRAMES` számlálója** (egészszámos, gyors, nincs külön hardver kellék).
- **Reasoning (gondolkodás)** — nem azonnali válaszadás, hanem belső „elő-feldolgozó” lépés: a motor a `[THINK_START]` és `[THINK_END]` jelek között a rejtett munkaállapotában forgat meg kulcsszavakat, asszociációkat és állapotokat, mielőtt kiírja a tényleges választ vagy végrehajt egy Agent-parancsot. A lépések a `GONDOLKODOM…` sávban élőben követhetők, SHIFT+9-gyel ki/be kapcsolható.

### 2.2 Kiindulási adatok

| Paraméter | Érték | Következmény a tervezésre |
| --- | --- | --- |
| CPU | Z80 @ 3,25 MHz | minden számítás egészszámos és táblázatos; bonyolult lebegőpontos művelet nincs |
| RAM | 16 KB (0x4000–0x7FFF) | a rendszerváltozók és a képernyő (D_FILE ≈ 793 bájt) levonandó a 16 KB-ból |
| ROM | 8 KB BASIC | a `PRINT`, `INPUT` és a szalagkezelő rutinok újrahasznosíthatók — nem kell újraírni |
| Háttértár | magnókazetta (`.T81`) | a tudás és az emlékezet „virtuálisan” nagy lehet: sávról cserélhető (multiload) |
| Képernyő | 32 × 24 karakter | tömör, rövid válaszok; görgetés; inverz fejlécek és státuszsáv |

### 2.3 Mit nem ígérünk (és miért)

Egy mai, valódi neurális nyelvi modellnek legalább tízmillió paramétere van; már 1 millió paraméter is kb. 1 MB 8 bites tárolással — ez a ZX81 teljes címtérének 64-szerese. Neurális háló tehát **fizikailag nem fér be**. A PIOCO ezért nem „csökkentett LLM”, hanem **miniatűr, valódi generálású nyelvi motor**: statisztikai nyelvi modell (n-gram) + magyar toldalékolás + váz-alapú szövegszintézis + indexelt tudásbázis. Az elvárt hatás ugyanaz, amit a mesterprompt kér: a válasz **futásidőben, újrakomponálva** születik, nem visszakeresett mondat.

### 2.4 Mit tudunk — a generálási lánc lépésről lépésre

1. **Tokenizáló** — a beírt szöveget szóalap- és toldaléktokenekre bontja. A szótár kb. **400–460 token** (gyakori szavak + magyar toldalékok: `-ban/-ben`, `-nak/-nek`, `-ra/-re`, `-val/-vel`, `-t`, `-ok/-ek/-ök` stb.), minden token 1 bájt (0–255). Az ismeretlen szó betű-tokenekre bontható — a modell tehát **mindent el tud olvasni**, nem csak a szótárban lévőt. Ez az „agglutináló nyelv kompromisszum”: kevés tárolóból nagy lefedettség.
2. **Belső gondolkodási fázis (reasoning)** — 3–5 lépés a `[THINK_START]` … `[THINK_END]` blokkban: szándékfelismerés → kulcsentitások (név, hely, téma, idő, **hangulat**) → tudáslekérés az indexelt tudásbázisból → választerv. A lépések élőben láthatók a `GONDOLKODOM…` sávban, SHIFT+9-gyel ki/be kapcsolható.
3. **Generálás** — a választervet a mini nyelvi modell (2–3 szó kontextusú n-gram, **4 bites egész súlyokkal, `-8..+7`, bájtonként kettő csomagolva**; a súlyokat a PC-s tréning kvantálja) és **vázak** (behelyettesíthető résekkel rendelkező mondatkeretek: számok, nevek, dátumok) együtt építik: a kimenet saját sorrendben, toldalékolva, behelyettesítve **újrakomponált** szöveg.
4. **Hőmérséklet** — a választási véletlen vezérlése (top-k szűkítés/kiszélesítés): 1 = tényszerű, 4 = kreatív (`SHIFT+1..4`). A véletlen forrása a Z80 `R` regisztere + a `FRAMES` (50 Hz) számláló — nélkülözhetetlen akkor is, amikor a modell „kockázatosabb” folytatást választ.
5. **Állapotfrissítés** — a beszélgetésben előkerülő kétállapotú tények bitekre kerülnek (pl. „fáj a fej” = 1), dátumbélyeggel; elavuláskor a motor rákérdez, majd új információval írja felül (lásd 6. szakasz).

### 2.5 Fő kompromisszumok egy helyen

| Igény | PIOCO-megoldás 16 KB-on | Amit elengedünk |
| --- | --- | --- |
| Mély, széles világtudás | tömörített, indexelt tudáscsomagok kazettáról (multiload) | csak az él, ami éppen fel van töltve |
| Hosszú beszélgetés-emlékezet | tömörített chat (kb. 30–40 üzenetvált) + szalag-mentés | a legrégebbi rész szalagra gördül |
| Tanulás futásidőben | a „tréning” PC-n fut, eredménye kazettára kerül; a gépen csak állapotok/bitek frissülnek | a modell súlyai nem változnak a ZX81-en |
| Szabad szöveg-értés | tokenizáló + kulcsszó/entitás-felismerés | bonyolult, többszörösen alárendelt mondatok félreérthetők |
| Hosszú válaszok | tömör, 4–6 soros válasz, lapozható folytatás | a képernyő (32×24) és a RAM korlátja |

## 3. Architektúra — modultérkép

```
            ┌─────────────────────────────────────────────────────┐
            │                   .T81 KAZETTA                      │
            │ [S1 BOOT] [S2 MOTOR+ALAPTUDÁS] [S3..N OVERLAY]      │
            │ [M EMLÉKEZET-MENTÉS — dátumbélyegzett blokkok]      │
            └──────────────────────────┬──────────────────────────┘
                                       │ multiload — célzott címekre tölt
┌──────────────────────────────────────▼──────────────────────────────┐
│                 ZX81 · 16 KB RAM (0x4000–0x7FFF)                    │
│  SYSVARS │ PROFIL (védett) │ D_FILE/UI │ MOTOR │ SZÓTÁR │ CHAT      │
│            ALAPMAG │ CSOMAGTERÜLET │ MUNKATERÜLET │ TARTALÉK        │
└─────────────────────────────────────────────────────────────────────┘
```

| Modul | Feladat |
| --- | --- |
| INDÍTÓ (BOOT, Sáv 1) | splash kép + pörgő karakter-effekt, név, üdvözlet, útmutató-kérdés; profil-kérdezés (pontos dátum, óra, név, nem, születési adat); mentés a védett PROFIL blokkba |
| MOTOR | tokenizáló, generátor (4 bites súlyokkal), reasoning ([THINK_START]/[THINK_END]), hőmérséklet (R+FRAMES), rajzolás, BASIC-írás, UI, szalag-I/O |
| SZÓTÁR | token ↔ szöveg táblák + toldalékkódok (kb. 400–460 token) + a kvantált súlytömb (4 bit/súly) |
| TUDÁS | ALAPMAG (mindig rezidens) + CSOMAGTERÜLET (témacsomagok / overlay-k cserélődnek rajta) |
| EMLÉKEZET | chat history + bitmezők + dátumbélyegek + viták álláspontja + elavulás-kezelés |
| PROFIL (PERSIST_BLOCK) | tartós, védett blokk: név, nem (1 bit), születési adat, dátum/óra, beállítások — a multiload sávok átugorják |

## 4. Memóriatérkép-javaslat (0x4000–0x7FFF, pontos bájtösszegekkel)

A bontás Python-számítással ellenőrzött: a zónák **folytonosan** lefedik a 0x4000–0x7FFF területet, összesen pontosan **16 384 bájtot**.

| Címtartomány | Zóna | Méret | Megjegyzés |
| --- | --- | ---: | --- |
| 0x4000–0x40FF | ROM-kompatibilis rendszerváltozók + saját állapotbájtok | 256 B | a ROM `INPUT`/`PRINT` rutinjai ezt igénylik |
| 0x4100–0x41FF | **PROFIL — tartós, védett blokk (PERSIST_BLOCK)** | 256 B | név, nem (1 bit), születési adat, dátum/óra, beállítások, állapotbitek; a multiload sávok **átugorják / soha nem írják** |
| 0x4200–0x45FF | D_FILE + UI puffer | 1024 B | felső harmada munkaterületként is: effektek (pörgő karakterek), scratch |
| 0x4600–0x53FF | MOTOR (kód) | 3584 B | tokenizáló, generátor, reasoning, rajz/BASIC, UI, szalag-I/O |
| 0x5400–0x5CFF | SZÓTÁR + tokenizáló táblák + súlytömb | 2304 B | kb. 400–460 token (1 B/token) + 4 bites súlyok, bájtonként 2 |
| 0x5D00–0x62FF | CHAT history | 1536 B | tömörített üzenetek, görgetés SHIFT+5/6 |
| 0x6300–0x6AFF | ALAPMAG (rezidens tudás) | 2048 B | az alaptudás magja mindig bent marad |
| 0x6B00–0x7AFF | CSOMAGTERÜLET (témacsomagok) | 4096 B | a témacsomagok itt cserélődnek kazettáról |
| 0x7B00–0x7DFF | MUNKATERÜLET | 768 B | token buffer, reasoning stack, rajzvászon (64×44 bit = 352 B), BASIC-puffer |
| 0x7E00–0x7FFF | TARTALÉK | 512 B | utólagos bővítés: kb. 56 B / modul (9 modul mellett) |
| **Összesen** | | **16 384 B** | 16,0 KB — pontosan lefedve |

### 4.1 A kért arányok vs. a valóság — a 16 KB „szorításának” helyei

Ez az a pont, ahol a mesterprompt irányadó arányai (motor 3–5 KB, szótár 2–3 KB, chat 2–3 KB, tudás 7–10 KB) összesen **14–21 KB**-ot adnak ki, ami a képernyővel és a rendszerváltozókkal együtt **nem fér el egyben** a 16 KB-ban. A javasolt megoldás:

- **Motor 3–5 KB → 3,5 KB** ✓ belefér.
- **Szótár 2–3 KB → 2,3 KB** ✓ belefér (kb. 400–460 token; a betű-tokenek visszaadják a lefedettséget).
- **Chat 2–3 KB → 1,5 KB** ⚠ csökkentve: a képernyő (kb. 1 KB) és a rendszerváltozók miatt nem fér be több. Kompenzáció: szalagra mentés (`SHIFT+S`) + görgetés, így a beszélgetés nem vész el, csak nem mind rezidens.
- **Tudás 7–10 KB → 6 KB rezidens** ⚠ (2 KB mindig bent maradó ALAPMAG + 4 KB cserélhető CSOMAGTERÜLET). A „hiányzó” 1–4 KB nem tényleges veszteség: a multiload miatt a tudásbázis **virtuálisan korlátlan** — a témák szalagról cserélődnek, szalagidő-arányosan.
- **Bővítési tartalék:** minden modul mellett 50–150 B igény a TARTALÉK zónából (512 B) és a zónák belső ráhagyásából fedezhető.

Ha a gyakorlatban (3. fázis, mérés után) mégis kiderül, hogy a motor vagy a szótár szűkös, a CHAT (–0,5 KB) és a MUNKATERÜLET (–0,25 KB) zónákból átcsoportosítható hely anélkül, hogy a védett PROFIL blokkot bármelyik érintené.

## 5. .T81 sávstruktúra (multiload)

A kazetta **háttérként** működik: semmit nem kell egyszerre bezsúfolni a RAM-ba. A sávok célzott címekre töltenek, ezért a korábban beolvasott, tartós adatok (PROFIL blokk) érintetlenek maradnak.

| Sáv | Tartalom | Viselkedés betöltés után |
| --- | --- | --- |
| **S1 — INDÍTÓ (BOOT)** | splash kép + pörgő karakter-effekt, modellnév, üdvözlet, útmutató-kérdés (I/N), profil-kérdezés: pontos dátum, óra, név, nem, születési adat | a PROFIL/PERSIST_BLOCK blokkba ment (0x4100–0x41FF), majd kéri a Sáv 2-t |
| **S2 — MOTOR + ALAPTUDÁS** | motor (3,5 KB) + szótár és súlytömb (2,3 KB) + ALAPMAG (2 KB) + a CSOMAGTERÜLET kezdő tartalma | célzott címekre tölt — a PERSIST_BLOCK-ot **átugorja** —, elindítja a csevegőképernyőt |
| **S3..N — TÉMACSOMAGOK (overlay-k)** | tudomány, gasztronómia, egészség, szórakozás, retro korszak, retro technológia, jövőkutatás, tanulás, hobbi, csillagászat, irodalom, filmek, hírességek, művészet, munka, UFO stb. | a CSOMAGTERÜLET (0x6B00–0x7AFF) felülírásával cserélődnek; a motor menüből / parancsból kéri őket |
| **M — EMLÉKEZET-MENTÉS** | chat history + állapotbitek + beállítások, dátumbélyeggel | visszatöltéskor a **legfrissebb** blokk nyer |

### 5.1 „Felülírás” a kazettán — műszaki korlát és megoldás

Fontos, őszinte korlát: egy magnókazetta **középre nem írható felül biztonságosan** — a felvétel fizikailag új felvétel. Javasolt megoldás: az emlékezet-mentés mindig a **szalag végére** kerül (hozzáfűzés), minden blokk dátumbélyeget kap, és a motor visszatöltéskor a **legfrissebb** érvényes blokkot választja; a régiek egyszerűen elavulnak. Alternatíva: külön „MENTÉS” kazetta. (Ezt a döntést a 2. fázisban véglegesítjük — nincs hatással a memóriatérképre.)

## 6. Karakter- és bitbiztonság (a „0x76-szabály”)

- **Képernyőmemória (D_FILE):** kizárólag a sima karaktertartomány (**0x00–0x3F**) és az inverz/grafikatartomány (**0x80–0xBF**) kerülhet bele; a `0x76` (sorzáró, NEWLINE) csak a print-rutintól, sorvégen; minden más kód (0x40–0x75, 0x77–0xFF — a ROM parancs- és vezérlőkód-tartományai, pl. `PRINT`, `RETURN`, `GOTO`) **tiltott** a képernyőmemóriában. A pontos karaktertáblázat a 2. fázisban véglegesül.
- **Bináris adat soha nem kerül nyersen a képernyőbe:** bitmezők, token-ID-k, címek csak dekódolás + formázás után, szövegként jelennek meg. A D_FILE felső harmada csak akkor munkaterület, ha rá e szabály érvényesül (scratch puffer, nem megjelenített adat).
- **„Pörgő karakterek” effekt** (a kiegészítés kérése): a splash és a `GONDOLKODOM…` sáv klasszikus futtató/pörgő karakter-látványa **kizárólag a biztonságos tartományba (0x00–0x3F és 0x80–0xBF) szűrt értékekkel** forgatható; az effekt generator minden karaktere előtt lefut a tartomány-vizsgálat, így a látvány sosem írhat `0x76`-ot vagy parancskódot a képernyőmemóriába.
- **Bitmezők (1 bit / tulajdonság), irányadó bontás:**
  - `PROFIL` állapotbájt: bit0 = nem (0 = férfi, 1 = nő); bit1–2 = korosztály (00 = gyerek, 01 = fiatal, 10 = felnőtt, 11 = 60+); bit3 = útmutatót kért; bit4 = reasoning alapból bekapcsolva; bit5–7 = tartalék.
  - `ÁLLAPOT` bájtok: pl. bit0 = fáj a fej, bit1 = hátfájás, … külön dátumbájtokkal (év+hónap+nap tömörítve).
  - Tárolás **XOR-maszkkal** (pl. 0xA5): a tárolt bájt véletlenül sem állhat össze `0x76`-á vagy más veszélyes kóddá; a bitek kibontása csak a munkaterületen történik.
- **Elavulás-kezelés** (a mesterprompt példája): „kedden fáj a fejem” → 1-es bit + dátumbélyeg, mentés a kazettára; későbbi beszélgetésben, ha releváns, a PIOCO rákérdez; ha a betöltés óta eltelt napok száma meghaladja a küszöböt (pl. 7 nap), az állapot **elavultként** kezelődik: rákérdez, majd nullázza / új infóval írja felül.

## 7. Viselkedési képességek és Agent-példák (a kiegészítés alapján)

A kiegészített mesterprompt konkrét viselkedési eseteket ír elő — ezek a „motor intelligenciájának” legkeményebb próbái, mert nem sablonválaszt, hanem állapotos, saját megfogalmazású reakciót várnak. Mindegyik hátterében a 2.4 fejezet generálási lánca áll: a reasoning lépései (szándék, entitások, **hangulat**, álláspont) döntenek arról, mit és hogyan mondjon.

### 7.1 Hangulat, humor és vita

Ha a felhasználó ingerülten szól be („you are so slow!”), a reasoning `[THINK_START]` blokkjában felismeri a **feszültség/lassúság** témát, és saját megfogalmazásban reagál — például a 3,25 MHz-es órajelre vagy a türelemre utalva —, nem beégetett udvarias pózzal. Humorral és iróniával („you are a genius!”) szemben önironikus, csipkelődő választ ad, a 16 KB-os korlátaira reflektálva: ezt a vázsablonok „hangulatparamétere” és a hőmérséklet 3–4-es fokozata együtt érik el. Vitánál („PC is better than ZX81”) a motor az EMLÉKEZET zónában **vitakövetet** tart: téma + a PIOCO álláspontja + a felhasználó érveinek váza; több körön át ugyanarra az álláspontra épít, és a korábbi körökben elhangzott érvekre visszautalhat — ez az állapotos generálás legszemléletesebb haszna.

### 7.2 Rajzolás 64×44-en, hozzáadó módban

A plot-vászon **64×44 bit** (44 sor × 8 bájt = **352 bájt** bitmap), a MUNKATERÜLET zónában él, és a képernyő felső sávjába renderelődik. Kérésre megrajzolja a házat, és — a kiegészítés előírása szerint — **soha nem törli** a meglévő rajzot: új elemek (ablak, fa) fix vászon-zónákba (pl. ég/talaj/objektum-sávok) illeszkednek, „hozzáadó rajzmódban”, felülírás nélkül. A vászon tartalma szalagra is menthető az emlékezet-mentés blokkjában.

### 7.3 BASIC program írása és utólagos módosítása

A motor rövid ZX81 BASIC programokat is állít elő (a tokenizáló BASIC-kulcsszó tokenekkel bővül), és a ZX81 sorszámozásának előnyeit kihasználva **utólag módosítja** őket: sorszám szerinti csere, beszúrás, szövegcsere, logikaváltás — a meglévő program sorainak újraírásával, nem teljes újraképzéssel. A program-puffer a MUNKATERÜLET maradék területén él; a hosszabb programok kezelése (és a csomagterület szabad faraként való tárolás) a 2. fázis nyitott döntése.

### 7.4 Időzített emlékeztetők

„Emlékeztess 8 órakor, hogy induljak munkába” — a motor az emlékeztetőt óra-perc célpontként rögzíti (2 bájt + 1-es aktív bit), és a ROM **50 Hz-es FRAMES számlálójához** viszonyítva jelzen a megadott időpontban (a `FAST`/`SLOW` módok időzítési sajátosságait a 2. fázisban mérjük és kezeljük). Az aktív emlékeztetők bitmezőben, dátumbélyeggel élnek, az elavulás-kezelés ugyanaz, mint az állapotbiteknél.

## 8. Vezérlők és képernyő (első változat)

| Billentyű | Funkció |
| --- | --- |
| `SHIFT+1..4` | Hőmérséklet: 1 = tényszerű … 4 = kreatív |
| `SHIFT+9` | Reasoning (gondolkodási lépések megjelenítése) ki/be |
| `SHIFT+5` / `SHIFT+6` | Beszélgetés görgetése vissza / előre |
| `SHIFT+S` | Mentés kazettára (chat + állapotbitek, dátumbélyeggel) |
| `SHIFT+SPACE` | Válasz / gondolkodás megszakítása |

Bevitel: a **ZX81 ROM `INPUT` rutinja**, karakteres módban. A csevegőpanel minden üzeneténél (modell és felhasználó egyaránt) **inverz fejléc** jelenik meg: órabélyeg + felhasznált tokenek + válaszidő, alattuk státusz- és gondolkodási sáv.

```
┌ bejelentkező kép (splash) ─────────┐  ┌ csevegőpanel ──────────────────┐
│   (blokkgrafika jelmez, inverz)    │  │PIOCO AI  12:41  TOK 214  0.8s │← inverz fejléc (modell)
│         P I O C O   A I            │  │Szia! Miben segíthetek?         │
│    miniatűr nyelvi modell          │  │─────────────────────────────── │
│        ZX81 · 16 KB                │  │<NÉV>    12:42  TOK 9    —     │← inverz fejléc (felhasználó)
│                                    │  │Mesélj a csillagokról!          │
│  Üdv, <NÉV>! Kérsz útmutatót?      │  │GONDOLKODOM: [2/4] entitások…   │← thinking sáv
│      (I = igen  /  N = nem)        │  └────────────────────────────────┘
└────────────────────────────────────┘
```

## 9. Gyors szalagkezelés (turbo / fast tape)

A gyári ZX81 szalagformátum lassú; a terv ezért tartalmaz **turbo/fast tape rutint** a 3. fázisban — de a mesterpromptnak megfelelően a fejlesztés idején **kikapcsolva**, egyetlen konstansszal (aktív/passzív) vezérelve, mert az emulátorok a gyári formátumot kezelik megbízhatóan. Emulátorban a betöltés amúgy is azonnali, így a fejlesztést nem lassítja.

## 10. Tréning és eszközök (PC oldalon, a GLM munkaterületen)

A „tréning” a ZX81-en nem futtatható — a PC-n építjük, az eredménye kerül a kazettára:

- `eszkozok/tokenizalo.py` — szótárépítés (gyakori szavak + magyar toldalékok statisztikája) + szöveg→token folyam;
- `eszkozok/csomaagepito.py` — tudásszöveg → tömörített csomag (RLE + nibble-csomagolás) + n-gram statisztika az adott témára, majd **kvantálás 4 bites, `-8..+7` egész súlyokra** (a szűkített tartomány hatása a válaszminőségre a tréning része);
- `eszkozok/t81iro.py` — ZX81 szalagblokkok (pilot/sync/adat bájtsorrenddel) helyes kiírása → `.T81`; a formátumrészleteket emulátor-kompatibilitás szerint a 3. fázisban véglegesítjük;
- **témacsomag-lista** (a mesterprompt szerint): tudomány, gasztronómia, egészség, szórakozás, retro korszak, retro technológia, jövőkutatás, tanulás, hobbi, csillagászat, irodalom, filmek, hírességek, művészet, munka, UFO;
- **tesztelés:** emulátorral (pl. EightyOne Windows-on, sz81 Linux-on) — `.T81` betöltés, multiload-lánc, 0x76-szabály betartásának ellenőrzése, majd valódi gépen gyakorlati próbásság.

## 11. Fázisterv

| Fázis | Cél | Kimenet |
| --- | --- | --- |
| **1. Ötlet és koncepció** ✅ | architektúra rögzítése, realitásvizsgálat, kompromisszumok tisztázása | ez a dokumentum + a repó felépítése |
| **2. Tervezés, működés és dizájn** | végleges memóriatérkép, bitmezők bontása, ZX81 karaktertábla, .T81 sávformátum, képernyőtervek, vezérlők, Agent-parancsnyelv, rajzvászon- és BASIC-puffer-elhelyezés, emlékeztető-modul specifikációja | `docs/fazis-2-terveles.md` |
| **3. Kódolás és csomagolás** | Z80 motor, PC-s eszközök, első futó `.T81` (turbo kikapcsolva) | `motor/`, `eszkozok/`, `kazetta/pioco-0.1.t81` |
| **4. Tudás, tréning, tesztelés** | alaptudás + első témacsomagok, emulátoros és gyakorlati ellenőrzés | `tudas/`, `kazetta/*.t81`, tesztnapló |

Minden fázis lezárásakor: commit a GitHubra + a fejlesztési napló frissítése + rövid összefoglaló, amiről dönthetsz (jóváhagyás / módosítási kérés).

## 12. Kockázatok és nyitott döntések

1. **Kazetta-felülírás** — fizikailag csak hozzáfűzés lehetséges; megoldási javaslat az 5.1-ben, a 2. fázis döntése.
2. **Szalagidő** — a gyári formátum lassú; a tudáscsomag méretét és a csomagváltások gyakoriságát ehhez kell igazítani; a turbo-rutin (később, óvatosan) enyhíti.
3. **ROM `INPUT` és saját UI** — a ROM rutin a saját képernyőkezelésünkkel együtt csak akkor működik, ha a kurzor- és sorkezelést igazítjuk; a 2. fázisban kiderül, kell-e vékony saját beviteli réteg.
4. **Turbo megbízhatóság** — emulátoron kikapcsolva fejlesztünk; valódi gépen külön tesztkör.
5. **Helyhiány a motorban/szótárban** — átcsoportosítási terv a 4.1-ben; a mérés a 3. fázisban dönt.
6. **Vászon + BASIC-puffer helyigénye** — a 352 bájtos rajzvászon és a program-puffer együtt szorítja a MUNKATERÜLET-et (768 B); ha szűkös, a CHAT zóna vagy a csomagterület szabad fara átcsoportosítás — a 2. fázis dönti el, mérés után.

---

*Készült: 2026-11-21 · GLM (Z.ai) · 1. fázis — az „Ötlet és koncepció” dokumentuma.*


