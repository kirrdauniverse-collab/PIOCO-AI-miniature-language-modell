# PIOCO AI — 1. fázis: ötlet és koncepció (MISTRAL munkaterület)

**Célplatform:** Sinclair ZX81 · 16 KB RAM · Z80 @ 3,25 MHz · egyetlen, több
betöltési sávot tartalmazó `.T81` kazettafájl
**Kiegészítést beépítő változat:** igen (többek között D_FILE/0x76, 1 bites
tárolás, agent-viselkedés, turbo tape — inaktív)

---

## 1. A koncepció egy mondatban

A PIOCO AI egy miniatűr, **valóban generáló** nyelvi modell a ZX81-en: a bejövő
szöveget **tokenizálja**, belső **gondolkodási fázison** (`[THINK_START]` …
`[THINK_END]`) visz át, állapotot frissít, majd a tömörített tudásbázisra és
mini nyelvi modelljére támaszkodva **futásidőben maga szerkeszti és toldalékolja
a választ**, hőmérséklet-vezérléssel és kazettás tudáscsomagokkal — mindez a
16 KB RAM-on belül.

## 2. Alapfogalmak laikusan, a PIOCO-ra vetítve

**Motor vs. tudástár.** A **motor** a keretprogram (az "elme gépe"), a
**tudástár/memória** pedig az adat, amit a motor olvas és ír. A tudást cserélni
lehet kazettáról, anélkül hogy a motor változna.

- **Token:** a szöveg feldarabolt építőköve (karakter, gyakori toldalék, gyakori
  szó, vezérlőjel). A PIOCO nem betűnként "pötyög", és nem beégetett mondatokat
  ad: **szóelemekből, toldalékokból építi a saját megfogalmazást**. Keretméret:
  kb. 400–460 token, 1 bájt/token; az ismeretlen szó betű-tokenekre bontható,
  tehát mindent "el tud olvasni".
- **Parameter és weight:** a paraméter a tanulható "állítócsavar", a súly az
  adott kapcsolat ereje. A ZX81-en nincs lebegőpontos gyorsító, ezért a súlyok
  **egész számosak, 4 bites kvantálással (-8…+7)**, és 1 bájton **két súly utazik
  együtt**. Tanításnál a kvantálás szűkítését figyelembe vesszük, hogy a modell
  ne essen szét.
- **Temperature:** a választási véletlen szintje (`SHIFT+1..4`). 1 = mindig a
  legerősebb jelölt (tényszerű); 4 = szélesebb választás (kreatív). A véletlent
  a Z80 `R` regiszter és a `FRAMES` (50 Hz) számláló keverékéből nyerjük a
  ZX81 saját, hardverszerű forrásairól. Szélesítésnél is mindig top-k keret
  marad, hogy **a válasz ne essen szét**.
- **Reasoning:** nem azonnali válaszadás, hanem belső elő-munka a
  `[THINK_START]` … `[THINK_END]` jelölések között: kulcsszavak, asszociációk,
  állapotok forgatása a rejtett munkaterületen, mielőtt a válasz kikerül vagy
  agent-parancs hajtódik végre. Kijelzése a `GONDOLKODOM…` sávban, SHIFT+9-gyel
  ki/be.

## 3. Realitásvizsgálat — mi fér be a 16 KB-ba

| Paraméter | Érték | Következmény |
| --- | --- | --- |
| CPU | Z80 @ 3,25 MHz | egészsámos, táblázatos számítás; interpoláció nincs |
| RAM | 16 KB (0x4000–0x7FFF) | rendszerváltozók + D_FILE (kb. 793 B) levonandó |
| ROM | 8 KB BASIC | `INPUT` (karakteres mód), `PRINT`, szalagrutinok újrahasznosítása |
| Háttértár | kazetta (`.T81`) | tudás/emlékezet "virtuálisan nagy": sávcserével (multiload) |
| Képernyő | 32 × 24 karakter | tömör, rövid válasz; gördítés; inverz fejlécek |

**Mit nem ígérünk:** neurális háló fizikailag nem fér be (1 M paraméter ≈ 1 MB,
az a ZX81 címterének 64-szerese). Ezért a PIOCO **miniatűr, valós generálású
nyelvi motor**: statisztikai (n-gram) nyelvi modell + magyar toldalékolás +
váz-alapú szövegszintézis + indexelt tudásbázis. A hatás, amit a mesterprompt
kér, megvan: a válasz **futásidőben, újrakomponálva** születik, nem
visszakeresett mondat.

## 4. Generálási lánc lépésről lépésre

1. **Tokenizálás** — szóalap- és toldaléktokenekre bontás (`-ban/-ben`,
   `-nak/-nek`, `-ra/-re`, `-val/-vel`, `-t`, `-ok/-ek/-ök` stb.).
2. **Reasoning** — 3–5 lépés: szándékfelismerés → kulcsentitások (név, hely,
   téma, idő) → tudáslekérés → választerv. Élőben látható a `GONDOLKODOM…` sávban.
3. **Generálás** — n-gram (2–3 szó kontextus) + **vázak** (behelyettesíthető
   résekkel: számok, nevek, dátumok) együtt rakják össze az újrakomponált választ.
4. **Hőmérséklet** — top-k szűkítés/kiszélesítés (`SHIFT+1..4`).
5. **Állapotfrissítés** — kétállapotú tények **1 bitre** kerülnek dátumbélyeggel
   (pl. "fáj a fej" = 1), elavulás-kezeléssel (lásd `03-agent-es-viselkedes.md`).

## 5. Architektúra — modultérkép

```
┌────────────────────────────────────────────────────────────────────────┐
│                     .T81 KAZETTA (multiload)                           │
│ [S1 INDÍTÓ] [S2 MOTOR+ALAPTUDÁS] [S3..N TÉMACSOMAG] [M EMLÉKEZET-MENTÉS]│
└────────────────────────────────────────────────────────────────────────┘
                 │ multiload — célzott címekre tölt, a PROFIL sávot átugorja
┌────────────────────────────────────────────────────────────────────────┐
│           ZX81 · 16 KB RAM (0x4000–0x7FFF)                             │
│ SYSVARS │ PROFIL (védett) │ D_FILE/UI │ MOTOR │ SZÓTÁR │ CHAT │ TUDÁS ││
│         │ ALAPMAG │ CSOMAGTERÜLET │ MUNKATERÜLET │ TARTALÉK            │
└────────────────────────────────────────────────────────────────────────┘
```

| Modul | Feladat |
| --- | --- |
| INDÍTÓ (Sáv 1) | splash kép + pörgő karakterek, név, üdvözlet, útmutató-kérdés; profil-kérdezés (pontos dátum, óra, név, nem, születési adat); mentés a védett PROFIL blokkba |
| MOTOR | tokenizálás, generálás, reasoning, hőmérséklet, UI, szalag-I/O |
| SZÓTÁR | token ↔ szöveg táblák + toldalékkódok |
| TUDÁS | ALAPMAG (mindig rezidens) + CSOMAGTERÜLET (témacsomagok sávcserével) |
| EMLÉKEZET | chat history + bitmezők + dátumbélyegek + elavulás-kezelés |
| PROFIL | tartós, védett blokk: név, nem (1 bit), születési adat, dátum/óra, beállítások — **a későbbi betöltések nem írják felül** |

Részletes memória-összehangolás és biztonsági szabályok:
`02-memoria-es-tombszabalyok.md`.
