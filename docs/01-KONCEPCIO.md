# Pico AI — 1. fázis: Ötlet és koncepció (ZX81 16 KB)

## Mi a Pico AI?

A **Pico AI** egy rendkívül erősen korlátozott, valódi generatív nyelvmodell, amely a Sinclair ZX81 16 KB-os memóriájába fér be, és egyetlen `.T81` kazettafájlban tölthető be több sávban (multiload).

Nem sablonválaszokat ad, hanem:
- tokenizál,
- belső „gondolkodási” állapotot tart fenn,
- hőmérséklet-vezérelt generálást végez,
- és saját megfogalmazású válaszokat állít elő a rendelkezésre álló (nagyon kicsi) tudásbázisból.

## Realitásvizsgálat – 16 KB-os korlátok

A ZX81 16 KB RAM-ja (a rendszerterület és a D_FILE után) kb. **12–13 KB** szabad felhasználói területet hagy. Ezen belül kell elférnie mindennek.

### Javasolt memória-elosztás (kiindulási pont)

| Komponens                  | Célméret     | Megjegyzés |
|---------------------------|--------------|----------|
| Motor + keretprogram      | 3,5–4,5 KB  | Tokenizáló, generáló ciklus, billentyűkezelés, multiload |
| Tartós memória (profil)   | 0,3–0,5 KB  | Felhasználó neve, nem, születési adat, dátum/óra – **nem írható felül** későbbi sávokkal |
| Token-szótár + alaptudás  | 4–6 KB      | Nagyon kompakt, bit-packing + tömörítés |
| Chat history + állapot    | 1,5–2,5 KB  | Körkörös buffer, elavult információk kezelése |
| Tudásbázis (alap)         | 3–5 KB      | A többi a kazettás csomagokban jön |
| Tartalék / bővítés        | 0,3–0,8 KB  | Modulonként 50–150 bájt |

**Kulcsfontosságú kompromisszumok:**
1. A „gondolkodás” nem nagy nyelvi modell, hanem egy nagyon sekély, szabályalapú + mintakereső + hőmérséklet-zajos generáló folyamat.
2. A tudásbázis nem szöveges mondatok, hanem erősen tömörített, token-alapú, gyakran 1-bites tulajdonságokkal kiegészített struktúra.
3. A D_FILE felső része munkaterületként használható, de **tilos** a 0x76 és a parancskódok megjelenése benne.
4. A tartós profiladatok külön, védett memóriaterületen élnek, amelyet a későbbi betöltések nem írnak felül.

## Többsávos `.T81` koncepció

1. **Sáv 0 – Indító / bejelentkező**
   - Szép bejelentkező kép
   - Név: „Pico AI”
   - Üdvözlés + opcionális segítség
   - Felhasználói adatok bekérése (dátum, óra, név, nem, születési adat)
   - Ezek mentése a **védett tartós területre**

2. **Sáv 1 – Motor + alaptudás**
   - A generáló motor
   - Tokenizáló
   - Alap szótár + minimális tudás
   - A tartós adatok megőrzése

3. **Későbbi sávok / külön csomagok**
   - Tematikus tudáscsomagok (tudomány, gasztronómia, egészség, retro tech, stb.)
   - Betölthetők a tartós profil megőrzésével

## Vezérlők (SHIFT kombinációk)

- `SHIFT + 1..4` → Temperature
- `SHIFT + 9`    → Reasoning (gondolkodási mód)
- `SHIFT + 5/6`  → Chat history görgetés
- `SHIFT + S`    → Mentés kazettára
- `SHIFT + SPACE`→ Generálás megszakítása

## Következő fázisok (javasolt terv)

**2. fázis – Tervezés és dizájn**
- Pontos memóriatérkép
- `.T81` sávstruktúra és fejlécformátum
- Képernyő-elrendezés (inverz fejlécek, thinking sáv)
- Bitmezők a profiladatokhoz
- Agent / belső parancsok specifikációja

**3. fázis – Kódolás és csomagolás**
- Z80 motor
- Tokenizáló implementáció
- Multiload kezelés
- `.T81` generáló eszközök (Python oldalon a fejlesztéshez)

**4. fázis – Tudásbázis, tréning, tesztelés**
- Alaptudás felépítése
- Tematikus csomagok
- Emulátoros (EightyOne, sz81 stb.) tesztelés
- Mentés / elavult információ kezelés

---

*Ez a dokumentum a 1. fázis lezárása. A következő lépés a 2. fázis részletes tervezése.*
