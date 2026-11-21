# Mesterprompt: „Pico AI” fejlesztése — Első prioritás: Sinclair ZX81 (16 KB, `.T81`)

> A projekt irányadó dokumentuma, a projektgazda szavai szerint, változatlanul rögzítve.
> (A hozzáférési tokent szándékosan nem tároljuk a repóban.)

## 1. Szerepem és a munkamódszerem (Fontos!)

- **Nem értek a programozáshoz** (Z80 assembly, Python, bináris formátumok), és **nem akarok kézzel kódrészleteket másolgatni, összefűzni vagy csomagolni**.
- **Kész, működő Pico modellt és futtatható csomagot/eredményt szeretnék**, miközben a tervezési döntéseket és a haladást végig követni és véleményezni akarom.
- **Munkamenet és fázisok (kb. 3–4 fázis, a munka igényeihez igazítva):**
  1. **Ötlet és koncepció** (a Pico AI architektúrájának rögzítése, realitásvizsgálat és kompromisszumok tisztázása).
  2. **Tervezés, működés és dizájn** (memóriatérkép, `.T81` sávstruktúra, képernyő-elrendezés, vezérlő-billentyűk, bitmezők, Agent-parancsok).
  3. **Kódolás és csomagolás** (a motor, a segédeszközök/generátorok és a `.T81` fájl elkészítése, menet közbeni pontosításokkal).
  4. **Adatbázis-felépítés, tréningelés és tesztelés** (az alaptudás és a szakosított tudáscsomagok elkészítése, tréningelése, emulátoros/gyakorlati ellenőrzése).
- **Kommunikációs szabály:** Ne vitatkozzunk minden egyes leírt soron feleslegesen. Ha valami műszakilag másképp kivitelezhető a 16 KB-os ZX81 korlátai között, röviden, tárgyilagosan jelezd, adj működő megoldást, és haladjunk előre.

## 2. Célplatform és jövőbeli távlatok

- **Elsődleges cél (most erre fókuszálunk):** **Sinclair ZX81 (16 KB RAM)**, lehetőleg **egyetlen összefüggő `.T81` kazettafájlban**, amely több betöltési sávot/blokkot tartalmaz.
- **Későbbi portolási irányok (csak távlati megjegyzésként tartsd szem előtt, most ne ezekre építs):** Spectrum 48/128, Commodore 16/64/128, Amiga 500/1200, TVC 64, Enterprise 128, Primo 32, HT1080Z.

## 3. Kötelező működési elvárások

1. **Valódi generálás és „gondolkodás” előre megírt sablonválaszok helyett:**
   - Ne előre definiált, beégetett mondatokat adjon vissza, hanem a 16 KB-os keretekhez mérten valós következtetési/gondolkodási folyamattal, saját megfogalmazással állítson elő válaszokat.
   - Működjön a lehető leginkább egy valódi AI modellhez hasonlóan (tokenizálás, belső gondolkodási fázis, állapotfrissítés, hőmérséklet-vezérlés).

2. **Többlépcsős `.T81` betöltés és védett tartós memória:**
   - Nem kell mindent egyszerre bezsúfolni a memóriába. A `.T81` álljon több betöltési sávból/blokkból:
     - **Indító sáv:** adjon bejelentkező képet, nevezze el a Pico modellt, üdvözöljön, kérdezze meg, kérek-e használati útmutatót (és igény szerint mutassa meg vagy lépjen tovább). Kérje be a **pontos dátumot, órát, felhasználó nevet, nemet és születési adatot**, majd mentse ezeket egy olyan **tartós memóriarészbe**, amelyet a későbbi betöltések **nem írnak felül**.
     - **Következő sáv(ok):** töltse be a motort és az **alaptudás-csomagot**, megőrizve a korábban elmentett tartós adatokat.

3. **Memória-arányok és kezelőszervek:**
   - Irányadó méretarányok (a ZX81 16 KB-os realitásaihoz igazítva):
     - Motor / keretprogram: kb. **3–5 KB**
     - Tartós szótár: kb. **2–3 KB**
     - Chat history és egyéb ideiglenes adatok: kb. **2–3 KB**
     - Tudásbázis: kb. **7–10 KB**
     *(Ha a 16 KB-os ZX81-en valahol szűkös a hely, jelezd, és mutass pontos, működő elosztást a multiload/tömörítési megoldásokkal összhangban.)*
   - **Felhasználói beállítások / vezérlők (később módosíthatók):**
     - Hőmérséklet (`Temperature`): `SHIFT + 1..4`
     - Gondolkodás / érvelés (`Reasoning`): `SHIFT + 9`
     - Beszélgetés görgetése oda-vissza: `SHIFT + 5` és `SHIFT + 6`
     - Mentés: `SHIFT + S`
     - Válasz / gondolkodás megszakítása: `SHIFT + SPACE`

