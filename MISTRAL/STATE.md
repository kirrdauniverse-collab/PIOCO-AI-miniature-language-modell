# MISTRAL-PROJEKT ÁLLÁSJELÉNTÉS (STATE) — utolsó frissítés: 2026-11-27

## 1. Mi ez a projekt?
Valódi, generatív mini-AI („PIOCO AI”) a Sinclair ZX81 (16 KB RAM) gépre, egyetlen
.T81 kazettafájlban. Későbbi célgépek: Spectrum, C16/64/128, Amiga, TVC, Enterprise,
Primo, HT1080Z és további retro platformok. Új otthon: `micro-ai-models-for-retro-computers`
(repó-rend: modell-felül, gép-alul → `mistral/zx-81/`). Angol prototípus.

## 2. Repók és hozzáférés
- `kirrdauniverse-collab/PIOCO-AI-miniature-language-modell` — EDDIGI MUNKAHELY (archívumba megy).
  Munkaág: `vibe/pico-ai-mistral-720f86` — ez tartalmaz MINDENT (forrás, eszközök, tesztek, kazetták).
- `kirrdauniverse-collab/ZX81-AI-micro-language-model` — régi gyűjtőrepó: CHATGPT1, GLM, GLM3, GROK1.
  A GLM3-ban van a GLM v0.6.5→v0.9.2 teljes vonala (MD5-ellenőrzött kazetták, TELJES_LELTAR, STATE 14. menet).
- `kirrdauniverse-collab/micro-ai-models-for-retro-computers` — AZ ÚJ FŐ REPÓ. 18 modell × 28 gép váz.
- Session-korlát: a vibe-session csak a PIOCO repóba írhat (403 az új repóra); ezért az átjelentkezés
  ZIP-csomaggal megy: `MISTRAL/MIGRACIO_CSOMAG_v2.zip` (617 KB, 618 fájl) — a tulajdonos webes
  drag&drop-pal tölti fel (Add file → Upload files).

## 3. Lezárt (3. fázis: kódolás+csomagolás) — MISTRAL v072 (=PIOCO v2.6f)
- Kiszállítás: `kazetta/MISTRAL_v072.T81` (15 920 B, EO81, egyblokkos kép 0x4009..0x7E00,
  E_LINE=0x7E00, launcher: `10 RAND USR 18176`), plusz PIOCO.T81/.P/.PZX/.WAV formákban.
- Motor: 4 141 B z80 gépkód @0x4700 (ORG 0x4700); szótár+bigramm+trigram 1 982 B @0x5800 (153 szó);
  CHAT-napló @0x6000; emlékezet @0x6700; munkaterület @0x6800; TADAT @0x6B00; KB @0x6C00;
  KB2 kérdés-válasz @0x7C00; TARTALEK @0x7D00; verem teteje 0x7FFF.
- Tesztek (mind PASS, valódi ZX81 ROM-mal, szimulátorban): ellenorzes.py, szalag_teszt.py,
  kazetta_teszt.py (LOAD bájtpontos + splash 12,3 szalagmp), beszelgetes_teszt.py
  (WHO MADE → „Sandor Safar…", HAHA, CATS, DOES IT WORK), teljes_folyamat_teszt.py (PZX-ből LOAD→RUN).
- Használat valós gépen: Tape→Open → `LOAD ""`+ENTER → `0 OK, 0:1` → **RUN** (R billentyű)+ENTER →
  splash → beszélgetés. Vezérlők: SHIFT+1..4 temperature, SHIFT+9 reasoning, SHIFT+5/6 görgetés,
  SHIFT+S mentés, SHIFT+SPACE megszakítás.
- Dokumentáció: `MISTRAL_v072_dokumentacio.md` + `MISTRAL_v072_tartalomjegyzek.md` (153 szó, kb2, 15 tudáscsomag).
- Forrás: `motor/pico.asm`, `motor/kb2.asm`, build: `eszkozok/*` (z80asm, t81_build, t81_pzx, t81_wav,
  tokenizer/bigram/trigram_train, kb_compile, sablon_keszit).

## 4. NYITOTT TÉMA — a v0.1 (GLM_v065) „betölt, de nem válaszol” tünet
- Tárgy: `MISTRAL/vizsgalando/MISTRAL_v001.t81` (= GLM_v065_RT16_TOPICS.t81, 259 813 B,
  sha-256: 16187115305e563952730ba3af1ca2dd51dd4e7a3c49cb7f2b4ca0e5ac682684, 17 blokkos EO81).
- Tünet (valós ROM, gyári v1): LOAD "" → 0/0 sikeres; RUN után semmi; nem válaszol.
- Diagnozis eddig: RTLOAD01 = tiszta BASIC loader (REM + PRINT-ek + `LOAD "RTBOOT1M"`);
  a motor a 2. blokkban REM-sorba rejtett Z80-kód (JP $408A); a snapshot E_LINE=0x0040 (érvénytelen);
  a gyári ROM LOAD után nem tud futó állapotot folytatni → RUN → REM → 0 OK. A 14 tudásblokk
  (RTBASE16 + 13 téma) így sosem töltődik be. A GLM3 leltárban ez „a valtozatlan tünetű alapfájl (v0.6.5)".
- Következő vizsgálat: a GLM3-as anyaggal kiegészítve (MD5SUMS, HIBA_ES_JAVITAS_TORTENET) folytatni.

## 5. Folyamatban lévő rendrakás (több modellel)
- A ChatGPT első migrációja HIÁNYOS volt: a 618 fájlos csomag NEM került fel; a 28 gép-almappa
  hiányzik a modelleknél; glm/grok/oxalpha átjárás, tájékoztató issue-k, TÖRÖLHETŐ.TXT — hátravan.
- Kiegészítő prompt átadva a tulajdonosnak a ChatGPT számára.

## 6. Szabályok (mindig érvényesek)
- Fájlnév: MISTRAL + verzió (pl. MISTRAL_v072.T81); minden kiszállításhoz: dokumentáció +
  teljes forráskód + tudás-tartalomjegyzék; rövid, tényközlő magyar kommunikáció; ne vitatkozz.
- A GitHub PAT, amit a tulajdonos egyszer a chatben megosztott: ROTÁLÁSRA VÁR (nem kerül fájlba/commitba).
