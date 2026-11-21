# PIOCO AI miniature language modell

> Miniatűr, **valóban generáló** AI nyelvi modell a Sinclair ZX81-hez (16 KB RAM) —
> egyetlen összefüggő, több betöltési sávot tartalmazó **.T81** kazettafájlban.

**Állapot:** 🔵 **3. fázis (Kódolás és csomagolás) — 2. szelet kész: Z80-szimulációs végpont-teszt MINDEN ZÖLD** · prototípus-nyelv: **angol** (D-3.2) · PERSIST: 0x7F00 (D-3.3)

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
| 3 | Kódolás és csomagolás — Z80 motor, PC-s eszközök, .T81 összeállítás | 🔵 2. szelet kész (2026-11-21): építés + blokkok + **Z80-szimulációs végpont-teszt zöld** (CRC-kereszteszt, D_FILE-képernyőkép); következik: INPUT + Agent-kör |
| 4 | Tudásbázis, tréning és tesztelés — alaptudás + témacsomagok, emulátoros ellenőrzés | ⬜ |

## Repó struktúra

```
PIOCO-AI/
├── docs/        tervezési és fázisdokumentumok
├── motor/       ZX81 gépi kód (Z80): boot.asm (1. szakasz), motor0.asm (2. szakasz)
├── eszkozok/    PC-s eszközök: crc16, tokengen, alapmag_gen, z80asm, epites, csomaggen,
│                z80sim (Z80-szimulátor), szimfuttatas (végpont-teszt)
├── tudas/       alaptudás: angol prototípus-korpusz + generált szótár-lista
└── kazetta/     pioco-0.1.tape (blokkfolyam) + adat/ + kepernyokep_szimulacio.txt
```

## Célplatform

- **Elsődleges (most erre építünk):** Sinclair ZX81, 16 KB RAM, Z80 @ 3,25 MHz, `.T81` kazetta
- **Távlati portok (most nem építünk rájuk):** Spectrum 48/128, Commodore 16/64/128,
  Amiga 500/1200, TVC 64, Enterprise 128, Primo 32, HT1080Z

## Licenc

MIT — lásd [`LICENSE`](LICENSE).
