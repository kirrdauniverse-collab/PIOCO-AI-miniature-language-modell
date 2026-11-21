# Agent-viselkedés és forgatókönyvek (a mesterprompt-kiegészítés alapján)

Ez a jegyzőkönyv rögzíti, hogyan viselkedjen a PIOCO AI a konkrét helyzetekben.
Minden forgatókönyvhöz tartozik a **belső reasoning-elvárás**: a modell a
`[THINK_START]` … `[THINK_END]` fázisban dolgozza fel a helyzetet, és a választ
**saját megfogalmazásban, futásidőben** szerkeszti — soha nem beégetett sabból
válaszol.

---

## 1. Hangulat, humor, vita (beszélgetés-állapot megőrzése)

| Helyzet | Belső felismerés | Válasz-elvárás |
| --- | --- | --- |
| "you are so slow!" | ingerültség, lassúság-téma | saját megfogalmazás, a 3,25 MHz-es órajelre vagy türelemre utalva — sablon nélkül |
| "you are a genius!" | irónia/humor gyanú | önironikus, csipkelődő válasz a 16 KB-os korlátokra reflektálva |
| "PC is better than ZX81" | vita-téma, álláspont | **megőrzi az előző körök álláspontját a memóriában**, több körön át kiáll a saját nézőpontja mellett |

A vita-állapot egy bitmező-pár a CHAT/EMLÉKEZET zónában (`vita-aktív`,
`álláspont-irány`) + a téma token-kulcsa; több körön át él, amíg a téma változik.

## 2. Rajzolás (64×44 PLOT) és utólagos bővítés

- "rajzolj házat" → alakzat kirajzolása a plot-készítő rutinnal.
- "adj hozzá még egy ablakot" / "rajzolj mellé egy fát" → **nem törli** a rajzot:
  fix **vászon-zónák** + **új/hozzáadó rajzmód**; az új elem a meglévő képhez
  illeszkedik.
- A vászon-zóna leírása a munkaterületen (a rajz pixeljei a D_FILE külső
  tartalékkerületen/munkaterület-bufferben, kizárólag biztonságos karakterkódokkal
  visszaírva).

## 3. ZX81 BASIC írása és utólagos módosítása

- Rövid BASIC program írása kérésre (tárolás a motor BASIC-forrás bufferében).
- Módosítás kérésre ("más szöveg", "új sor", "sorszám szerinti csere/beszúrás",
  logikaváltás) → a ZX81 sorszámozás előnyét kihasználva: **új sorszámú sor
  beszúrása felülírja a régit**, a program többi része változatlan marad.

## 4. Időzített emlékeztető

- "emlékeztess 8 órakor, hogy induljak munkába" → a `FRAMES` (50 Hz) számláló
  értékét rögzítjük a célpillanatig; a motor minden visszatérésnél ellenőrzi
  (a `FAST`/`SLOW` mód sajátosságait figyelembe véve), és a megadott időpontban
  jelez.
- A célidőpont dátumbélyeggel, biteken, kompakt tárolásban él az EMLÉKEZET-ben.

## 5. Emlék-mentés kazettára és elavulás-kezelés

Példafolyamat ("fáj a fejem" kedden):

1. **rögzítés:** `fáj a fej` = 1 bit, dátumbélyeggel.
2. **mentés:** beszélgetés végén az EMLÉKEZET-blokk szalagra kerül, a védett
   PROFIL-adatok változatlanul.
3. **visszatérő emlékeztetés:** legközelebbi beszélgetésnél, ha releváns
   (pl. egészség-téma), a modell rákérdez: "múlik még a fejfájásod?"
4. **elavulás:** ha a válasz "elmúlt", vagy a dátumbélyeg alapján túl sok idő
   telt el a rögzítés óta → a bejegyzés **elavultként** kezelődik, és az új
   információ felülírja a régi bitet/dátumot.

## 6. Kezelőszervek (gyors-áttekintés)

| Beállítás | Billentyű |
| --- | --- |
| Hőmérséklet (1–4) | `SHIFT+1..4` |
| Reasoning ki/be | `SHIFT+9` |
| Görgetés vissza/előre | `SHIFT+5` / `SHIFT+6` |
| Mentés (RAM → kazetta) | `SHIFT+S` |
| Válasz/gondolkodás megszakítása | `SHIFT+SPACE` |

Bevitel: ZX81 ROM `INPUT` rutin karakteres módban. A csevegőpanelen **inverz
fejlécek** (időbélyeg, felhasznált tokenek, válaszidő) mindkét fél üzeneteinél,
lásd `GONDOLKODOM…` thinking-sáv.

## 7. Agent-parancsok (tervezet, a 2. fázisban véglegesítve)

| Parancs | Funkció |
| --- | --- |
| `RAJZ <objektum>` | alakzat a vászon-zónába (hozzáadó móddal) |
| `BASIC <feladat>` | rövid ZX81 BASIC program írása/módosítása |
| `EMLÉKEZZ <szöveg>` | bit/dátum rögzítés az EMLÉKEZET-be |
| `EMLÉKEZTET <idő> <szöveg>` | FRAMES-alapú időzített emlékeztető |
| `MENT` | emlékezet mentése kazettára (PROFIL védve) |
| `TÖLT <csomag>` | témacsomag betöltése kazettáról a CSOMAGTERÜLET-re |
