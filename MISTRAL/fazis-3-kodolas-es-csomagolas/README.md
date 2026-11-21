# 3. fázis — Kódolás és csomagolás (MISTRAL munkaterület)

**Állapot:** első működő kivágás; v2: vezérlők + bigramm-generátor ✅ — a teljes eszközlánc futtatható,
a `PIOCO.T81` legyártott és automatikusan ellenőrzött.

---

## Mit ad ez a fázis?

| Elem | Fájl | Állapot |
| --- | --- | --- |
| Z80 motor (forrás) | `motor/pico.asm` | összeáll, **1 819 bájt** (v2) (zóna-határ: 4 096 B) |
| saját Z80-összeállító | `eszkozok/z80asm.py` | kétmenetes; a motor készletén fut |
| tokenizáló-tanító | `eszkozok/tokenizer_train.py` | szövegből szótár-blob (111 token / 740 B + bigramm 550 B) |
| tudáscsomag-fordító | `eszkozok/kb_compile.py` | kulcsszó+tény sorok → bináris lánc |
| `.T81` építő | `eszkozok/t81_build.py` | PI-mágnesjelű blokkok + PROFIL/0x76-védelem |
| füstvizsgálat | `tesztek/ellenorzes.py` | 8 ellenőrzés: méret, mágnesjel, XOR, PROFIL, RAM-határ, 0x76-tiltás, szótárforma, bigrammforma |
| tudásforrások | `tudas/*.txt` | alapkcorpusz + 15 témacsomag-forrás (angol prototípus) |
| kész kazetta | `kazetta/PIOCO.T81` | **4 144 B, 5 blokk** (BOOT, MOTOR, SZÓTÁR, ALAPMAG, témacsomag) |

## Hogy épül? (teljes, 4. fázis szerinti)

```
python3 eszkozok/z80asm.py motor/pico.asm kazetta/motor.bin
python3 eszkozok/tokenizer_train.py tudas/alapcorpus.txt kazetta/szotar.bin
python3 eszkozok/bigram_train.py tudas/alapcorpus.txt kazetta/szotar.bin kazetta/bg.bin
for p in science health retro astronomy cooking entertainment future learning hobby literature movies celebrities art work ufo; do
  python3 eszkozok/kb_compile.py tudas/$p.txt kazetta/$p.bin
done
cat kazetta/szotar.bin kazetta/bg.bin > kazetta/szotar_full.bin
python3 eszkozok/t81_build.py kazetta/motor.bin kazetta/szotar_full.bin \
        kazetta/science.bin kazetta/PIOCO.T81 kazetta/science.bin SCIENCE
python3 tesztek/ellenorzes.py kazetta/motor.bin kazetta/szotar_full.bin \
        kazetta/PIOCO.T81 kazetta/bg.bin
```

## Mit tud már a motor (v2)?

- indulás: PROFIL mágnesvizsgálat → alap-értékek feltöltése (védett zóna),
  splash + üdvözlet névvel
- saját, biztonságos D_FILE-kezelés minden print-nél (0x76 és 0xC0+ kód
  **tiltása futáskor is**, nem csak építéskor)
- teljes 8 soros billentyűzet (ENTER + SHIFT), felengedés-várással;
  SHIFT+1..4 hőmérséklet, SHIFT+9 érvelés, SHIFT+S mentés-stub,
  SHIFT+SPACE megszakítás
- karakteres sorbevitel, tokenizálás (szótár-találat vagy betűtokenek),
  szándékfelismerés (REASON)
- token-alapú generálás: bigramm 4 bites súlyokkal, hőmérséklet-szavazással
- tudáskeresés: ALAPMAG-lánc (0x6C00) → beépített KBTAB → bigramm

## Nyitott pontok (a 4. fazis emulatortesztje veglegesiti)

A 4. fazis egy reszet mar elkeszult: teljes 8 soros KEYTBL + ENTER,
SHIFT-vezerlok es bigramm-generator (olasd:
`../fazis-4-tudas-trening-teszt/05-vezervek-es-nagygenerator.md`).

- ASCII -> ZX81 karakterkod-tabla (ASCTAB) vegso ertekei
- ROM-INPUT kapcsolo (a sajat editor marad az alapertelmezett)
- turbo tape engedelyezese (a blokkformatum mar tamogatja; bit = FLAG-A bit3)
- görgetés (SHIFT+5/6) bekötése; EMLEKEZET (06-os) blokkirás

## Tervezett témacsomag-lista (a 4. fázisban tréningelvek)

tudomány, gasztronómia, egészség, szórakozás, retro korszak/technológia,
jövőkutatás, tanulás, hobbi, csillagászat, irodalom, filmek, hírességek,
művészet, munka, UFO — mindegyik `tudas/*.txt` forrásból `kb_compile.py`-val.
