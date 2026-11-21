# PIOCO AI — 1. fázis: Ötlet és koncepció

**Projekt:** PIOCO AI miniature language modell
**Célplatform:** Sinclair ZX81 · 16 KB RAM · Z80 @ 3,25 MHz · egyetlen, több betöltési sávot tartalmazó `.T81` kazettafájl
**Dátum:** 2026-11-21
**Fejlesztői munkaterület:** `GLM/` (helyi) · **Repó:** `github.com/kirrdauniverse-collab/PIOCO-AI-miniature-language-modell`

> Elnevezési döntés: a mesterprompt „Pico AI”-ként hivatkozik a modellre, a repó neve viszont PIOCO. A **PIOCO AI**-t tekintjük hivatalos névnek — a motorban és az eszközökben egyetlen konstans dönt róla, bármikor cserélhető.

---

## 1. A koncepció egy mondatban

A PIOCO AI egy miniatűr, **valóban generáló** nyelvi modell a Sinclair ZX81-en belül: nem beégetett mondatokat ad vissza, hanem a bejövő szöveget **tokenizálja**, több lépéses **belső gondolkodási folyamaton** (szándék → entitások → tudáslekérés → választerv) visz át, majd a tömörített tudásbázisra és a saját mini nyelvi modelljére támaszkodva **maga szerkeszti, toldalékolja és állítja össze a választ**, hőmérséklet-vezérléssel, állapotos emlékezettel és kazettás tudáscsomagokkal — mindezt a 16 KB-os RAM-ban.

## 2. Realitásvizsgálat: mi fér be a 16 KB-ba?

### 2.1 Kiindulási adatok

| Paraméter | Érték | Következmény a tervezésre |
| --- | --- | --- |
| CPU | Z80 @ 3,25 MHz | minden számítás egészszámos és táblázatos; bonyolult lebegőpontos művelet nincs |
| RAM | 16 KB (0x4000–0x7FFF) | a rendszerváltozók és a képernyő (D_FILE ≈ 793 bájt) levonandó a 16 KB-ból |
| ROM | 8 KB BASIC | a `PRINT`, `INPUT` és a szalagkezelő rutinok újrahasznosíthatók — nem kell újraírni |
| Háttértár | magnókazetta (`.T81`) | a tudás és az emlékezet „virtuálisan” nagy lehet: sávról cserélhető (multiload) |
| Képernyő | 32 × 24 karakter | tömör, rövid válaszok; görgetés; inverz fejlécek és státuszsáv |

### 2.2 Mit nem ígérünk (és miért)

Egy mai, valódi neurális nyelvi modellnek legalább tízmillió paramétere van; már 1 millió paraméter is kb. 1 MB 8 bites tárolással — ez a ZX81 teljes címtérének 64-szerese. Neurális háló tehát **fizikailag nem fér be**. A PIOCO ezért nem „csökkentett LLM”, hanem **miniatűr, valódi generálású nyelvi motor**: statisztikai nyelvi modell (n-gram) + magyar toldalékolás + váz-alapú szövegszintézis + indexelt tudásbázis. Az elvárt hatás ugyanaz, amit a mesterprompt kér: a válasz **futásidőben, újrakomponálva** születik, nem visszakeresett mondat.

### 2.3 Mit tudunk — a generálási lánc lépésről lépésre