4. **Képernyőmemória (`D_FILE`) mint munkaterület és `0x76` / parancskód-tiltás:**
   - Használjuk ki a `D_FILE` felső harmadát munkaterületként/változókhoz/effektekhez, ahol megoldható.
   - **Szigorú szabály:** a képernyő memóriájába kerülő közvetlen adatok **nem tartalmazhatnak** olyan értékeket, amelyek a ZX81 karakterkódjában parancsokra (`PRINT`, `RETURN`, `GOTO` stb.) vagy vezérlő-/sorzáró karakterekre (`0x76` hex) mutatnak. Kizárólag üres, egyszerű ASCII/ZX81 karakter- és grafikus tartományok használhatók, hogy ne fagyjon le a gép.

5. **Egyetlen bites adattárolás (`1 bit / tulajdonság`):**
   - A kétállapotú adatok (pl. nő/férfi, gyerek/felnőtt, igaz/hamis, igen/nem, fáj/nem fáj) lehetőség szerint egyetlen biten, **egy bájton belül bináris bontással** legyenek tárolva.
   - Ügyeljünk arra, hogy a bitek összeállásából ne keletkezzen olyan érték (különösen `0x76` vagy kijelzőt/rendszert akasztó kód), amely fagyást okozhat.

6. **Tömörítés és utólagos bővíthetőségi tartalék:**
   - Alkalmazzunk érdemi tömörítési lehetőségeket ott, ahol tényleg helyet vagy szalagidőt nyerünk.
   - A főbb modulok/szakaszok mellett hagyjunk **kb. 50–150 bájt** tartalékot, ahol lehetséges, az utólagos módosítások és bővítések érdekében.

7. **Tokenizáló rendszer:**
   - Integráljunk valódi, LLM-szerű **tokenizáló** mechanizmust (irányadóan kb. **1–2 KB** körüli kerettel), hogy ne előre definiált mondatokat adjon a modell.

8. **Kazettás tudáscsomagok és tréningelő eszközök:**
   - A magnetofonkazetta (`.T81`) háttértárként működjön: az alaptudás-csomag (ami elég az induláshoz és egyszerű beszélgetéshez) felülírható legyen kazettáról speciálisabb témacsomagokkal (pl. tudomány, gasztronómia, egészség, szórakozás, retro korszak, retro technológia, jövőkutatás, tanulás, hobbi, csillagászat, irodalom, filmek, hírességek, művészet, munka, UFO stb.).
   - Szükség legyen a csomagok **tréningeléséhez** segédletre/eszközre a fejlesztés közben és a projekt elkészülte után is.

9. **Memória-mentés kazettára és elavult információ kezelése:**
   - A modell tudja elmenteni az átmeneti memóriája/emlékezete tartalmát a kazettán lévő régi adatok felülírásával (a tartós alapadatok megőrzése mellett).
   - Példa: ha kedden jelzem, hogy fáj a fejem, mentse el egy biten (`1/0`), beszélgetés végén mentse, és későbbi beszélgetésnél, ha releváns, kérdezzen rá — viszont ha elmúlt vagy sok idő telt el a betöltés óta, kezelje elavultként és írja felül új információval.

10. **Gyors szalagmentés / -betöltés (`turbo/fast tape`):**
    - Építsünk be gyors szalagkezelő rutint a lassú gyári ZX81 fájlkezelés kiváltására, **de a fejlesztés idejére tartsuk inaktívan/kikapcsolhatóan**, mert az emulátorok nem kezelik megbízhatóan.

11. **Dizájn és bevitel:**
    - Szép, hangulatos **fő-/bejelentkező kép** az indításkor.
    - A csevegőpanelen **inverz fejlécek** órabélyeggel, felhasznált tokenekkel és válaszidővel (mind a modell, mind a felhasználó üzeneteinél), továbbá hasznos státusz-/gondolkodási (`thinking`) sáv.
    - A felhasználói bevitelhez a **ZX81 ROM `INPUT` rutinját** használjuk karakteres módban.

