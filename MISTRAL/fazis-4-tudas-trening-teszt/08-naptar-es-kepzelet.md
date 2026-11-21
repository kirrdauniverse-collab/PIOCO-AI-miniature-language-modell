# 08 — Naptár és képzelet (v2.3)

**Állapot:** kész, az összes ellenőrzés zöld. Motor: **4 052 B** (tartalék 44 B a
4 096-os motorzónán belül), kazetta: **6 755 B / 7 blokk**.

Ez a lépés megvalósítja a beszélgetésben egyeztetett négy(elemű) bővítést:

1. év-bekérés + hét-név számítása,
2. „what day is today" és „what time is it" válaszok,
3. képzelet-modul (imagination),
4. FACTTAB-kiegészítés.

(Az egészet egyeztettük: a **trigram-tábla** szándékosan a KÖVETKEZŐ lépés —
új adateszközt és táblaformátumot igényel, biztos helyről.)

---

## 1. Naptár: év + héttag

- **Év-bekérés**: az induló dátum-kérdés mostantól `enter date as dd mm yy:` —
  az év megadása *opcionális* az első dátumban. Ha nincs meg (vagy korábban
  dátum nélkül lett használatban), a boot megkérdezi:
  `enter year as yy:` és addig ismétli, amíg 0–99 közötti szám nem jön.
  **Tárolás:** `PROF_YR = PROFIL+0x26` (1 B, `0xFF` = nincs meg — a 0 az
  érvényes 2000-es év!).

- **DOWGET** (visszatér A = 0..6, 0 = vasárnap; `0xFF` = nincs év):
  Zeller-egyszerűsítés a 2000–2099-es évszázadra. Mivel J = 20 esetén
  5·J + J/4 = 105, ami 7-tel osztva 0-t ad, a képlet:

  ```
  A = (nap + TAB13[m'] + K + K/4 + jan2000-korrekció) mod 7
  ```

  ahol m' = év kezdeti hónap (január/februárnál m' += 12 és K = yy−1);
  a csak 2000. január/februárnál negatívra forduló K-t K = 99 + 1
  korrekciós bit helyettesíti.
  A TAB13 táblát a teljes 2000–2099 tartományra **brute-force** ellenőriztük
  a Python `calendar` moduljával: **36 525 dátum, 0 hiba**. Ugyanezt a számítást
  a Z80-algoritmus pontos szimulációjával is lefuttattuk (ugyanúgy 0 hiba).
  A számítás 8 bites (max összeg 167, nem csordul túl) — 16 bites matek nélkül.

- **BOOTD**: induláskor, ha dátum+ev megvan, kiírja:
  `it's sunday 06 12 09` (napnév + nap-hónap; az évet a kiírásból a
  helymegtakarítás miatt elhagytuk — a tárolásban megvan).

- **Válasz-vezérlés**: `intent 6` = „what day" (TODAY/DATE szavakra),
  `intent 7` = „what time" (TIME szóra). Ha nincs meg az év, a modell nem áll le:
  sima generálással válaszol (ugyanaz a magatartás, mint más
  tudásnélküli kérdésnél).

## 2. „What time is it?" — pontosan mi ez?

Session-óra: a bekapcsolás óta eltelt idő a 50 Hz-es FRAMES-ből:
FRAMES/50 = másodpercek → /60 → perc:másodperc formában a válaszba.
Ez szándékos egyszerűsítés (nem valós óra) — később ROM-alapú
beállításra válthatjuk.

## 3. Képzelet-modul (imagination)

Ha a sor kimondott vagy rejtett `IF`, `WOULD`, `COULD`, `WISH` szót tartalmaz
(KWGET szavankénti ellenőrzéssel, kis-/nagybetűt fittyenhagyva), a motor
`IMAGF = 1` jelzőt állít (INTENT nem változik). A GENERATE eljárás — ha
IMAGF = 1 — az `IMAGPICK`-et hívja: ez egy véletlen szót választ az `IMAGSEED`
(DREAM / HUMAN / MAYBE / SOMETHING) táblából, szótári tokenre fordítja
(DICTLOOK), és a GENERÁTOR ezzel a tokennel indul a megszokott
ATTN/STARTSEED elágazás helyett. Az eredmény: a válasz a képzelet-tematikájú
bigramm-kapcsolatokból épül fel — nem beégetett mondat, hanem a
betanult átmenet-háló más indulópontról indítva.

