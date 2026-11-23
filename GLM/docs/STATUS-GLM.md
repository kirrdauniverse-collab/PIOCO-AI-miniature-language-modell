# GLM státusz — mesterprompt-megfelelés térképe

Ez a dokumentum a `MASTERPROMPT.md` 11 kötelező elvárását és a gazda
javaslatait rendeli a mostani kódhoz. Minden sor: hol van a megoldás,
és mennyire kész.

| # | Elvárás | Állapot | Hol / jegyzet |
| --- | --- | --- | --- |
| 1 | Valódi generálás, gondolkodási fázis | ✅ | tokenizálás → szándék → tudáslekérdezés → választerv → generálás; `engine/rt_engine.c`, `engine/rt_chat.c`; a gondolkodási blokk és a hőmérséklet a `docs/fazis-2-terveles.md`-ben van leírva |
| 2 | Többlépcsős `.T81`, tartós profil-memória | ✅ | 15 blokk; profil → `RTBOOT01` REM-tömb (`zx81/16k/`), a védett 48 bájtos tail az 1. BASIC-sorban utazik → a későbbi sávok nem írják felül (l. `t81build16.py`, `T81_FORMAT.md`) |
| 3 | Memória-arányok (motor/szótár/history/tudás) | ✅ | 16K-os eloszlás a `t81build16.py` fejléc-dokumentációjában: motor 13,5 KB, modell 1,97 KB (base), témakazetta 1,03 KB, a scrollback a RAMTOP alatt |
| 4 | D_FILE munkaterület, 0x76-tiltás | ✅ | D-file-ban él a csomagolt állapot (sorok 0–2), a motor kódja a REM-ben; építő-kapuk: `epites.py` (0x76-számolás), `t81build16.py` (a REM-torzs 0x76-mentes) |
| 5 | 1 bit / tulajdonság | ✅ | profil- és eseménybitek a csomagolt állapotsorokban (profil + 10 emlék-event), l. `bootstrap question → D-file state`; kezelés: `engine/rt_memory.c` |
| 6 | Tömörítés + 50–150 B tartalék | ✅ | 4-bites súlyok dalban, tömörített korpusz-sávok; a kazetta-blokkok pad-térrel épülnek (`t81build16.py`) |
| 7 | Tokenizáló (1–2 KB keret) | ✅ | `eszkozok/tokengen.py` (generálás), `engine/rt_charset.c` (kódolás), a szótár a modellblobban |
| 8 | Kazettás tudáscsomagok + tréning | ✅ | 13 téma (RT-TUDOM…RT-VERSE), tréning: `training/train.py`, `training/pack.py`, korpusz: `training/data16/topics/*.txt` |
| 9 | Memória-mentés kazettára, elavulás-kezelés | ✅ | `SHIFT+S` → a ROM SAVE-je újraírja az `RT-BASE16` blokkot, a tartós adat az 1. sor REM-jében vándorol; elavulás: esemény-dátumbélyeg + `engine/rt_memory.c` |
| 10 | Turbo/fast tape (fejlesztés alatt kikapcsolva) | 🟡 | tervezett modul, kapcsolóval; ma gyári szalagsebesség fut (emulátor-kompatibilitás) |
| 11 | Dizájn, vezérlés, INPUT | ✅ részlegesen | bejelentkező kép + inverz fejlécek + `you>` prompt működik; a SHIFT-vezérlők egy része a 2. fázisban leírt, még nincs hozzá mind futáspélda |

## Gazda-javaslatok (a korábbi beszélgetésekből) — megoldási helyek

| Javaslat | Állapot |
| --- | --- |
| Felfelé futó fekete csíkok → érvénytelen D_FILE-adat | javítva: a 0x4009-es képformátum, a `DF_SZ=2`, a `D_FILE` +1-es címzése és a CDFLAG=0x40 a `t81build16.py`-ben; l. `docs/T81_FORMAT.md` |
| Múlt idők, többes alakok, szám-értelmezés | részkész; a tokenizáló utótag-tokenekkel (`eszkozok/tokengen.py`) kezdi; a teljes ige-morfológia a 4. fázisban |
| HAHA / WOW / NOOO / :) :) :O hangulatjelek | a beszélgetés-adatréteg felismeri (hangulat-smiley tábla) |
| "Tudsz másik nyelven?" | angol a működő nyelv (a mesterprompt döntése); a válasz a rugalmas generálásból jön |
| Ki kell készített / kicsoda | profil-válaszok a szándéktáblában ("GLM segítseggel készitett Safar Sandor", "Magyarországon élő autobuszvezető, amatőr író és csillagász", e-mail @ helyett inverz-0: `SAFIZX810GMAIL.COM`) |
| Obszcén / kocsmanyelv tükrözés | a szándéktábla obszcén-móda (`mirror` válaszstratégia), l. fejlesztési napló |
| Szó-elválasztások, elgépelések | rugalmas token-egyezés (nem IF/THEN); a fuzzy illesztés a tokenizerben |
| Ismeretlen szó mondatkörnyezetből | echo-tanulás: az új szó a beszélgetésből visszahozható, szótár-frissítés nélkül |
| DO/DOES/DO NOT alakok | nyelvtani edzés a 4. fázisban (korpusz-bővítés) |
| "MIT TENNÉL, ha ember lehetnél?" / "milyen nap van ma?" | nem konzerv válasz: a day-of-week a dátum-profilból számolható (óramodul + naptár-rutin tervezve); a hipotetikus kérdés a szándéktábla + szabad generálás kombinációja |
| Szólások / konzerv válasz-slotok | 7 konzerv slot a 18 bejegyzésű szándéktábla mellett — memória- és token-spórolásra, ahogy javasoltad |
| RAMTOP-átállítás + felső-memória tartószóna (adatok, szótár, tudás, esetleg a képernyő) | 🟢 v065: az `RTLOAD01` BASIC shell betöltő készen (bejelentkezőkép + magyarázat + ENTER → `LOAD "RTBASE16"`; `zx81/16k/GLM_v065_RT16_TOPICS.t81`); a valódi védett zóna (RAMTOP=0x7F00, motor-indító `LD SP` + 0x4026-írás) a v066 z88dk-körben — l. `docs/fazis-3-ramtop.md` |