## 4. Első lépés kérése

Kezdjük az **1. fázissal (Ötlet és koncepció)**: foglald össze röviden és érthetően a „Pico AI” ZX81-es koncepcióját a fenti pontok alapján, jelezd, hol kell okosan összehangolni a memóriakorlátokat (16 KB), és javasolj egy tiszta fázistervet a továbblépéshez!

## 5. Kiegészítés (2026-11-21) — fogalmak, tömörítés, `D_FILE`-buktatók és viselkedési példák

> A projektgazda kiegészítése a mesterprompthoz, lényegében változatlan szöveggel rögzítve; a tervezésben ezek az előírások ugyanúgy kötelezőek, mint az 1–4. pontok.

### 5.1 Alapfogalmak és működés — matek és zsargon nélkül, a Pico AI-ra vetítve

A munka során (és amikor magyarázunk) mindig tartsuk szem előtt a különbséget a **motor (keretprogram)** és a **tudástár / memória** között, és úgy magyarázzuk a döntéseket, hogy érthetőek maradjanak:

- **Token:** A szöveg feldarabolt építőköve (karakter, gyakori szótag/toldalék, gyakori szó vagy vezérlőjel). Célunk, hogy ne betűnként „pötyögjön” a modell (ami elviszi a kapacitást), és ne is csak előre megírt mondatokat mondjon, hanem szótagokból/szóelemekből építkezve tudjon saját megfogalmazást összerakni.
- **Paraméter és weight (súly):** A paraméter a modell tanulható „állítócsavarja”/kapcsolata, a súly pedig az adott kapcsolat erőssége (pozitív vagy negatív irányú ráhatás). Mivel a ZX81-en kevés a memória és nincs lebegőpontos gyorsító, a súlyokat **egész számokkal** kezeljük (**4 bites kvantálás, `-8..+7` tartomány**), és a tanításnál figyelembe vesszük a szűkítést, hogy ne essen szét a modell.
- **Temperature (hőmérséklet):** Azt szabályozza, mennyire legyen szigorúan a legesélyesebb folytatásnál a modell (`SHIFT + 1..4`), vagy mennyire merjen váratlanabb, változatosabb, játékosabb/kreatívabb megoldást választani (például a Z80 `R` regiszterét és a `FRAMES` számlálót bevonva), anélkül hogy szétesne a válasz.
- **Reasoning (gondolkodás / érvelés):** Nem azonnali válaszadás, hanem egy belső „elő-feldolgozó” lépés (`[THINK_START]` és `[THINK_END]` között): a modell belső kulcsszavakat/asszociációkat/állapotokat forgat meg a rejtett/munkaállapotában, mielőtt kiírja a tényleges választ vagy végrehajt egy Agent-parancsot.

### 5.2 Tömörítés, sűrítés és a „16 KB vs. kért KB-arányok” összehangolása

- A ZX81-ben **16 KB RAM** áll rendelkezésre (a rendszerváltozók és a kijelzőkezelés mellett). Ha az arányokat (motor, szótár, chat history/ideiglenes tár, tudásbázis) összeadjuk, látszik, hogy egyszerre nem fér be minden a 16 KB-ba.
- **A megoldásunk kulcsa:**
  1. **Multiload `.T81` sávok:** egyetlen `.T81` fájlban több egymást követő blokk szerepel (`BOOT` → motor + alaptudás → témacsomagok/overlay-k), és a betöltések **átugorják/megőrzik** a védett tartós memóriát (`PERSIST_BLOCK`).
  2. **Sűrítés / kvantálás / ritkítás:** ahol érdemi helyet vagy szalagidőt nyerünk (például 1 bájton 2 darab 4 bites súly tárolása, ismétlődő/nulla értékek okos kezelése, szótári/mintabeli tömörítés), ott alkalmazzuk — de mindig ügyelve arra, hogy a tömörítés ne tegye használhatatlanná a futásidejű feldolgozást, és hagyjunk **50–150 bájt** mozgásteret/tartalékot a főbb modulok mellett az utólagos javításokhoz és bővítésekhez.

### 5.3 A `D_FILE` (képernyőmemória) és az 1 bites tárolás buktatói

