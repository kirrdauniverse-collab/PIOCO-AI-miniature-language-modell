# 3. fázis — Kódolás és csomagolás (MISTRAL munkaterület)

**Állapot:** v2.6c — **single-image kazetta** (valódi ROM SAVE-kép, ROM LOAD ""-val betölthető),
minden teszt zöld (`szalag_teszt`, `kazetta_teszt`, `ellenorzes`, `beszelgetes_teszt`).
A v2.5 elrendezés a C/6 hiba okát szüntette meg (l. `t81_build.py` fejléc):
a ZX81 ROM LOAD rutinja csak egyetlen összefüggő képet tud betölteni
(0x4009-től a szalagon lévő E_LINE-ig, nálunk 0x7E00-ig).

---

## Mit ad ez a fázis?

| Elem | Fájl | Állapot |
| --- | --- | --- |
| Z80 motor (forrás) | `motor/pico.asm` | összeáll, **4 141 bájt** (v2.6c) (zóna: 0x4700–0x57FF = 4 352 B) |
| saját Z80-összeállító | `eszkozok/z80asm.py` | kétmenetes; a motor készletén fut (SBC/ADC HL,rr; RET cc javítva) |
| tokenizáló-tanító | `eszkozok/tokenizer_train.py` | szövegből szótár-blob (111 token / 740 B + bigramm 550 B) |
| tudáscsomag-fordító | `eszkozok/kb_compile.py` | kulcsszó+tény sorok → bináris lánc |
| `.T81` építő | `eszkozok/t81_build.py` | **EO81-konténer, single image** (0x4009..0x7E00), launcher-sor + PROFIL/0x76-védelem |
| boot-sablon gyártó | `eszkozok/sablon_keszit.py` | a valódi ROM bootjából kimért telepedett állapot (698 B, determinisztikus) |
| végponti teszt | `tesztek/kazetta_teszt.py` | konténer + **valódi ROM LOAD ""** (bájtpontos) + rendszerváltozók + motor-boot (splash) |
| szalag-protokoll teszt | `tesztek/szalag_teszt.py` | EAR-atmenetsoros LOAD valódi ROM-mal |
| füstvizsgálat | `tesztek/ellenorzes.py` | EO81-konténer, E_LINE=0x7E00, launcher-sor, rendszerváltozók, D_FILE/0x76-védelem, zónák bájtpontossága, szótár/bigramm/trigram/eml/tadat formák |
| derail-nyomkövető | `tesztek/trace_motor.py` | motor single-step diagnosztika (az első ROM-PC-ig) |
| tudásforrások | `tudas/*.txt` | alapcorpusz + 15 témacsomag-forrás (angol prototípus) |
| kész kazetta | `kazetta/PIOCO.T81` | **15 921 B, EO81 single image** (kép: 15 863 B = 0x4009..0x7E00) |

