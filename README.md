# PIOCO AI miniature language modell

> Miniatűr, **valóban generáló** AI nyelvi modell a Sinclair ZX81-hez (16 KB RAM) —
> egyetlen összefüggő, több betöltési sávot tartalmazó **.T81** kazettafájlban.

**Állapot:** 🟢 **3. fázis — KIPRÓBÁLHATÓ VÁLTOZAT v0.2: `pioco-by-GLM-0.2.p`** (a C/F080 + száguldozó-pixelek javítása: D-3.8 PERSIST a ROM veremzónájáról 0x7E00-ra költözött — a hibát a valódi ROM Logan–O'Hara listája alapján találtuk meg) · prototípus-nyelv: **angol** (D-3.2) · PERSIST: 0x7E00 (D-3.8) · **névkonvenció: minden átadott fájl `pioco-by-GLM-<verzió>…`** (2026-11-21-től)

## Mi ez?

A PIOCO AI nem beégetett mondatokat ad vissza. A 16 KB-os kereteken belül valódi
feldolgozási láncot valósít meg:

**tokenizálás → belső gondolkodási fázis (szándék → entitások → tudáslekérés → választerv)
→ állapotfrissítés → generálás hőmérséklet-vezérléssel.**

A tudás kazettás csomagokból jön (multiload), a személyes adatok (név, nem, születési
adat, dátum/óra) egy **védett tartós memóriablokkba** (`PERSIST_BLOCK`) kerülnek,
amelyet a későbbi betöltési sávok nem írnak felül. Kétállapotú információk
(igen/nem, fáj/nem fáj) **1 biten** tárolódnak, dátumbélyeggel és elavulás-kezeléssel.
A modell nyelve: szótag/toldalék tokenek és **4 bites egész súlyok** (`-8..+7`,
bájtonként kettő), gondolkodása a `[THINK_START]` … `[THINK_END]` blokkban fut.
Tud **rajzolni** (64×44-es plot-vásznon, hozzáadó módban), **rövid BASIC programot
írni és utólag módosítani**, **időzített emlékeztetőt** tartani, és humorban,
ingerlésben és vitában is saját megfogalmazással, több körön át emlékező állásponttal válaszol.

## Dokumentumok

| Fájl | Tartalom |
| --- | --- |
| [`MASTERPROMPT.md`](MASTERPROMPT.md) | A projekt mesterpromptja (követelmények, működési elvek, szabályok) + a projektgazda kiegészítése (5. fejezet) |
| [`docs/fazis-1-koncepcio.md`](docs/fazis-1-koncepcio.md) | **1. fázis:** koncepció, realitásvizsgálat, modultérkép, memóriatérkép-javaslat, .T81 sávstruktúra, fázisterv |
| [`docs/fazis-2-terveles.md`](docs/fazis-2-terveles.md) | **2. fázis:** végleges memóriatérkép (belső bontásokkal), bitmezők, karaktertábla, .T81 blokkformátum, képernyőtervek, vezérlők, Agent-parancsnyelv, emlékeztető-modul |
| [`docs/FEJLESZTESI-NAPLO.md`](docs/FEJLESZTESI-NAPLO.md) | Fejlesztési napló fázisonként |

## Tervezett fázisok

| # | Fázis | Állapot |
| --- | --- | --- |
| 1 | Ötlet és koncepció | ✅ kész (2026-11-21) |
| 2 | Tervezés, működés és dizájn — végleges memóriatérkép, bitmezők, sávformátum, képernyők, vezérlők, Agent-parancsok | ✅ kész (2026-11-21) |
| 3 | Kódolás és csomagolás — Z80 motor, PC-s eszközök, .T81 összeállítás | 🔵 5. szelet kész (2026-11-21): D-3.8 PERSIST-költöztetés a ROM veremzónájáról (valódi ROM + Logan–O'Hara lista alapján), romsim.py ROM-szintű virtuális gép; következik: ROM-szintű zöld futás, INPUT + Agent-kör |
| 4 | Tudásbázis, tréning és tesztelés — alaptudás + témacsomagok, emulátoros ellenőrzés | ⬜ |

## Repó struktúra

```
PIOCO-AI/
├── docs/        tervezési és fázisdokumentumok
├── motor/       ZX81 gépi kód (Z80): boot.asm (1. szakasz), motor0.asm (2. szakasz)
├── eszkozok/    PC-s eszközök: crc16, tokengen, alapmag_gen, z80asm, epites, csomaggen,
│                z80sim (Z80-szimulátor), szimfuttatas (szalag-mód végpont-teszt),
│                pgen (rezidens .P generátor), pfuttatas (virtuális emulátor-teszt)
├── tudas/       alaptudás: angol prototípus-korpusz + generált szótár-lista
└── kazetta/     pioco-0.1.p (KIPRÓBÁLHATÓ! kézbesített név: pioco-by-GLM-0.1.p),
                 pioco-0.1.tape, adat/, kepernyokep_*.txt
```

## Célplatform

- **Elsődleges (most erre építünk):** Sinclair ZX81, 16 KB RAM, Z80 @ 3,25 MHz, `.T81` kazetta
- **Távlati portok (most nem építünk rájuk):** Spectrum 48/128, Commodore 16/64/128,
  Amiga 500/1200, TVC 64, Enterprise 128, Primo 32, HT1080Z

## Licenc

MIT — lásd [`LICENSE`](LICENSE).