- **Miért különösen kényes a ZX81?** A képernyőmemóriában (`D_FILE`) a **`0x76` (118 decimális)** érték speciális jelentéssel bír (sorvég/vezérlő viselkedés), és a ZX81 karakterkód-világában a parancs-/vezérlőkódok vagy hibás értékek a képernyőn **fagyást, képszakadást vagy szétesést** okozhatnak.
- **„Pörgő karakterek” és `D_FILE` felső harmada:** Szeretjük a klasszikus, látványos indulási/állapotjelző látványt (ahogy a régi gépeken pörögnek a karakterek a képernyő tetején), és szeretnénk kihasználni a `D_FILE` felső harmadát munkaterületként/változókhoz is — **de kizárólag `0x76`-tól és veszélyes parancs-/vezérlőkódoktól mentes értékekkel**, biztonságos tartományra szűrve.
- **1 bites flagek és bit-összeállítás:** Kétállapotú infókat (nő/férfi, gyerek/felnőtt, igaz/hamis, igen/nem, fejfájás fáj/nem fáj) tegyünk **1 bitre** egy bájton belül. Ugyanakkor ha több bitből áll össze egy bájt (különösen, ha képernyőhöz vagy kiíráshoz/tároláshoz kapcsolódik), ellenőrizzük, hogy ne álljon össze belőle `0x76` vagy más fagyást okozó érték.

### 5.4 Részletes példák a viselkedésre és az Agent-működésre

- **Hangulat, humor, vita:**
  - Ha ingerülten szólunk be (pl. *„you are so slow!”*), a belső gondolkodásban vegye észre a feszültséget/lassúságot, és saját megfogalmazásban reagáljon (például a 3,25 MHz-es órajelre vagy türelemre utalva), ne sablonnal.
  - Ha humorral/iróniával ugratunk (pl. *„you are a genius!”*), tudjon önironikus, csipkelődő választ adni a 16 KB-os korlátokra reflektálva.
  - Ha vitatkozunk (pl. *„PC is better than ZX81”*), őrizze meg az előző körök álláspontját/témáját a memóriában, és álljon ki a saját nézőpontja mellett több körön át.
- **Rajzolás (`64×44` `PLOT` / alakzatok) és utólagos bővítés:**
  - Ha azt kérjük, rajzoljon házat, rajzolja meg; ha utána azt kérjük, *„adj hozzá még egy ablakot”* vagy *„rajzolj mellé egy fát”*, **ne törölje le** a meglévő rajzot, hanem a meglévőhöz illesztve (fix vászon-zónákkal és új/hozzáadó rajzmóddal) egészítse ki.
- **BASIC program írása és utólagos módosítása:**
  - Tudjon rövid ZX81 BASIC programot írni, és ha később módosítást kérünk (pl. más szöveg, új sor, sorszám szerinti csere/beszúrás vagy logikaváltás), tudja frissíteni a meglévő programot a ZX81 sorszámozásának előnyeit kihasználva.
- **Időzített emlékeztető és memória-mentés / elavulás:**
  - Emlékeztető példa: *„emlékeztess 8 órakor, hogy induljak munkába”* — a `FRAMES` (50 Hz) számlálóra építve (a `FAST`/`SLOW` mód sajátosságait is figyelembe véve) jelezzen a megadott időpontban.
  - Memória-mentés és elavulás példa: ha kedden jelzik, hogy fáj a fejük, mentse el egy biten (`1/0`), mentse el a beszélgetés végén a kazettán a védett alapadatok megtartásával; ha legközelebb beszélgetünk és releváns, kérdezzen rá — de ha elmúlt vagy túl sok idő telt el, kezelje elavultként és írja felül új információval.
- **Gyors szalagkezelés és dizájn:**
  - Legyen benne gyors szalagmentés/-betöltés rutin, de a fejlesztés alatt maradjon inaktív/kikapcsolható az emulátor-kompatibilitás miatt.
  - A csevegőpanelen legyenek **inverz fejlécek** (időbélyeg, felhasznált tokenek, válaszidő) mind a felhasználó, mind a modell üzeneteinél, látható gondolkodási (`thinking`) jelzéssel, és a bevitel történjen a ZX81 ROM `INPUT` rutinjával karakteres módban.

Kezdjük el az **1. fázist (Ötlet és koncepció)** ezekkel a kiegészítésekkel együtt!

