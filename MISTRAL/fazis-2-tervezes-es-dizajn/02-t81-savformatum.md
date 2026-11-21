# `.T81` kazetta struktúra és multiload blokkformátum (2. fázis)

**Cél:** egyetlen `.T81` fájl, több egymás utáni betöltési blokkal (sávval);
a betöltés célzott RAM-címekre megy, és a PROFIL blokkot megőrzi.

---

## 1. A sávfájl felépítése

```
┌────────────────────────  PIOCO.T81  ───────────────────────────┐
│ [B1] BOOT/INDÍTÓ        → indító és profil-kérdező szekvencia  │
│ [B2] MOTORMAG           → MOTOR (0x4600–0x55FF)                │
│ [B3] SZÓTÁR             → 0x5600–0x5FFF                        │
│ [B4] ALAPMAG            → 0x6C00–0x77FF                        │
│ [B5..Bn] TÉMACSOMAG 1..k→ 0x7800–0x7DFF (egymást felülírók)    │
│ [Bé] EMLÉKEZET-MENTÉS keret → CHAT (0x6000–0x67FF), gép→szalag │
└────────────────────────────────────────────────────────────────┘
```

- **Indító blokk (B1):** splash kép, pörgő karakterek, üdvözlet,
  útmutató-kérdés, profil-kérdezés; elmenti a PROFIL-t, ha még nem létezik
  (mágikus bájt alapján dönt róla), majd jelzi: "a motor következik".
- **B2–B4** betöltése a PROFIL **átugrásával** — a motor minden blokkot csak a
  saját célzónájára enged a memóriába.
- **B5..Bn témacsomagok:** igény szerint, menüből vagy a `TÖLT` agent-parancsból;
  mindig a CSOMAGTERÜLET-re töltődnek, felülírva az előző csomagot.

## 2. Blokkformátum (saját, a motor loaderje értelmezi)

```
Bájt:    0     1      2      3      4      5      6      7      8     9…
      ┌─────┬─────┬───────┬──────┬──────┬──────┬──────┬──────┬───────────┐
      │ 'P' │ 'I' │ típus │ címL │ címH │ mérL │ mérH │ XOR  │  adat…    │
      └─────┴─────┴───────┴──────┴──────┴──────┴──────┴──────┴───────────┘
```

| Mező | Méret | Jegyzet |
| --- | --- | --- |
| Mágnesjel (`'P'`,`'I'`) | 2 B | blokkelej-felismerés |
| Típus | 1 B | 01=BOOT, 02=MOTOR, 03=SZÓTÁR, 04=ALAPMAG, 05=TÉMACSOMAG, 06=EMLÉKEZET, 07=SZAKASZ (blokkfolytatás nagyobb csomagnál) |
| Célcím | 2 B | 16 bites RAM-cím (alacsony bájt elöl) |
| Méret | 2 B | adatbájtok száma (max. 1536 a CSOMAGTERÜLET-hez, 4096 a MOTOR-hoz) |
| XOR-ellenőrző | 1 B | az adatbájtok XOR-a, betöltés után összehasonlítva |
| Adat | 0–4096 B | a betöltendő tartalom; TÉMACSOMAG-nál elől 16 bájt csomagnév |

**Védőellenőrzések minden betöltéskor:**

1. cél + méret a PROFIL-zónába (`0x4100–0x41FF`) esne? → **megszakítás + üzenet**;
2. cél + méret kilóg a 0x4000–0x7FFF tartományból? → megszakítás + üzenet;
3. XOR-nemegyezés? → megszakítás, újrapróbálásra felszólítás (gyári sebességgel).

## 3. Turbo / fast tape — benne van, de kikapcsolva

- A fenti blokkformátum **gyári szalagsebességgel** is működik (a lassúság az ára a
  megbízható emulátorkompatibilitásnak).
- A **gyorsbetöltő rutin** engedélyezése egy bit a PROFIL-ban (bit3 =
  `TURBO_TAPE`); fejlesztés idején **0 (ki)**, mert az emulátorok nem kezelik
  megbízhatóan.
- Ha bekapcsolják: rövidebb sávok, keskeny vezérlőjel-eltolás, 2–3-szoros
  sebesség — **csak tesztkörben**, visszakapcsolhatóan.

## 4. Szalag-írás (MENT)

- `SHIFT+S` vagy a `MENT` agent-parancs → a CHAT tartalma EMLÉKEZET-blokként
  (06-os típus) a kazettára kerül, dátumbélyeggel (lásd
  `03-bitmezo-terkep.md`); a régi mentésszekció új hajtásfelirattal
  megkülönböztethető marad.
- A PROFIL-blokkot a mentő rutin **kizárja az írásból** — a
  PROFIL változatlanul marad, csak az EMLÉKEZET-blokk íródik.

---

## Frissítés (v2.5 — EO81 single-image, implementált és tesztelt)

A fenti többblokkos-formátumterv **nem volt betölthető** a valódi ZX81 ROM-mal:
a LOAD rutin (NEXT-PROG 0x0347 → IN-PROG 0x037B) **csak egyetlen összefüggő
képet** vesz, 0x4009-től a szalagon lévő E_LINE-ig. A régi design e miatt adott
**C/6 (out of range)** hibát — nem a BASIC-programok hibája volt.

Az implementált v2.5 `.T81` (EO81 konténer):

```
b"EO81" | [32 B név | 16 B ASCII méret | adat] ...blokkok...
```

- **Fő blokk `PIOCO`:** stream = `b"PIOCO"` + `0x80`-lezáró bájt + **kép**
  (15 863 B = `0x4009..0x7E00`), valódi ROM SAVE-kének megfelelően:
  - boot-sablon (0x4009–0x42C2-ig, 698 B, `sablon_keszit.py`),
  - `10 RAND USR 18176` launcher-sor `0x406D`-nél,
  - szintetikus teljes 24 soros üres képernyő (D_FILE=0x4083, sorlezáró 0x76-értékek épek),
  - VARS (0x439C) = üres 0x80; edit-stub (7F 76 00) = 0x439D; STKBOT=STKEND=0x439F,
  - zónák: MOTOR 0x4700, SZÓTÁR 0x5700, TADAT 0x6B00, ALAPMAG 0x6C00, TARTALEK 0x7D00,
  - rendszerváltozó-patchek (E_PPC=10, D_FILE, DF_CC, VARS, X_PTR, STKBOT, STKEND),
  - **a szalagon lévő E_LINE = 0x7E00** → a LOAD a 0x7DFF-nél áll meg,
    a PROFIL (0x7E00..0x7FFF) a képen kívüli, LOAD-védettségért.
- A LOAD "" (null-név, D=0x80) névnyilvántartás nélkül tölt; a lejátsoó a
  blokk ELŐTT min. 0,5 s csendet adjon.
- **További témacsomag-blokkok** (a 8. argumentumtól `[csomag.bin, név]` párok)
  a motor saját betöltőjét hívják — a PROFIL-persistencia a motor SHIFT+S
  kazettaíró-rendszerének feladata (4. fázis).
- Lejátszó-protokoll az `zx81sim.py` `stream_to_ear` (lead_in ≥ 25 000 csend,
  bit = 4 (0) / 9 (1) impulzus × 150/150 µs, bit utáni ~1 ms csend, MSB first).

Végponti bizonyíték: `tesztek/kazetta_teszt.py` valódi ROM-mal bájtpontos LOAD-ot
bizonyít (PROFIL-szenitel érintetlen, a 0x7FE8–0x7FEB verem-maradék 4 bájt kivételével).