1. **Tokenizáló** — a beírt szöveget szóalap- és toldaléktokenekre bontja. A szótár kb. **400–460 token** (gyakori szavak + magyar toldalékok: `-ban/-ben`, `-nak/-nek`, `-ra/-re`, `-val/-vel`, `-t`, `-ok/-ek/-ök` stb.), minden token 1 bájt (0–255). Az ismeretlen szó betű-tokenekre bontható — a modell tehát **mindent el tud olvasni**, nem csak a szótárban lévőt. Ez az „agglutináló nyelv kompromisszum”: kevés tárolóból nagy lefedettség.
2. **Belső gondolkodási fázis (reasoning)** — 3–5 lépés: szándékfelismerés → kulcsentitások (név, hely, téma, idő) → tudáslekérés az indexelt tudásbázisból → választerv. A lépések élőben láthatók a `GONDOLKODOM…` sávban, SHIFT+9-gyel ki/be kapcsolható.
3. **Generálás** — a választervet a mini nyelvi modell (2–3 szó kontextusú n-gram, a tudáskorpuszra és a beszélgetésre „tanítva”) és **vázak** (behelyettesíthető résekkel rendelkező mondatkeretek: számok, nevek, dátumok) együtt építik: a kimenet saját sorrendben, toldalékolva, behelyettesítve **újrakomponált** szöveg.
4. **Hőmérséklet** — a választási véletlen vezérlése (top-k szűkítés/kiszélesítés): 1 = tényszerű, 4 = kreatív (`SHIFT+1..4`).
5. **Állapotfrissítés** — a beszélgetésben előkerülő kétállapotú tények bitekre kerülnek (pl. „fáj a fej” = 1), dátumbélyeggel; elavuláskor a motor rákérdez, majd új információval írja felül (lásd 6. szakasz).

### 2.4 Fő kompromisszumok egy helyen

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
            │ [S1 INDÍTÓ] [S2 MOTOR+ALAPTUDÁS] [S3..N TÉMACSOMAG] │
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
| INDÍTÓ (Sáv 1) | splash kép, név, üdvözlet, útmutató-kérdés; profil-kérdezés (pontos dátum, óra, név, nem, születési adat); mentés a védett PROFIL blokkba |
| MOTOR | tokenizáló, generátor, reasoning, hőmérséklet, UI, szalag-I/O |
| SZÓTÁR | token ↔ szöveg táblák + toldalékkódok (kb. 400–460 token) |
| TUDÁS | ALAPMAG (mindig rezidens) + CSOMAGTERÜLET (témacsomagok cserélődnek rajta) |
| EMLÉKEZET | chat history + bitmezők + dátumbélyegek + elavulás-kezelés |
| PROFIL | tartós, védett blokk: név, nem (1 bit), születési adat, dátum/óra, beállítások |

## 4. Memóriatérkép-javaslat (0x4000–0x7FFF, pontos bájtösszegekkel)

A bontás Python-számítással ellenőrzött: a zónák **folytonosan** lefedik a 0x4000–0x7FFF területet, összesen pontosan **16 384 bájtot**.

| Címtartomány | Zóna | Méret | Megjegyzés |
| --- | --- | ---: | --- |
| 0x4000–0x40FF | ROM-kompatibilis rendszerváltozók + saját állapotbájtok | 256 B | a ROM `INPUT`/`PRINT` rutinjai ezt igénylik |
| 0x4100–0x41FF | **PROFIL — tartós, védett blokk** | 256 B | név, nem (1 bit), születési adat, dátum/óra, beállítások, állapotbitek; a multiload sávok **soha** nem írnak ide |
| 0x4200–0x45FF | D_FILE + UI puffer | 1024 B | a D_FILE felső harmada munkaterületként is használható (effektek, scratch) |
| 0x4600–0x53FF | MOTOR (kód) | 3584 B | tokenizáló, generátor, reasoning, UI, szalag-I/O |
| 0x5400–0x5CFF | SZÓTÁR + tokenizáló táblák | 2304 B | kb. 400–460 token, 1 bájt/token |
| 0x5D00–0x62FF | CHAT history | 1536 B | tömörített üzenetek, görgetés SHIFT+5/6 |
| 0x6300–0x6AFF | ALAPMAG (rezidens tudás) | 2048 B | az alaptudás magja mindig bent marad |
| 0x6B00–0x7AFF | CSOMAGTERÜLET (témacsomagok) | 4096 B | a témacsomagok itt cserélődnek kazettáról |
| 0x7B00–0x7DFF | MUNKATERÜLET | 768 B | token buffer, reasoning stack, scratch |
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
| **S1 — INDÍTÓ** | splash kép + modellnév, üdvözlet, útmutató-kérdés (I/N), profil-kérdezés: pontos dátum, óra, név, nem, születési adat | a PROFIL blokkba ment (0x4100–0x41FF), majd kéri a Sáv 2-t |
| **S2 — MOTOR + ALAPTUDÁS** | motor (3,5 KB) + szótár (2,3 KB) + ALAPMAG (2 KB) + a CSOMAGTERÜLET kezdő tartalma | célzott címekre tölt — a PROFIL blokkot **nem érinti** —, elindítja a csevegőképernyőt |
| **S3..N — TÉMACSOMAGOK** | tudomány, gasztronómia, egészség, szórakozás, retro korszak, retro technológia, jövőkutatás, tanulás, hobbi, csillagászat, irodalom, filmek, hírességek, művészet, munka, UFO stb. | a CSOMAGTERÜLET (0x6B00–0x7AFF) felülírásával cserélődnek; a motor menüből / parancsból kéri őket |
| **M — EMLÉKEZET-MENTÉS** | chat history + állapotbitek + beállítások, dátumbélyeggel | visszatöltéskor a **legfrissebb** blokk nyer |