- Sikeresen: az `IMAGSEEDT`-token lesz az **első** válasz-szó; a BGWRITE
  ATTN/STARTSEED ága ilyenkor ki sem érhető — a seed felülírása nem lehetséges.
- Ha a seed-szó nincs a szótárban (pl. szótár-újratraining elmaradása), a
  válasz sima generálás.
- A jelző és a seed-token is törlésre kerül egy válasz után.

## 4. FACTTAB-kiegészítés (bitkódok 3–6)

| szó | bitkód | megjegyzés |
| --- | --- | --- |
| SLEEP | 3 | Új |
| TIRED | 4 | Új |
| HUNGRY | 5 | csak az emlékezetzónában (a MASKOF a PROFIL FLAGB-be csak 0–4-es bitkódot enged — a 0x76-tilalmi szabályunk miatt) |
| ANGRY | 6 | ugyanúgy csak az emlékezetzónában |

Az 5–6-os bitkód a 0x76-tilalmi szabály biztonságán belül marad: a PROFIL
FLAGB-be sosem kerül — csak az emlékezetzóna 4 bájtos rekordjaiba.

## 5. Új memóriazóna: TADAT (0x6B00)

A motorzóna (0x4600–0x55FF) kész volt telítődni. A motorzónán kívül, a
PB-munkaterület és az ALAPMAG-zóna közé került egy **fix adattábla-blokk**:

```
TADAT  =  0x6B00   (07-as blokk-típus a .T81-ben)
TAB13      TADAT+0x00   15 B
DOWTAB     TADAT+0x0F   28 B (SUN/MON/TUE/WED/THU/FRI/SAT, 4 B-ig)
TXTDAYP    TADAT+0x2B    6 B ("it's ")
TXTTIS     TADAT+0x31    9 B ("time is ")
WTAB       TADAT+0x3A   12 B (TODAY, DATE)
TIMTAB     TADAT+0x46    6 B (TIME)
IMAGTAB    TADAT+0x4C   21 B (IF, WOULD, COULD, WISH)
IMAGSEED   TADAT+0x61   28 B (DREAM, HUMAN, MAYBE, SOMETHING)
```

Forrás: `motor/tadat.asm`; a motor csak EQU-címeken hivatkozik rá. Az
`ellenorzes.py` 6. opcionális argumentumával ellenőrizzük, hogy a
beégetett bájtok bájtponosan megfelelnek a pico.asm EQU-eltolásaival
számított szövegeknek — a táblakiosztás így nem csúszhat el észrevétlenül.

## 6. Szótár és korpusz

Az `alapcorpus.txt` kapott 5 új sort (if/would/could/wish/dream/human/maybe/
something/today/time együttjátszva), így a szótár **129 token / 852 B**,
a bigramm-tábla 655 B (270 átmenet) lett. A vezérszavak (TODAY/DATE/TIME/IF…)
felismerése **BLINE-alapú** (KWGET), nem szótári — a naptár-válasz akkor is
él, ha egy szó kiesne a szótárból.

## 7. Bruttó mérlege

| elem | előtte | utána |
| --- | --- | --- |
| motor | 3 557 B | 4 052 B (tartalék: 44 B) |
| szotar_full | 1 290 B | 1 507 B |
| tábla-blokk (TADAT) | — | 125 B (0x6B00-on; az ALAPMAG-ig 256 B a zóna) |
| kazetta | 5 907 B / 6 blokk | 6 755 B / 7 blokk |

A motor ezzel a lépéssel igazán telített lett (44 B tartalék — az irányadó
50–150 B alsó határa alá csúsztunk). A következő lépésben a TADAT zóna
256 bájtja ad még mozgásteret a trigram-táblának, ha az oda is megfér.

## 8. Ismert határok (tisztességesen)

- A v2.3 **előtt** mentett régi PROFIL-ban a PROF_YR inicializálatlan maradhat —
  ekkor a motor 2000-et (0) vél, és a kiszámolt hét-név a valóságtól el lehet.
  Új alapértelmezésnél a default-writer `0xFF`-et ír, és a boot bekéri az évet.
- Az óra session-idő — gép-hívás (ROM) nélkül nem valós órát mutat.
- A napi BOOTD-kiírásban az év nem jelenik meg (hely; a tárolásban megvan).
- A DOWGET 8 bites, byte-bontású (a saját assembler-készletünknek megfelelően:
  `LD DE,(nn)` stb. nincs) — ez egyben gyors is.
