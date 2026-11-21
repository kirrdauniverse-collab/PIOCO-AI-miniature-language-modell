# Végleges memóriatérkép — ZX81, 16 KB (2. fázis)

**Érvényesség:** ez a bontás a 3. fázis kódolásának alapszerződése. A zónák
**folytonosan** lefedik a 0x4000–0x7FFF területet, összesen pontosan
**16 384 bájt** (számítással ellenőrizve).

---

## 1. Zónatábla

| Címtartomány | Zóna | Méret | Jegyzet |
| --- | --- | ---: | --- |
| `0x4000–0x40FF` | SYSVARS | 256 B | ZX81 rendszerváltozók (motor csak olvassa/kezeli; FRAMES, D_FILE pointer) |
| `0x4100–0x41FF` | PROFIL (védett) | 256 B | tartós felhasználói adatok + beállítások; a multiload **soha nem írja felül** (védettség: `0x4100`-as mágikus bájt ellenőrzésével) |
| `0x4200–0x45FF` | UI / D_FILE | 1024 B | D_FILE (793 B) + inverz fejlécek, thinking sáv, pörgő karakter-zóna; felső harmad munkaterület-használatra a 0x76-maszkkal |
| `0x4600–0x55FF` | MOTOR | 4096 B | tokenizáló, generátor, reasoning, hőmérséklet, UI-logika, saját loader |
| `0x5600–0x5FFF` | SZÓTÁR | 2560 B | token ↔ szöveg táblák + toldalékkódok (kb. 400–460 token) |
| `0x6000–0x67FF` | CHAT | 2048 B | beszélgetés-előzmények rekordokban (lásd `05-agent-parancsok-es-chat-formatum.md`) |
| `0x6800–0x6BFF` | MUNKATERÜLET | 1024 B | tokenizer-puffer, n-gram kontextus, reasoning állapotgép, rajz-vászon leírók |
| `0x6C00–0x77FF` | TUDÁS · ALAPMAG | 3072 B | mindig rezidens indító tudás; indexelt tételek |
| `0x7800–0x7DFF` | TUDÁS · CSOMAGTERÜLET | 1536 B | erre a területre töltődnek a kazettás témacsomagok (felülírják az előzőt) |
| `0x7E00–0x7EFF` | TARTALÉK (közös) | 256 B | utólagos bővítés; ezen felül minden nagyobb zóna belső tartalékot őriz |
| `0x7F00–0x7FFF` | VEREM + STOPPER | 256 B | Z80 verem (felülről lefelé nő) + leállítás/indítás bélyegek |

## 2. Arányok vs. a mesterprompt igénye

| Mesterprompt igény | Tervezett elosztás | Megjegyzés |
| --- | --- | --- |
| Motor/keretprogram 3–5 KB | 4,0 KB | a képzett középérték |
| Tartós szótár 2–3 KB | 2,5 KB | ~400–460 token fér rá kényelmesen |
| Chat + ideiglenes 2–3 KB | 2,0 + 1,0 = 3,0 KB | CHAT rekordok + MUNKATERÜLET |
| Tudásbázis 7–10 KB | **4,5 KB RAM-ban** (ALAPMAG + CSOMAGTERÜLET) | **ez az egyetlen valódi kompromisszum:** a 7–10 KB tudás a kazettán él — témacsomagonként 7–10 KB, szekciókra bontva, és a CSOMAGTERÜLET-en cserélődnek; egyszerre mindig ~4,5 KB van élve (rezidens ALAPMAG + éppen betöltett szekció) |
| Tartalék 50–150 B/module | 256 B közös + modulon belüli 8 B-párok a nagy zónák végén | utólagos javítás/bővítés helye |

## 3. Verem és kritikus pointer-egyeztetések

- **SP induló értéke:** `0x7FFF` (a VEREM-zóna teteje); a zóna 256 B standard
  feltöltésjelezett (`0xB7`-mintázat), így a tényleges veremmélység futás
  közben is ellenőrizhető.
- **PROFIL védelem mechanizmus:** minden loader-blokk megkapja a
  **célzónát és a méretet** a `.T81` blokkfejlécekből (lásd
  `02-t81-savformatum.md`); a betöltés előtt a motor ellenőrzi a
  célzásokat a **PROFIL védelmi összehasonlítóval** — ha egy blokk bármilyen
  byte-a `0x4100–0x41FF` tartományba esne, a betöltés **megszakad** és
  felhasználói figyelmeztetés jön. Így a PROFIL védelme **a formátumon és a
  rutinokon** alapul, nem a "szándékon".
- **D_FILE pointer:** a motor a `0x4200`-t állítja be D_FILE-nak; a BASIC
  nem kapja vissza a vezérlést addig, amíg a modell fut (a motor
  saját főciklust futtat, a bevitel a ROM `INPUT` karakteres rutinján megy).

## 4. Multiload terület-átfedések (tiltás-nyilvántartás)

| Betöltési blokk | RAM cél | Ütközik-e más blokkal? |
| --- | --- | --- |
| S1 INDÍTÓ + PROFIL-kérdés | MOTOR + UI | nem (induláskor, egyszer) |
| S2 MOTOR + SZÓTÁR + ALAPMAG | MOTOR + SZÓTÁR + ALAPMAG | nem, **PROFIL-t átugorja** |
| S3..S_n TÉMACSOMAG | CSOMAGTERÜLET | egymást felülírják (arra szolgálnak) |
| M EMLÉKEZET-mentés/vissza | CHAT | visszaállítás CHAT-re; PROFIL nem érintett |

## 5. Nyitott kérdések a 3. fázisra

- A pörgő karakter-effekt pontos sorkijelzési frekvenciája (interrupt vs.
  FRAMES-felülírás; FAST/SLOW viselkedés).
- A CSOMAGTERÜLET-en belüli szekcióhatárok finomhangolása, ha egy témacsomag
  4 KB-nál nagyobb szekciókat igényelne — ilyenkor **két részlettel töltünk**.
