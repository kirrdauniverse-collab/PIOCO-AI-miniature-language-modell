# 4. fázis — Tudás, tréning, tesztelés (MISTRAL munkaterület)

**Állapot:** futóvá tett vezérlés, generátor, emlékezet,
chat-napló/görgetés **és naptár + képzelet-modul (v2.3)**. A `PIOCO.T81`
**v2.5: 15 921 B, EO81 single image** (valódi ROM LOAD "" betöltés, bájtpontos),
minden automatikus vizsgálat + a szimulátoros végponti tesztek (`szalag_teszt`,
`kazetta_teszt`) zöldek.

## Mappa

- `01-nyelvvaltas-dontes.md` — az angol prototípusra váltás rögzítése
- `02-trening-utmutato.md` — kód nélküli tréning: `tudas/x.txt` → `kb_compile.py`
- `03-emulatoros-teszt-terv.md` — az A–F emulátoros ellenőrzőlista
- `04-kesz-csomagok.md` — csomag-állapotok + a tervezett témák
- `05-vezervek-es-nagygenerator.md` — bekötött SHIFT-vezérlők,
  teljes billentyűzet ENTER-rel, bigramm-generátor 4 bites súlyokkal
- `06-emlekezet-es-mentes.md` — 4 bájtos emlékrekordok a 0x6700-on,
  dátum-bekérés, fakt-felismerés, 14 napos elavulás, SHIFT+S
- `07-chat-naplo-es-gorgetes.md` — CHAT-napló inverz fejlécekkel,
  sor-/oszlopkurzoros nyomtatómag, SHIFT+5/6 görgetés
- `08-naptar-es-kepzelet.md` — **új** (v2.3): év-bekérés + hét-név számítás
  (2000–2099, 36525 dátumra ellenőrzve), „what day"/„what time" intentek,
  képzelet-modul (IF/WOULD/COULD/WISH → véletlen IMAGSEED-token), FACTTAB
  kiegészítés, TADAT adattábla-blokk (0x6B00)

## Mit hozott a negyedik lépés?

- új nyomtatómag: sor-/oszlopkurzor (DFROW/DFCOL → DFILE + 33×sor + oszlop),
  32 oszlopnél sortörés, a 23. sornál görgetés — a hosszú beírás már nem
  sértheti a 0x76-orterminátorokat (rejtett hiba javítva)
- CHAT-napló (0x6001): [fejléc][0][szöveg][0] formában; fejléc =
  `YOU m:ss [tt]` ill. `PIOCO m:ss [tt] sS`, inverzen
- SHIFT+5/6: message-by-message böngésző (vissza/előre, bármely billentyű
  kilép), a legújabb üzenettel indul
- válaszidő-mérés FRAMES-pillanatképpel, token-számláló a BGWORD-ben

## Mit hozott az ötödik lépés (v2.3)?

- év-bekérés (PROF_YR, opcionálisan a dátum-sorban is) + DOWGET hét-név
  számítás a 2000–2099-es évszákra — a TAB13 tábla 36 525 dátumra
  brute-force ellenőrizve (0 hiba)
- „whate day"/„what time is it" válaszok (intent 6/7); ha nincs év, sima
  generálásra esik vissza
- képzelet-modul: IF/WOULD/COULD/WISH felismerés → véletlen
  DREAM/HUMAN/MAYBE/SOMETHING token a generátor induló szavaként
- FACTTAB új szavak (SLEEP/TIRED/HUNGRY/ANGRY, bitkód 3–6)
- új TADAT blokk (0x6B00): a statikus táblák kikerültek a motorzónából
  (motor: 4052 B, tartalék 44 B; reszletek: `08-naptar-es-kepzelet.md`)

## Mit hozott a harmadik lépés?

- EMLÉKEZET zóna (06 blokk, cél = **0x6700**, 254 B / 63 rekord)
- boot-flow: EMINIT → dátum-bekérés, ha még nincs („enter date as dd mm:")
  → OBSSCAN (14 napnál régebbi rekordok elavulttá tétele)
  → REMCHK (aktív fejfájás/rosszullét-faktra rákérdezés)
- FACTSET: HEAD/SICK/HAPPY-faktok felismerése, NO/NOT tagadás kezelése,
  FLAG-B bitképzés 0x76-biztos határokkal
- SHIFT+S: PROFIL dátumbélyeg („[memory saved]"); a kazettára írás
  az emulátoros fázisra marad, PC-oldalon a 06-kör már teljes
- az `eml_make.py` és az `ellenorzes.py` eml-ellenőrzése

## Mit hozott a második lépés?

- teljes 8 soros billentyűtérkép (ENTER + SHIFT-bit) a motorban
- SHIFT+1..4 (hőmérséklet), SHIFT+9 (érvelés), SHIFT+S (mentés-stub),
  SHIFT+SPACE (megszakítás) — a vezérlők élnek
- token-alapú generátor: bigramm, 1 bájt = 2 darab 4 bites súly,
  hőmérséklet-szavazással — a két betanult vázlatszöveg törlődött
- ALAPMAG-lánc keresés a 0x6C00-on betöltött csomagban, beépített
  KBTAB-tartalékkal, majd bigramm-továbbgenerálás
- 12 új témacsomag lefordítva (astronomy … ufo), mindegyik 1536 B alatt

## építési recept (teljes)

```
python3 eszkozok/z80asm.py motor/pico.asm kazetta/motor.bin
python3 eszkozok/z80asm.py motor/tartalek.asm kazetta/tartalek.bin
python3 eszkozok/tokenizer_train.py tudas/alapcorpus.txt kazetta/szotar.bin
python3 eszkozok/bigram_train.py tudas/alapcorpus.txt kazetta/szotar.bin kazetta/bg.bin
python3 eszkozok/trigram_train.py tudas/alapcorpus.txt kazetta/szotar.bin kazetta/tri.bin
for p in science health retro astronomy cooking entertainment future learning hobby literature movies celebrities art work ufo; do
  python3 eszkozok/kb_compile.py tudas/$p.txt kazetta/$p.bin
done
cat kazetta/szotar.bin kazetta/bg.bin kazetta/tri.bin > kazetta/szotar_full.bin
python3 eszkozok/eml_make.py kazetta/eml.bin 0:1:12:5 1:1:2:6
python3 eszkozok/z80asm.py motor/tadat.asm kazetta/tadat.bin
python3 eszkozok/sablon_keszit.py /tmp/zx81.rom
python3 eszkozok/t81_build.py kazetta/motor.bin kazetta/szotar_full.bin \
        kazetta/science.bin kazetta/PIOCO.T81 kazetta/tadat.bin \
        kazetta/tartalek.bin kazetta/boot_sablon.bin
python3 tesztek/ellenorzes.py kazetta/motor.bin kazetta/szotar_full.bin \
        kazetta/PIOCO.T81 kazetta/bg.bin kazetta/eml.bin kazetta/tadat.bin \
        kazetta/tri.bin kazetta/tartalek.bin
python3 tesztek/szalag_teszt.py /tmp/zx81.rom
python3 tesztek/kazetta_teszt.py /tmp/zx81.rom
