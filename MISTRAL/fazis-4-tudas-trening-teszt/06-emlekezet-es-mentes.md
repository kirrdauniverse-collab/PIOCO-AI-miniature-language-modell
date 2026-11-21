# EMLÉKEZET (06 blokk) és mentés — 4. fázis, harmadik lépés

Állapot: elkészült és automatikusan ellenőrizve. A `PIOCO.T81` most
**5079 bájt, 6 blokk** (új: B6-EMLEKEZET, cél = 0x6700); a kilencféle
vizsgálat (méret, mágnesjel, XOR, PROFIL-védelem, RAM-határ, 0x76-tiltás,
szótárforma, bigramm-forma, emlékforma) zöld.

## 1. Kimért számok

| Elem | v2 (előző lépés) | v2.1 (most) | Zónahatár |
| --- | --- | --- | --- |
| Motor (`motor.bin`) | 1819 B | **2729 B** | 4096 B |
| Szótár + bigramm (`szotar_full.bin`) | 1290 B | 1290 B | 2560 B |
| EMLÉKEZET zóna (0x6700) | — | 2 + 4×63 = **254 B** | CHAT figyelmen kívül: 0x6700–0x67FF = 256 B |
| Kazetta (`PIOCO.T81`) | 4144 B, 5 blokk | **5079 B, 6 blokk** | — |

A motor mérete 2729/4096 B: marad ~1,3 KB a későbbi görgetésre
(SHIFT+5/6) és a chat-history fejlécekre.

## 2. Az emlékrekord formátuma

Az emlékezetzóna a CHAT-terület végén, **0x6700**-tól; a 06-os
kazettablokk ide tölt:

```
[0x6700] mágnesjel 0xC3
[0x6701] rekordszám (0..63)
[0x6702] rekordok, egyenként 4 bájt:
         b0 = bitkód (0..31; a fakt-azonosító)
         b1 = érték 0/1, bit7 = elavulás-jel (elavult: 0x80)
         b2 = nap (1..31)
         b3 = hónap (1..12)
```

Egy fakt **4 bájton** él; max 63 rekord = 254 B.

## 3. Boot-folyamat

1. `EMINIT`: mágnesvizsgálat (nincs 0xC3 → üres zóna); a PROFILban
   mentett dátumot átveszi (vagy 0-k maradnak).
2. `DATASK`: ha nincs dátum (nap = 0), addig kérdezi az „enter date
   as dd mm:" kérdést, amíg érvényes dátum nem jön; a beírt dátum a
   PROFIL 0x24/0x25 bájtjába is kerül (védve a későbbi betöltésektől).
3. `OBSSCAN`: az összes rekordon végigmegy, és a 14 napnál régebbiek
   értékbájtját 0x80-ra írja (érték 0 + elavulás-jel). Hónaponkénti
   besorolással számol (azonos hónap: napkülönbség; egy hónappal
   korábbi: 30 + napkülönbség; kettő vagy több: elavult) — 16 bites
   matek nélkül, a hónapokat egységesen 30 nappal közelíti.
4. `REMCHK`: ha van **aktív** (b1 = 1) fejfájás- vagy rosszullét-rekord,
   rákérdez: „i remember head pain. better?" — ha a válaszban szerepel
   a GONE/BETTER/YES/GOOD/OK szó, a fakt 0-ra áll (megszűnt).

## 4. Fakt-felismerés beszéd közben

A főciklus minden sor után lefuttatja a `FACTSET`-et:

| Kulcsszó a sorban | bitkód | alapérték |
| --- | --- | --- |
| HEAD / HURT / ACHE | 0 | 1 |
| SICK / ILL / FEVER | 1 | 1 |
| HAPPY / GLAD | 2 | 1 |

- ha a sorban **NO / NOT** is szerepel, az érték 0 („no pain" → nem fáj);
- találat esetén INTENT = 5 és a válasz a rögzítés: „[noted]";
- a FLAG-B (PROFIL 0x1C) 0–4. bitje tükrözi a 0–4. bitkódokat
  (bitképzés: 1 << (bitkód ÉS 7), de az 5+ bit tilos, hogy FLAG-B
  soha ne állhasson össze 0x76-ot adó bájtba);
- a FLAG-B állítás dátumát a PROFIL 0x20/0x21 bájtba bélyegzi.

## 5. Mentés: SHIFT+S

`SAVEMEM` a PROFIL 0x22/0x23 bájtba írja a mentés dátumát. **Őszinte
jelzés:** a 06 blokk valódi kazettára írása (ROM SAVE rutin) az
emulátoros fázisra marad; PC-oldalon viszont már most teljes a kör:
`eml_make.py` építi a 06 blokkot, a `t81_build.py` beteszi a
kazettába, az `ellenorzes.py` ellenőrzi.

## 6. Emlékfájl készítése kézzel (PC-n)

```
python3 eszkozok/eml_make.py kazetta/eml.bin 0:1:12:5 1:1:2:6
```

(bitkód:érték:nap:hónap sorozatok; fenti példa: fejfájás = 1, május 12.;
rosszullét = 1, június 2.)

## 7. Fejlesztési megjegyzések

- a rekordkeresés (`EMFIND`) lineáris; 63 rekordnál is csak 252
  összehasonlítás — ZX81-en belül gyors;
- évnév nincs a dátumban: az évfordulót (dec→jan átmenet) a 30 napos
  közelítés így is kezeli (a decemberti rekord elavul, ahogy eltelt
  2 hónapnyi index); ez dokumentált egyszerűsítés;
- elavult rekord törlése nem történik, csak felülírás új fakt-tal —
  ezzel a SHIFT+S későbbi, valódi kazetta-írása helytakarékos.
