# Hiba- és javítási napló — MISTRAL ág (PIOCO)

A teljes változatlista a régi repó (`PIOCO-AI-miniature-language-modell`, ág
`vibe/pico-ai-mistral-720f86`) commit-történetéből, hibaleírásokkal és javításokkal.

## Lezárt fázisok
| Változat | Commit | Mit hozott | Hiba/jelenség → javítás |
| --- | --- | --- | --- |
| 1. fázis (koncepció) | `73dfa9a` | memória/tömörítés koncepció, agent-viselkedés, fázisterv | — |
| 2. fázis (tervezés) | `78a0582` | végleges 16 384 B memória-térkép, T81 blokkformátum, bitmezők, képernyők | — |
| 3. fázis (első működő) | `e402f54` | Z80 motor (1066 B), saját assembler, tokenizer-tanító, t81-építő, tesztek, PIOCO.T81 (5 blokk) | — |

## 4. fázis kezdete (tudás/vezérlés)
| Commit | Mit hozott | Hiba → javítás |
| --- | --- | --- |
| `3b5a7a0` | nyelvváltás angol prototípusra (szótár 661 B), SCIENCE/HEALTH/RETRO csomagok | — |
| `d653d33` | vezérlők (SHIFT-parancsok ENTER+release), bigramm-generátor 4 bites súlyokkal (212 átmenet), összesen 15 témakör | DICTLOOK, BGGOTO hibajavítás |
| `1548934` | emlékezet (0x6700): 4 bájtos emlékrekordok (max 63), dátum-bekérés, 14 napos elavulás, SHIFT+S belyegzés | — |
| `1ab7a73` | CHAT-napló (0x6001) + SHIFT+5/6 görgetés, 0x76-védett sortörés, válaszidő-mérés | — |
| `051bac0` | naptár-modul (2000–2099 hetnap, 36 525 nap tesztelve, 0 hiba), TIME/DAY intentek, képzelet-modul (IF/WOULD/COULD/WISH), TADAT-blokk | — |
| `8f1d424` | trigram-lépés (TRIGOTO/TRIINIT), BGCHOOSE-javítás, TARTALEK-blokk | bg csoport-vegjel hiba |

## A kritikus szakasz: „betölt, de C/6 / nem fut” korszak
| Commit | Hiba (tünet) | Javítás |
| --- | --- | --- |
| `3ab12ba` | a korábbi, elméleti tesztek nem látták a valódi ROM viselkedését | valódi ZX81 szimulátor + szalag-protokoll teszt bevezetése |
| `7d87c48` | **C/6** hiba: ROM LOAD után a program nem indult; oka: több-blokkos, nem összefüggő kép + assembler RET cc hiba + CALCUR A-regiszter-megőrzés + ROM-hu VARS-elrendezés | **single-image EO81 kazetta**, mindhárom motorhiba javítva, tesztek áírva |
| `12ad064` | v2.6b: **wild-jump** (a motor az interpretáció közben verem-egyensúlyt vesztett) | TOKSTRIP verem-egyensúly javítás |
| `3f16cc6` | v2.6c: DERAIL #2–#5: REASON/KBWALK/FACTSET/KWGTAB mutató-szken, BGWORD token-ID, ASC2ZX kisbetű-fold | mind öt derail javítva; beszélgetés-teszt végig zöld |

## Kiszállítás-korszak (LOAD "" → RUN)
| Commit | Hiba/tünet | Javítás |
| --- | --- | --- |
| `1b88b47` (v2.6d) | néhány emulátor gyorstöltője a konténerfejlécet 0x4009-re írva „azonnali újraindítást” okozott | hivatalos EightyOne EO81/T81 formátum (zx81-név, bit7-es lezáró, entry = adat+név) + `PIOCO.P` univerzális gyorstöltő |
| `f09c7ab`+`2f11f5d` (v2.6e) | WAV-szalag nem ismert fel a valós szalagbeolvasóval (időzítés a szabvány fele sem) | impulzus 150+150 µs, bit 4/9 impulzus, bit után 1300 µs csend; szigorú WAV-dekódoló roundtrip-igazolás (15 868 B OK) |
| `132780f`+`9f9ddec` (v2.6f) | „betölt, és utána semmi” — a felhasználónál a RUN hiányzott (a ZX81 mentés nem autorunol) | README: LOAD "" → `0 OK, 0:1` → **RUN** (R billentyű); PZX kiszállítás; teljes_folyamat_teszt: a kiszállított PZX-ből LOAD+RUN → splash, PASS |

## MISTRAL név-szabály
| Commit | Mit hozott |
| --- | --- |
| `ca48831`, `9e0c1fd` | `MISTRAL_v072.T81` (a v2.6f-fel bájtpontosan azonos) + dokumentáció + tudás-tartalomjegyzék; WHO MADE válaszszöveg még „with GLM's help” — következő verzióban MISTRAL-ra váltandó |

## A külső (belinkelt) v0.1 kazetta vizsgálata — NYITOTT téma
Tárgy: `vizsgalando/MISTRAL_v001.t81` (17 blokkos EO81-konténer, 259 813 B).
**Tünet (a felhasználónál, gyári v1 ROM-mal):** betölt (`0/0` sikeres), RUN után is — **nem válaszol a kérdésekre**; a javítások eddig nem változtattak ezen.
**Diagnozis eddig:**
1. `RTLOAD01` = tiszta BASIC loader (REM + PRINT-ek + `LOAD "RTBOOT1M"`), USR/semmilyen gépkód-hívás nincs benne.
2. A válasz-motor a 2. blokkban REM-sorba rejtett Z80 gépkód (JP $408A) — a snapshot `E_LINE=0x0040` (érvénytelen cím).
3. A gyári ZX81 ROM a LOAD után mindig újrarekonstruál és a szerkesztőbe tér vissza; futó állapotot nem tud folytatni → RUN → REM → `0 OK`, semmi.
4. A tudás a 14 további szalagblokkban van (multiload), ami így sosem töltődik be.
**Következő vizsgálat:** ebből a fájlból indulunk újra.