### 5.1 „Felülírás” a kazettán — műszaki korlát és megoldás

Fontos, őszinte korlát: egy magnókazetta **középre nem írható felül biztonságosan** — a felvétel fizikailag új felvétel. Javasolt megoldás: az emlékezet-mentés mindig a **szalag végére** kerül (hozzáfűzés), minden blokk dátumbélyeget kap, és a motor visszatöltéskor a **legfrissebb** érvényes blokkot választja; a régiek egyszerűen elavulnak. Alternatíva: külön „MENTÉS” kazetta. (Ezt a döntést a 2. fázisban véglegesítjük — nincs hatással a memóriatérképre.)

## 6. Karakter- és bitbiztonság (a „0x76-szabály”)

- **Képernyőmemória (D_FILE):** kizárólag a sima karaktertartomány (**0x00–0x3F**) és az inverz/grafikatartomány (**0x80–0xBF**) kerülhet bele; a `0x76` (sorzáró, NEWLINE) csak a print-rutintól, sorvégen; minden más kód (0x40–0x75, 0x77–0xFF — a ROM parancs- és vezérlőkód-tartományai, pl. `PRINT`, `RETURN`, `GOTO`) **tiltott** a képernyőmemóriában. A pontos karaktertáblázat a 2. fázisban véglegesül.
- **Bináris adat soha nem kerül nyersen a képernyőbe:** bitmezők, token-ID-k, címek csak dekódolás + formázás után, szövegként jelennek meg. A D_FILE felső harmada csak akkor munkaterület, ha rá e szabály érvényesül (scratch puffer, nem megjelenített adat).
- **Bitmezők (1 bit / tulajdonság), irányadó bontás:**
  - `PROFIL` állapotbájt: bit0 = nem (0 = férfi, 1 = nő); bit1–2 = korosztály (00 = gyerek, 01 = fiatal, 10 = felnőtt, 11 = 60+); bit3 = útmutatót kért; bit4 = reasoning alapból bekapcsolva; bit5–7 = tartalék.
  - `ÁLLAPOT` bájtok: pl. bit0 = fáj a fej, bit1 = hátfájás, … külön dátumbájtokkal (év+hónap+nap tömörítve).
  - Tárolás **XOR-maszkkal** (pl. 0xA5): a tárolt bájt véletlenül sem állhat össze `0x76`-á vagy más veszélyes kóddá; a bitek kibontása csak a munkaterületen történik.
- **Elavulás-kezelés** (a mesterprompt példája): „kedden fáj a fejem” → 1-es bit + dátumbélyeg, mentés a kazettára; későbbi beszélgetésben, ha releváns, a PIOCO rákérdez; ha a betöltés óta eltelt napok száma meghaladja a küszöböt (pl. 7 nap), az állapot **elavultként** kezelődik: rákérdez, majd nullázza / új infóval írja felül.

## 7. Vezérlők és képernyő (első változat)

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

