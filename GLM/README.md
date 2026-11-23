# ZX81 AI micro language modell — GLM munkakönyvtár

> Miniatűr, **valóban generáló** AI nyelvi modell ("Pico AI") a Sinclair ZX81-hez
> (16 KB RAM), egyetlen összefüggő, több betöltési sávot tartalmazó **.T81**
> kazettafájlban. Ez a `GLM/` munkakönyvtár tartalmaz **mindent**: motort,
> PC-eszközöket, tudásadatot, épített kazettákat és a teljes dokumentációt.

Tulajdonos: **Sáfár Sándor (kirrdauniverse-collab)** · Motor-fejlesztés és kutatás: GLM

Nem beégetett válaszok: a modell **tokenizál → belső gondolkodási fázist futt
(szándék → entitások → tudáslekérdezés → választerv) → állapotot frissít →
hőmérséklet-vezérelt mintavétellel generál**. A személyes adatok (dátum, óra, név,
nem, születési adat) **védett tartósmemória-blokkba** kerülnek, a későbbi
betöltési sávok nem írják felül; a kétállapotú adatok **1 biten** tárolódnak,
dátumbélyeggel és elavulás-kezeléssel — ahogy a mesterprompt kérte.

## Két építővonal

| Vonal | Motor | Állapot | Hol |
| --- | --- | --- | --- |
| **A — 16K multiload kazetta (GLM_v065)** | C-motor z88dk-vel Z80 gépi kódba fordítva | ✅ **kipróbálható**: shell betöltő + boot-sáv + alaptudás + 13 témácsomag, 16 blokk egy `.T81`-ben | `zx81/16k/` |
| **B — PIOCO Z80 asm-vonal** | Kézi Z80 assembly, saját PC-s Python assemblerrel | 🟢 tervek + eszközök kész, motor félkész (0.6) | `motor/`, `eszkozok/`, `kazetta/` |

A közös C-motor PC-n is fut (`engine/rt_*.c`), így a fejlesztés gyorsan
ellenőrizhető gép nélkül is.

## Kirakat: kész kazetta

- **`zx81/16k/GLM_v065_RT16_TOPICS.t81`** — a teljes multiload-kazetta (16 blokk):
  - `RTLOAD01` — **új: BASIC shell betöltő a szalag elején** (tisztán BASIC,
    gépikód nélkül): bemutatja a programot, tájékoztat, hogy a felső memória
    aktiválása a későbbi v066-ban újraindítással jár, majd ENTER-re
    `LOAD "RTBASE16"`-mel folytatja a láncot;
  - `RTBOOT01` — bejelentkező kép, a modell üdvözöl, felajánlja a használati
    útmutatót, bekéri a pontos dátumot, órát, felhasználónevet, nemet és a
    születési adatot, majd elmenti őket a védett tartós részbe;
  - `RTBASE16` — motor + alaptudás-csomag a korábbi adatok megőrzésével;
  - 13 témakazetta: tudomány, magyarság, hobbi, egészség, munka, művészet,
    tanulás, irodalom, film, programozás, csillagászat, ASCII-rajz, vers.
  - Tervezés: a RAMTOP/felső-memória terv (`RTLOAD01`, v066-os `LD SP` +
    tartószóna) a [`docs/fazis-3-ramtop.md`](docs/fazis-3-ramtop.md) alatt.
- Az előző, v064-es változat is megmarad: `zx81/16k/GLM_v064_RT16_TOPICS.t81`.
- Blokkonkénti sima `.p` gyorsbetöltők is készülnek: `zx81/16k/GLM_v064_rt16_*.p`.

**Kipróbálás (EightyOne vagy más ZX81 emulátor, 16K RAM):**
1. A `.T81`-t kazettaként csatold (tape-ként, ne quickload).
2. `LOAD ""`, aztán `RUN`: először az `RTLOAD01` shell betöltő szövegei jönnek,
   ENTER után a szalag automatikusan továbbmegy.
3. A boot-sáv üdvözöl és kitölti a profilt; az interju után (ENTER) a szalagról
   névre betölt az `RTBASE16` blokk, onnan az alapkérdéseket a `you>` prompt
   mögött kapod.

A vezérlők részletes állapotát lásd a [`docs/HASZNALAT-16K.txt`](docs/HASZNALAT-16K.txt)
és a [`docs/fazis-2-terveles.md`](docs/fazis-2-terveles.md) alatt: a
`SHIFT+S` mentés, `SHIFT+1..4` hőmérséklet, `SHIFT+9` gondolkodás,
`SHIFT+5/6` görgetés a 2. fázis tervei közé tartozik; működik viszont a
`SHIFT+0` torlés a boot-kérdésekben és a szalagról-névre-töltés.

## Könyvtárak

