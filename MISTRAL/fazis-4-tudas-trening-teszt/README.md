# 4. fázis — Tudás, tréning, tesztelés (MISTRAL munkaterület)

**Állapot:** futóvá tett vezérlés, generátor **és emlékezet**. A
`PIOCO.T81` **5079 B, 6 blokk**, kilencféle automatikus vizsgálat zöld
(szótárforma, bigrammforma + emlékforma is).

## Mappa

- `01-nyelvvaltas-dontes.md` — az angol prototípusra váltás rögzítése
- `02-trening-utmutato.md` — kód nélküli tréning: `tudas/x.txt` → `kb_compile.py`
- `03-emulatoros-teszt-terv.md` — az A–F emulátoros ellenőrzőlista
- `04-kesz-csomagok.md` — csomag-állapotok + a tervezett témák
- `05-vezervek-es-nagygenerator.md` — bekötött SHIFT-vezérlők,
  teljes billentyűzet ENTER-rel, bigramm-generátor 4 bites súlyokkal
- `06-emlekezet-es-mentes.md` — **új**: 4 bájtos emlékrekordok a 0x6700-on,
  dátum-bekérés, fakt-felismerés, 14 napos elavulás, SHIFT+S

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
python3 eszkozok/tokenizer_train.py tudas/alapcorpus.txt kazetta/szotar.bin
python3 eszkozok/bigram_train.py tudas/alapcorpus.txt kazetta/szotar.bin kazetta/bg.bin
for p in science health retro astronomy cooking entertainment future learning \
         hobby literature movies celebrities art work ufo; do
  python3 eszkozok/kb_compile.py tudas/$p.txt kazetta/$p.bin
done
cat kazetta/szotar.bin kazetta/bg.bin > kazetta/szotar_full.bin
python3 eszkozok/eml_make.py kazetta/eml.bin 0:1:12:5 1:1:2:6
python3 eszkozok/t81_build.py kazetta/motor.bin kazetta/szotar_full.bin \
        kazetta/science.bin kazetta/PIOCO.T81 kazetta/science.bin SCIENCE \
        kazetta/eml.bin
python3 tesztek/ellenorzes.py kazetta/motor.bin kazetta/szotar_full.bin \
        kazetta/PIOCO.T81 kazetta/bg.bin kazetta/eml.bin
```

A kazettán a B4-ALAPMAG a tudás (most science), a B5-CSOMAG a cserélhető
téma (most szintén science, igazából: bármelyik másik .bin-re cserélhető).