## 8. Gyors szalagkezelés (turbo / fast tape)

A gyári ZX81 szalagformátum lassú; a terv ezért tartalmaz **turbo/fast tape rutint** a 3. fázisban — de a mesterpromptnak megfelelően a fejlesztés idején **kikapcsolva**, egyetlen konstansszal (aktív/passzív) vezérelve, mert az emulátorok a gyári formátumot kezelik megbízhatóan. Emulátorban a betöltés amúgy is azonnali, így a fejlesztést nem lassítja.

## 9. Tréning és eszközök (PC oldalon, a GLM munkaterületen)

A „tréning” a ZX81-en nem futtatható — a PC-n építjük, az eredménye kerül a kazettára:

- `eszkozok/tokenizalo.py` — szótárépítés (gyakori szavak + magyar toldalékok statisztikája) + szöveg→token folyam;
- `eszkozok/csomaagepito.py` — tudásszöveg → tömörített csomag (RLE + nibble-csomagolás) + n-gram statisztika az adott témára;
- `eszkozok/t81iro.py` — ZX81 szalagblokkok (pilot/sync/adat bájtsorrenddel) helyes kiírása → `.T81`; a formátumrészleteket emulátor-kompatibilitás szerint a 3. fázisban véglegesítjük;
- **témacsomag-lista** (a mesterprompt szerint): tudomány, gasztronómia, egészség, szórakozás, retro korszak, retro technológia, jövőkutatás, tanulás, hobbi, csillagászat, irodalom, filmek, hírességek, művészet, munka, UFO;
- **tesztelés:** emulátorral (pl. EightyOne Windows-on, sz81 Linux-on) — `.T81` betöltés, multiload-lánc, 0x76-szabály betartásának ellenőrzése, majd valódi gépen gyakorlati próbásság.

## 10. Fázisterv

| Fázis | Cél | Kimenet |
| --- | --- | --- |
| **1. Ötlet és koncepció** ✅ | architektúra rögzítése, realitásvizsgálat, kompromisszumok tisztázása | ez a dokumentum + a repó felépítése |
| **2. Tervezés, működés és dizájn** | végleges memóriatérkép, bitmezők bontása, ZX81 karaktertábla, .T81 sávformátum, képernyőtervek, vezérlők, Agent-parancsnyelv | `docs/fazis-2-terveles.md` |
| **3. Kódolás és csomagolás** | Z80 motor, PC-s eszközök, első futó `.T81` (turbo kikapcsolva) | `motor/`, `eszkozok/`, `kazetta/pioco-0.1.t81` |
| **4. Tudás, tréning, tesztelés** | alaptudás + első témacsomagok, emulátoros és gyakorlati ellenőrzés | `tudas/`, `kazetta/*.t81`, tesztnapló |

Minden fázis lezárásakor: commit a GitHubra + a fejlesztési napló frissítése + rövid összefoglaló, amiről dönthetsz (jóváhagyás / módosítási kérés).

## 11. Kockázatok és nyitott döntések

1. **Kazetta-felülírás** — fizikailag csak hozzáfűzés lehetséges; megoldási javaslat az 5.1-ben, a 2. fázis döntése.
2. **Szalagidő** — a gyári formátum lassú; a tudáscsomag méretét és a csomagváltások gyakoriságát ehhez kell igazítani; a turbo-rutin (később, óvatosan) enyhíti.
3. **ROM `INPUT` és saját UI** — a ROM rutin a saját képernyőkezelésünkkel együtt csak akkor működik, ha a kurzor- és sorkezelést igazítjuk; a 2. fázisban kiderül, kell-e vékony saját beviteli réteg.
4. **Turbo megbízhatóság** — emulátoron kikapcsolva fejlesztünk; valódi gépen külön tesztkör.
5. **Helyhiány a motorban/szótárban** — átcsoportosítási terv a 4.1-ben; a mérés a 3. fázisban dönt.

---

*Készült: 2026-11-21 · GLM (Z.ai) · 1. fázis — az „Ötlet és koncepció” dokumentuma.*