| Könyvtár | Tartalom |
| --- | --- |
| `docs/` | Minden tervezési dokumentum: fázis-1 koncepció, fázis-2 tervezés (memória-térkép, bitmezők, sávstruktúra, vezérlők), fejlesztési napló, használati útmutatók, `T81_FORMAT.md` (EO81-konténer formátum), `BINARY_FORMAT.md`, `LEARNING.md`, `STATUS.md` |
| `MASTERPROMPT.md` | A projekt mesterpromptja (követelmények, 0x76/parancskód-tiltás, bit-tárolás, memóriarányok) |
| `zx81/16k/` | ✅ Az épített, letölthető kazetták (`.T81` + `.p`) |
| `zx81/` | A ZX81-port C-forrásai (`hal_zx81.c`, `main_zx81.c`, `boot16.c`, `app16.c`, Makefile) |
| `engine/` | A közös C-motor (chat, model, memory, journal, clock, router, tape, finomhangolás) |
| `models16/`, `models16_v05/` | A betanított modellek kicsi, kompakt binárisai |
| `training/` | Tréning-korpusz (alap + témák), `train.py`, `pack.py`, `corpus_gen16.py`, `qat16.py` az utólagos tréningeléshez |
| `motor/` | A PIOCO Z80 asm-motor forrásai (`boot.asm` @0x4082, `motor0.asm` @0x4600) |
| `eszkozok/` | PC-eszközök: saját **Z80 assembler** (`z80asm.py`), tokenizáló-generátor (`tokengen.py`), csomaggenerátor (`csomaggen.py`), `.P`-építő (`pgen.py`), motor-építő (`epites.py`), Z80-szimulátor (`z80sim.py`), mikroteszt |
| `tools/` | T81-eszközkészlet: `t81build16.py` (15-blokckos kazetta-építő), `t81verify.py` (szalag-ellenőrző) |
| `tudas/` | Az angol nyelvű alapszótár és alapkorpusz forrásformában |
| `kazetta/` | A PIOCO-vonal épített kimenetei (`pioco-0.6.p`, `pioco-0.1.tape` + `.blk` sávok) |

## Építés és ellenőrzés

```bash
./build_all.sh
```

Ez futtatja mindent, ami itt, gép nélkül is ellenőrizhető:
Z80-assemble (boot + motor0), multiload sáv + adatblokkok építése CRC-körrel,
rezidens `.P`-generálás, a `GLM_v064_RT16_TOPICS.t81` szalag-ellenőrzése, majd
az `RTLOAD01` shell betöltő építése és a `GLM_v065_RT16_TOPICS.t81` ellenőrzése.

A C-motor teljes újrafordításához `z88dk` kell (a kész kazetta a repóban van,
úgy nem kötelező újrafordítani):

```bash
make -C zx81
python3 tools/t81build16.py <chat16.bin> <boot16.bin> models16_v05 zx81/16k
python3 tools/t81verify.py zx81/16k/GLM_v064_RT16_TOPICS.t81
```

Témakazetta tréningelése (a mesterprompt 8. pontja):

```bash
python3 training/train.py --class G --data training/data16/base.txt --out runs16/base_g --steps 20000
python3 training/pack.py --npz runs16/base_g.npz --bin models16_v05/base_g.bin
```

## Fázisállapot (a mesterprompt 4 fázisa)

| # | Fázis | Állapot |
| --- | --- | --- |
| 1 | Ötlet és koncepció (realitásvizsgálat, memóriaarányok, kompromisszumok) | ✅ `docs/fazis-1-koncepcio.md` |
| 2 | Tervezés: memória-térkép, `.T81` sávstruktúra, `0x76`-kapuk, bitmezők, vezérlők | ✅ `docs/fazis-2-terveles.md`, `docs/T81_FORMAT.md` |
| 3 | Kódolás és csomagolás | ✅ v0.6.4: működő multiload-lánc (boot → base → témák), inverz fejlécek, `you>` prompt, torlás javítva · 🟢 PIOCO asm-vonal félkész |
| 4 | Tudásbázis, tréning, emulátoros ellenőrzés | ✅ 13 témakazetta betanítva és betöltésüket emulátorban lejátszva · 🟡 élő `/topic`-váltás futás közben, `turbo tape` kapcsoló |

## Ismert határok és következő lépések

- A `/topic` váltás élő beszélgetés közben (szalag-név átírás a futási időben)
  a következő félév; ma a témakazetta a töltés-láncban cserélhető.
- A chat-körben a `SHIFT+0` torlás még nem működik (a boot-kérdésekben igen).
- A `turbo tape` gyorsbetöltés az emulátor-kompatibilitás miatt fejlesztés alatt
  ki van kapcsolva; az emulátor-kompatibilis gyári sebesség marad.
- A gyári ZX81-ROM másolata a szerzői jog miatt nem jár a tárban: az emulátor
  szállítja a memória-szimulációhoz (`eszkozok/romsim.py` használhatja a saját ROM-fájljával).

## Licenc

MIT — lásd [LICENSE](LICENSE).
