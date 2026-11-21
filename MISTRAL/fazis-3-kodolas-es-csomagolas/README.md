# 3. fázis — Kódolás és csomagolás (MISTRAL munkaterület)

**Állapot:** első működő kivágás ✅ — a teljes eszközlánc futtatható,
a `PIOCO.T81` legyártott és automatikusan ellenőrzött.

---

## Mit ad ez a fázis?

| Elem | Fájl | Állapot |
| --- | --- | --- |
| Z80 motor (forrás) | `motor/pico.asm` | összeáll, **1 066 bájt** (zóna-határ: 4 096 B) |
| saját Z80-összeállító | `eszkozok/z80asm.py` | kétmenetes; a motor készletén fut |
| tokenizáló-tanító | `eszkozok/tokenizer_train.py` | szövegből szótár-blob (91 token / 776 B) |
| tudáscsomag-fordító | `eszkozok/kb_compile.py` | kulcsszó+tény sorok → bináris lánc |
| `.T81` építő | `eszkozok/t81_build.py` | PI-mágnesjelű blokkok + PROFIL/0x76-védelem |
| füstvizsgálat | `tesztek/ellenorzes.py` | 7 ellenőrzés: méret, mágnesjel, XOR, PROFIL, RAM-határ, 0x76-tiltás, szótárforma |
| tudásforrások | `tudas/alapcorpus.txt`, `tudas/tudomany.txt` | mintakorpusz + TUDOMANY + TUDOMANY témacsomag |
| kész kazetta | `kazetta/PIOCO.T81` | **2 931 B, 5 blokk** (BOOT, MOTOR, SZÓTÁR, ALAPMAG, témacsomag) |

## Hogy épül? (3 sor)

```
python3 eszkozok/z80asm.py motor/pico.asm kazetta/motor.bin
python3 eszkozok/tokenizer_train.py tudas/alapcorpus.txt kazetta/szotar.bin
python3 eszkozok/kb_compile.py tudas/tudomany.txt kazetta/tudomany.bin
python3 eszkozok/t81_build.py kazetta/motor.bin kazetta/szotar.bin kazetta/tudomany.bin \
        kazetta/PIOCO.T81 kazetta/tudomany.bin TUDOMANY
python3 tesztek/ellenorzes.py kazetta/motor.bin kazetta/szotar.bin kazetta/PIOCO.T81
```

## Mit tud már a motor (v1)?

- indulás: PROFIL mágnesvizsgálat → alap-értékek feltöltése (védett zóna),
  splash + üdvözlet névvel
- saját, biztonságos D_FILE-kezelés minden print-nél (0x76 és 0xC0+ kód
  **tiltása futáskor is**, nem csak építéskor)
- karakteres sorbevitel, tokenizálás (szótár-találat vagy betűtokenek),
  szándékfelismerés (REASON), vázlat-választás R+FRAMES véletlennel,
  kulcsszó–tény keresés az alaptudásból

## Nyitott pontok (a 4. fázis emulátortesztje véglegesíti)

- billentyűzet bit–karakter térkép (`KEYTBL`) és ENTER-kezelés
- ASCII → ZX81 karakterkód-tábla (`ASCTAB`) végső értékei
- token-alapú generátor leváltja a v1 szöveges vázakat
- ROM-INPUT kapcsoló (a saját editor marad az alapértelmezett)
- turbo tape engedélyezése (a blokkformátum már támogatja; bit = FLAG-A bit3)

## Tervezett témacsomag-lista (a 4. fázisban tréningelvek)

tudomány, gasztronómia, egészség, szórakozás, retro korszak/technológia,
jövőkutatás, tanulás, hobbi, csillagászat, irodalom, filmek, hírességek,
művészet, munka, UFO — mindegyik `tudas/*.txt` forrásból `kb_compile.py`-val.