## Hogy épül? (teljes, 4. fázis szerinti)

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
```

A szimulátortesztekhez a valódi ZX81 ROM szükséges (szerzői jogvédett, nem
kerül a repóba): `/tmp/zx81.rom` (8 192 B).

## A C/6 hiba okai és a v2.5 javítás (röviden)

1. **Formátum:** a régi szétszórt, célcímzett blokkos `.T81` a ROM LOAD-erőltetés
   miatt **elvileg sem** volt betölthető (NEXT-PROG 0x0347 egyetlen összefüggő
   képet vesz, 0x4009-től a szalagon lévő E_LINE-ig). → single image.
2. **Assembler-hiba:** a saját `z80asm.py` a `RET cc` opkódokat félbemaradt
   JP-bájttal helyettesítette (pl. `RET Z` → lone `d2`), ami a motorban
   repedéssé nőtt (EMINIT: `JP NC,0x2521`-lel került a motor ROM-ba).
   Javítás: külön `COND_RET` tábla (0xC0/0xC8/0xD0/0xD8).
3. **Motorhiba:** az `ASC2ZX` a betű kódját A-ban adja, de PUTA-ban a
   `CALL CALCUR` felülírta A-t (utolsó művelete `LD A,(DFCOL)`), ezért a
   képernyőre a kurzor-oszlop került a szöveg helyett. Javítás: CALCUR
   megőrzi A-t (`PUSH AF`/`POP AF`).
4. **Képernyő-biztonság:** a builder a VARS 0x80-bájtja a képernyő-lezáró
   0x76-ot írta felül; a SLOW-módos képernyőfrissítés valódi gépen itt
   furcsult meg. Javítás: ROM-hű elrendezés — a D_FILE-lezáró 0x76 ép,
   a VARS a maga 0x80-bájtjára mutat (0x439C), az edit-stub (7F 76 00)
   utána, STKBOT=STKEND a stub után (boot-mért).
5. **PROFIL-védelem:** a szalagon lévő E_LINE = **0x7E00** → a LOAD ténylegesen
   sosem ír a 0x7E00..0x7FFF (PROFIL) zónára; a tartós mentést a motor
   SHIFT+S kazettaíró-rendszere kezeli.

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
SHIFT-vezerlok es bigramm-generator (olvasd:
`../fazis-4-tudas-trening-teszt/05-vezervek-es-nagygenerator.md`).

- ASCII -> ZX81 karakterkod-tabla (ASCTAB) vegso ertekei
- ROM-INPUT kapcsolo (a sajat editor marad az alapertelmezett)
- turbo tape engedelyezese (a blokkformatum mar tamogatja; bit = FLAG-A bit3)
- görgetés (SHIFT+5/6) bekötése; EMLEKEZET (06-os) blokkirás

## Tervezett témacsomag-lista (a 4. fázisban tréningelvek)

tudomány, gasztronómia, egészség, szórakozás, retro korszak/technológia,
jövőkutatás, tanulás, hobbi, csillagászat, irodalom, filmek, hírességek,
művészet, munka, UFO — mindegyik `tudas/*.txt` forrásból `kb_compile.py`-val.

## v2.6c állás — WHO MADE-válasz kiírva, beszélgetés-végponti teszt zöld

**Ez a kör négy, egymáshoz kapcsolódó mutató-logikai hibát tárt fel és javított** —
mindnek a gyökere az volt, hogy a kereső rutinok (KWDEQ/KWGET/KWGTAB) a
regisztereket a hívás elején megőrzik (PUSH/POP), a hívó kódja viszont úgy
íródott, mintha a kereső **előre léptetné** a bejegyzés-mutatót:

1. **REASON** (intent-kereső): a RE_NOM csak 2× INC DE lépéssel haladt tovább,
   ezért a tábla második bejegyzés után lezáró 0-ba botlott, és a 13 keyword
   (WHO, HAHA, DO…) közül csak kettő ment át — így a "WHO MADE" intentje
   sosem lett 2 (GEN_KB). A javítás: 0-szken az aktuális bejegyzés végéig.
2. **KBWALK/KW_H**: találatnál egyetlen INC HL után PRTLN — a kulcsszó
   második betűjétől írta volna a szöveget ("HO MADE"). A javítás: 0-szken.
3. **FACTSET/FS_NX** és **KWGTAB/KGT_S**: dupla INC → bejegyzés-szken
   elcsúszás (a "WHAT DAY IS IT TODAY" felismerést tette volna tönkre).
4. **BGWORD/DICTAPP**: a token-ID elvész (LD A,(RESPW) felülírja a token
   után), a DICTAPP a 0-indexet kereste → üres RESP. A javítás egyetlen
   utasítás: LD A,(BGFROM) a CALL előtt.

Plusz a **DERAIL #2** (a session eleji javítás, commitolva ezzel együtt):
DICTLOOK verem-egyensúly — a találati ág a DL_CMP-keret 6 PUSH-ját bontja
fel jó sorrendben, a DL_MISS a prologusz 3 PUSH-ját (BC/HL/DE sorrend).

Megjavítottuk továbbá az **ASC2ZX**-t: a KB2-válaszok vegyes betűesei a
64 bájtos tábla mögé olvastak ("with GLM's help" → szemét). A kisbetűk most
nagybetűre fordulnak, 32 alatti kód szóköz (a ZX81 egy betűkészletet ismer).

**Igazolás (kazetta_teszt boothívásával, valós gombnyomásokkal):**
WHO MADE → "SANDOR SAFAR, WITH GLM'S HELP", HAHA → "HAHA! GLAD",
CATS → bigram-generált "CAT IS", DOES IT WORK → "YOU THE", WHAT TIME →
"TIME IS 00:00", inverz YOU/PIOCO fejlécek, a D_FILE a beszélgetés alatt
jogszerű (0x76-tiltás, 0xC0+ nincs). Mind a négy teszt PASS.

**Kanonikus kazetta szinkron:** a repó-gyökér `kazetta/`-ban az új
motor.bin (4 141 B) + PIOCO.T81 (15 921 B) megvan.

**Nyitott (4. fázis):** a kreatív-kérdés vizsgálat ("what day" naptár-modul,
IF/WOULD képzelet-sortervek), a felhasználói dátum-bekérés finomítása,
és a generált válaszok minőségének javítása nagyobb corpus-indexelt.
