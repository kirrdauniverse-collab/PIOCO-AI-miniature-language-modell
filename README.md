# PIOCO AI miniature language modell

> Miniatűr, **valóban generáló** AI nyelvi modell a Sinclair ZX81-hez (16 KB RAM) —
> egyetlen összefüggő, több betöltési sávot tartalmazó **.T81** kazettafájlban.

**Állapot:** 🟡 **1. fázis (Ötlet és koncepció) — KÉSZ** · Következő: 2. fázis (tervezés és dizájn)

## Mi ez?

A PIOCO AI nem beégetett mondatokat ad vissza. A 16 KB-os kereteken belül valódi
feldolgozási láncot valósít meg:

**tokenizálás → belső gondolkodási fázis (szándék → entitások → tudáslekérés → választerv)
→ állapotfrissítés → generálás hőmérséklet-vezérléssel.**

A tudás kazettás csomagokból jön (multiload), a személyes adatok (név, nem, születési
adat, dátum/óra) egy **védett tartós memóriablokkba** kerülnek, amelyet a későbbi
betöltési sávok nem írnak felül. Kétállapotú információk (igen/nem, fáj/nem fáj)
**1 biten** tárolódnak, dátumbélyeggel és elavulás-kezeléssel.

## Dokumentumok

| Fájl | Tartalom |
| --- | --- |
| [`MASTERPROMPT.md`](MASTERPROMPT.md) | A projekt mesterpromptja (követelmények, működési elvek, szabályok) |
| [`docs/fazis-1-koncepcio.md`](docs/fazis-1-koncepcio.md) | **1. fázis:** koncepció, realitásvizsgálat, modultérkép, memóriatérkép-javaslat, .T81 sávstruktúra, fázisterv |
| [`docs/FEJLESZTESI-NAPLO.md`](docs/FEJLESZTESI-NAPLO.md) | Fejlesztési napló fázisonként |

## Tervezett fázisok

| # | Fázis | Állapot |
| --- | --- | --- |
| 1 | Ötlet és koncepció | ✅ kész (2026-11-21) |
| 2 | Tervezés, működés és dizájn — végleges memóriatérkép, bitmezők, sávformátum, képernyők, vezérlők, Agent-parancsok | ⏳ következik |
| 3 | Kódolás és csomagolás — Z80 motor, PC-s eszközök, .T81 összeállítás | ⬜ |
| 4 | Tudásbázis, tréning és tesztelés — alaptudás + témacsomagok, emulátoros ellenőrzés | ⬜ |

## Repó struktúra

```
PIOCO-AI/
├── docs/        tervezési és fázisdokumentumok
├── motor/       ZX81 gépi kód (Z80) — a 3. fázistól
├── eszkozok/    PC-s eszközök: tokenizáló, csomaggenerátor, .T81 író — a 3. fázistól
├── tudas/       alaptudás + témacsomag-források — a 4. fázistól
└── kazetta/     elkészült .T81 fájlok
```

## Célplatform

- **Elsődleges (most erre építünk):** Sinclair ZX81, 16 KB RAM, Z80 @ 3,25 MHz, `.T81` kazetta
- **Távlati portok (most nem építünk rájuk):** Spectrum 48/128, Commodore 16/64/128,
  Amiga 500/1200, TVC 64, Enterprise 128, Primo 32, HT1080Z

## Licenc

MIT — lásd [`LICENSE`](LICENSE).
