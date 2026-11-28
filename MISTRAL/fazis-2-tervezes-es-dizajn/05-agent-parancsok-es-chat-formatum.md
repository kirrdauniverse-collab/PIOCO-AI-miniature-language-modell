# Agent-parancsok és chat-rekordformátum (2. fázis)

---

## 1. Agent-parancsok (végleges névtábla)

| Parancs | Szintaxis | Funkció | Tárolás |
| --- | --- | --- | --- |
| `RAJZ` | `RAJZ <objektum>` | alakzat a 64×44 plot-vászonra, **hozzáadó módban** (ami már ott van, megmarad) | vászon MUNKATERÜLET-ben |
| `BASIC` | `BASIC <feladat>` | rövid ZX81 BASIC program írása; módosításnál új sorszámmal felülírja a régi sort | program MUNKATERÜLET-ben |
| `EMLÉKEZZ` | `EMLÉKEZZ <szöveg>` | kétállapotú tény rögzítése biten + dátumbélyeg | EMLÉKEZET-bitrekord |
| `EMLÉKEZTET` | `EMLÉKEZTET <óra[:perc]> <szöveg>` | `FRAMES`-alapú időzített emlékeztető | cél-FRAMES MUNKATERÜLET-ben |
| `MENT` | `MENT` | emlékezet szalagra; PROFIL változatlan | `.T81` blokk 06 |
| `TÖLT` | `TÖLT <csomagnév>` | témacsomag betöltése a CSOMAGTERÜLET-re | `.T81` blokk 05 |
| `TURBO` | `M TURBO BE/KI` | gyors szalagrutin engedélyezése (fejlesztés alatt: KI) | FLAG-A bit3 |

- A parancsfelismerés a tokenizálónál történik: a parancs-tokenek a SZÓTÁR
  vezérlősávjában élnek (nem új táblát fogyasztanak).
- A `RAJZ` pozícióit a vászon **zónaként** kezeli (ház = zóna A, az "új ablak"
  a zónán belül, a "fa" a mellette lévő szabad zónába kerül).

## 2. Chat-rekordformátum (CHAT zóna, 0x6000–0x67FF)

Minden üzenet egy rekord, sorban egymás mögött:

```
+0: fejléc 1: bit7 = küldő (0=felhasználó, 1=PIOCO),
              bit6 = volt reasoning fázis,
              bit5 = tartalmaz agent-parancsot,
              bit4 = elavultnak jelölt,
              bit3 = folytatás (lapozott válasz része),
              bit2..0 = hőmérséklet szintje a keletkezéskor (1–4)
+1: fejléc 2: óra az alsó 5 bitben (0–23), perc/2 a felső 3 bitben (2 perces pontosság)
+2: token-szám (alsó 7 bit: 0–127; a bit7: örökretartás-jelzés)
+3: szöveghossz bájtokban (tokenekhez igazítva)
+4…: tokenek (1 bájt/token), 0-val zárva
```

- **Fejrősség per rekord:** 4 bájt + szöveg. Kapacitásszámítás:
  ~2048 B / (~13 B átlag) ≈ **kb. 150 rövid üzenet** csúcs; gyakorlatban
  **30–40 tartalmas üzenetváltás** fér el nagyobb hosszban — a régi végsor
  szalagra gördül, ha a zóna betelik (MENT és törlés).
- **Időbélyeg:** a `FRAMES`-ből és a belépés pillanatából képződik (a fast/slow
  módok különbségeit a motor kezeli).
- **Elavulás:** bit4 jelöli; a `EMLÉKEZZ`-rekordokkal összefüggő üzenetek
  az elavulás után relevanciát veszíthetnek, a motor rákérdezhet.

## 3. Reasoning állapotgép (MUNKATERÜLET, vázlat)

```
[THINK_START]
  1. SZÁNDÉK: kérdés / állítás / parancs / beállítás felismerése
  2. ENTITÁSOK: név, hely, téma, idő kinyerése
  3. TUDÁS-LÉPÉS: ALAPMAG- vagy CSOMAGTERÜLET-indexkeresés
  4. VÁLASZTERV: vázfeltöltés (szám/név/dátum behelyettesítés)
[THINK_END] → generálás a választási top-k halmazon (hőmérséklet szerint)
```

- A lépés-jelzők kiírása csak FLAG-A bit4 engedéllyel megy a GONDOLKODOM… sávba.
- A gondolkodási állapot **soha nem kerül a képernyőre nyers formában** — csak a
  maszkolt, leegyszerűsített változata jelenhet meg.
