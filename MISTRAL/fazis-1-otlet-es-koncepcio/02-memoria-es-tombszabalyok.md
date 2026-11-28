# Memóriakorlát-összehangolás, biztonsági szabályok és tömörítés

Ez a dokumentum válaszol a mesterprompt két legérzékenyebb pontjára:
**(a)** a kért KB-arányok hogyan férnek össze a 16 KB-tal, és
**(b)** hogyan ússzuk meg a `D_FILE` és az 1 bites tárolás csapdáit.

---

## 1. A 16 KB vs. a kért arányok — az igazság röviden

A mesterprompt irányadó arányai (motor 3–5 KB, szótár 2–3 KB, chat 2–3 KB,
tudásbázis 7–10 KB) **összesen 14–21 KB** — tehát a felső végén egyszerre nem fér
be. Ez nem akadály, hanem a **multiload tervezés belső logikája**: nem mindennek
kell egyszerre a RAM-ban lennie.

### 1.1 Amit egyszerre, rezidensben tartunk (kb. 15,5 KB hasznos)

| Zóna | Méret | Jegyzet |
| --- | ---: | --- |
| Rendszerváltozók + D_FILE/UI | kb. 1,1 KB | D_FILE ≈ 793 B + SYSVARS-tartalék |
| INDÍTÓ + MOTOR (keretprogram) | ~4,0 KB | a kért 3–5 KB középértéke |
| SZÓTÁR (token+toldalék) | ~2,5 KB | a kért 2–3 KB középértéke |
| CHAT history + munkaterület | ~2,5 KB | ~30–40 üzenetvált, bitmezőkkel |
| TUDÁS ALAPMAG | ~4,5 KB | mindig rezidens indulótudás |
| PROFIL (védett, tartós) | ~0,2 KB | név/nem/szul./dátum/óra + beállítások |
| TARTALÉK (4 modul × 100 B) | ~0,4 KB | 50–150 B/module utólagos bővítéshez |
| **Összesen** | **~15,2 KB** | 16 384 B-ból, készletszámítás a 2. fázisban véglegesítve |

### 1.2 Ami kazettáról, sávcserével operál

- **TÉMACSOMAGOK** (tudomány, gasztronómia, egészség, szórakozás, retro
  korszak/technológia, jövőkutatás, tanulás, hobbi, csillagászat, irodalom,
  filmek, hírességek, művészet, munka, UFO stb.) — a **CSOMAGTERÜLET**-re
  töltödnek a helyükre, felülírva az előzőt. Az alaptudás-csomag is felülírható.
- **EMLÉKEZET-MENTÉS** — a chat/memory tartalom dátumbélyegzett blokkban
  visszamhető kazettára, a PROFIL változatlanul hagyásával.
- **Turbo/fast tape** — gyors szalag-rutin be van tervezve, de **fejlesztés
  idején inaktív/kikapcsolható** (emulátor-kompatibilitás; gyári ZX81
  sebességgel tesztelünk).

## 2. Képernyőmemória (D_FILE) mint munkaterület és a 0x76-tilalom

- A D_FILE felső harmadát (kb. 8 sor) **munkaterületként** használjuk:
  pörgő karakter-effekt, állapotsáv, reasoning-jelzés. A motor ezért a sáv
  alatti területet címezheti változóként/effekt-tárolóként — **kizárólag a
  D_FILE saját, biztonságos írásán keresztül**.
- **Szigorú szűrőszabály:** a képernyőre kerülő minden bájt átmegy egy
  **biztonsági maszk rutinen**. Beengedett tartományok: szóköz, ZX81 egyszerű
  ASCII-, grafikus- és inverzkarakter-kódok. **Kitiltva:** `0x76` (sorvég),
  minden parancskód-kifelé (PRINT, RETURN, GOTO, LIST stb.) és minden
  vezérlőkód. Ez a maszk a generálási lánc utolsó lépése, minden kiírásnál.
- A pörgő karakter-effekt is a maszkos értékhalmazból válogat, ezért soha nem
  tud "vak" parancskódot vagy `0x76`-ot a képernyőre írni — a képernyő fagyása
  konstrukciós szinten kizárva.

## 3. 1 bites tárolás és a bájt-összeállás biztonsága

- Kétállapotú tények (nő/férfi, gyerek/felnőtt, igaz/hamis, igen/nem, fáj/nem
  fáj) **1 biten** élnek egy PROFIL/EMLÉKEZET bájtban, dátumbélyeggel.
- A módosított bájt (pl. bitmező-flag) **minden mentés és minden kiírás előtt**
  így van kezelve:
  1. **érték-vizsgálat:** ha a képződő bájt véletlenül `0x76` lenne, az
     utolsó biztonsági bitet 0 → 1-re fordítjuk (árnyékolt eltolás), és ezt
     a módosítást egy párhuzamos "árnyék-zászló" bájt jelzi;
  2. **mentésnél:** a nyers bájtok az EMLÉKEZET-blokkban kerülnek kazettára —
     soha nem a `D_FILE`-ba, és soha nem kerül kiírási szövegbe.
- Így a bájt-összeállás nem tud képernyős fagyást, szétesést, képszakadást
  okozni.

## 4. Tömörítés és tartalék szabályok

| Terület | Módszer | Nyeremény |
| --- | --- | --- |
| Súlyok | 4 bites kvantálás, 1 bájt = 2 súly | kb. 50% |
| Tudáscsomag | ismétlődő/ritka értékek futóhossz-kezelése (RLE-szerű) a betöltőben | típusonként 20–40% |
| Szótár | 1 bájtos tokenek; hosszasan ismétlődő toldalékok 1 tokent kapnak | betű-alapúhoz képest több × |
| Chat history | rövid üzenetek, fejléc 1 bájton (type+suppress), szöveg 8 B-futamban csoportosítva | egyértűen kb. 30–40 üzenet fér |
| **Tartalék** | minden modul mellett 50–150 B üres | utólagos módosítás, bővítés |

A tömörítés mindig **futásidejű feldolgozhatóság mellett** dönt: ami a betöltőben
kibontásra kerül, az a RAM-ban közvetlen címezhető marad; a kazettán
**tömörített** formában él (helyet és szalagidőt nyerünk).
