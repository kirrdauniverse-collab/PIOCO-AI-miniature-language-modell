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
