# MISTRAL_v072.T81 — PIOCO AI mini nyelvi modell a ZX81-re (16 KB)

**A fájl:** `kazetta/MISTRAL_v072.T81` (15 920 B, EO81-konténer, egyetlen blokk) —
bájtpontosan azonos a szigorúan tesztelt PIOCO v2.6f kazettával (`kazetta/PIOCO.T81`),
csak az elvárt név-szabály szerint: **MISTRAL + verziószám a fájlnévben**.

## Mi ez?
Valódi, generatív mini-AI: tokenizálás, THINK-fázis, temperature, 4 bites kvantált
súlyok, bigramm/trigram-folyam. Nem sablonválasz-adó. Angol prototípus (a ZX81
egy betűkészlete miatt minden NAGYBETŰSEN jelenik meg).

## Betöltés (EightyOne vagy ZEsarUX, eredeti v1 ROM)
1. Tape > Open Tape Image → `MISTRAL_v072.T81`
2. a gépen: `LOAD ""` + ENTER — sikeres jelzés: `0 OK, 0:1`
3. azután: **RUN** (az **R** billentyű — a K-kurzor egy lenyomásra adja a szót) + ENTER
4. jön a `P I O C O  A I` splash, utána a beszélgetés.
(A sima ZX81 mentés NEM autorunol — a LOAD utáni RUN kötelező.)

## Vezérlés beszélgetés közben
SHIFT+1..4 = temperature; SHIFT+9 = reasoning (thinking sáv); SHIFT+5/6 = görgetés;
SHIFT+S = mentés; SHIFT+SPACE = megszakítás. Karaktervéd-írás: a motor 0x76-tiltással
védi a képernyőfájlt (D_FILE-biztonság).

## Memória-térkép (16 KB-n belül)
- motor (Z80 gépkód): 0x4700–0x57FF (motor.bin, 4 141 B, ORG 0x4700)
- SZOTAR szótár+bigramm+trigram: 0x5800 (1 982 B) · CHAT 0x6000 · EMSTORE 0x6700
- MUNKAT munkaterület: 0x6800 (BLINE, TOKBUF, INTENT, RESP, GENCTR stb.)
- TADAT 0x6B00 · KB 0x6C00 · KB2 0x7C00 · TARTALEK 0x7D00 · VEREM: 0x7FFF
- szalag-kép: 0x4009..0x7E00 (15 863 B), E_LINE=0x7E00, launcher: `10 RAND USR 18176`

## Igazolt (szimulátorban, valódi ROM-mal)
- LOAD "" bájtpontos; RUN → splash; WHO MADE / HAHA / CATS / DOES IT WORK / WHAT TIME
  — mind válaszol; a generálás valódi (pl. CATS → „CAT IS" — bigram-folyamból).
- Tesztek: ellenorzes.py, szalag_teszt.py, kazetta_teszt.py, beszelgetes_teszt.py, teljes_folyamat_teszt.py — PASS.

## Forráskód (teljes)
- motor: `motor/pico.asm` (+ `motor/tartalek.asm`, `motor/kb2.asm`)
- build-lánc: `eszkozok/z80asm.py`, `t81_build.py`, `t81_pzx.py`, `t81_wav.py`,
  `tokenizer_train.py`, `bigram_train.py`, `trigram_train.py`, `kb_compile.py`, `sablon_keszit.py`
- tesztek: `tesztek/` (6 fájlfolyamat)

## Tudásadatok tartalomjegyzéke
l. `MISTRAL_v072_tartalomjegyzek.md` (153 szavas szótár, kb2 kérdés-válasz adatbázis,
15 tudáscsomag kulcsszó-listákkal).

## Megjegyzés
A WHO MADE válaszszöveg jelenleg „Sandor Safar, with GLM's help." — a fájlnevek már
MISTRAL-elrendezésűek; a válaszszöveg MISTRAL-ra váltása a következő verzióban mehet.
