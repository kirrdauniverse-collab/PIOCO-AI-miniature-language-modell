# 3. fázis bővítés — A felső memória: RAMTOP-trükk és védett tartószóna (v066-terv)

Bevezető ötlet (a gazdától): a szalag **elejére** egy egyszerű BASIC betöltő kerül,
ami röviden ismerteti a programot és a működését, felhívja a figyelmet, hogy
a felső memória aktiválása újraindítást igényel, és ENTER-re a rendszer átnézi
a RAMTOP-ot és NEW-t futtat; az utána felszabaduló felső területre kerülhet
minden tartós dolog — adatok, szótár, tudás, D_FILE átállítás esetén akár a
képernyő is.

## 1. Amit a gyári ROM-ból megállapítottunk (ellenőrizve a zx81 ROM dumpán)

- A teljes ROM-ban az SP újrabeállításának egyetlen forráscíme
  `LD SP,(0x4002)` (ERR_SP) — `LD SP,(0x4026)` (`LD SP,(RAMTOP)`) **egy
  helyen sincs benne**. A 0x4026 szót az emulátor quickload használja
  SP-forrásként, a gyári ROM maga nem.
- Következés: a `POKE 16422,0 : POKE 16423,124 : NEW` sorozat önmagában
  **nem** ad rom-szintű védelmet — a NEW után az SP a régi (magas) helyén
  marad, és az editori/verem-működés megszennyezheti az ott beírt adatot.
- Ezért a védett tartószóna tényleges beüzemelése **motor-indításbeli gépi
  kóddal** történik (motor-induláskor `LD SP,<ramtop>` + a 0x4026 szó
  beállítása), nem BASIC POKE-okkal. A BASIC-betöltő a bevezető és az
  irányítás szerepét játssza — ezt a v065 már le is szállítja (`RTLOAD01`).

## 2. Mi van már MOST a v064/v065-ben (ténylegesen védett tartalom)

- A gyári ROM szalagos LOAD **nem ír az E_LINE fölé** (a v0.6.4 javítás
  erről szólt): minden blokk-kép E_LINE-nál lezárul.
- A base FULL kép (RTBOOT01/RTLOAD01, 15 889 B) 0x7E19-ig ér (utolsó bájt;
  a következő szabad cím 0x7E1A = E_LINE), a topic SHORT képek 0x7ADC-ig
  (következő szabad cím 0x7ADD) — tehát a **0x7E1A fölötti sávot egyetlen mai
  blokk sem írja felül betöltéskor**: ebből a tartószónak a
  **0x7F00-0x7FFC sávot (253 bájt) választjuk**, a 0x7E1A-0x7EFF (230 B)
  tartományt a ROM/verem-kelléknek hagyjuk tartalékként. Ez **valódi
  tartószóna**, túlél minden betöltést és NEW-t (áramszünetig).
- A v064-es csomagolt állapotsorok a D-file-ban élnek, és a SHORT betöltők
  szintén nem írják őket felül (ez a meglévő, működő emlékezet).

## 3. v066-os célkiépítés (z88dk-újrafordítást igényel)

| Elem | Cím | Jegyzet |
| --- | --- | --- |
| RAMTOP (0x4026) | `0x7F00` | a motor induláskor `LD SP,0x7F00`; a quickload SP ugyaninnen jön |
| Védett tartószóna | `0x7F00-0x7FFC` | 253 B: profil-másolat (48 B), tanult szavak, esemény-bitek, zóna-jelző |
| D_FILE | `0x7A00` körül áthelyezve | a ROM a D_FILE-rendszerváltozóból dolgozik → HAL-kompatibilis; CLS megőrzi a geometriát |
| Motor + altint | `0x4082-0x79FF` | változatlan logika, csak címhatárok tolódnak |
| Modell | a lánc legvégén (RTLM-varázs) | a szótár és a tudás a motor boot közben másolódik a **védett sávba** — a ROM LOAD mindig 0x4009-ről tölt, közvetlen felső-betöltés csak a (kikapcsolt) turbo-tape-mal lesz |

## 4. D_FILE a felső memóriában? (a gazda kérdése)

Igen, elvileg mehet: a ROM a D_FILE/0x4029-féle rendszerváltozóból dolgozik,
a HAL szintén — a geometria és a scroll séma a sávnak megfelelően érintetlen
marad. Fenntartások: (1) a CLS törli a tartalmat (a geometriát nem), (2) az
alsó 2 szerkesztőisor (DF_SZ=2) a D-file alját foglalja, (3) a mesterprompt
4. pontjának 0x76-tilalma a képernyőre kerülő **aktív tartalom** forrásainál
mindig él.

## 5. Nyitott pontok (a következő z88dk-körben megigazítandók)

1. A motor C-stack mélységének mérése menet közben (SP-csúcs) — a 0x7F00-as
   RAMTOP szűkíti; a mérés a ROM-szimulátorban vagy emulátorban a v0.6.3-as
   méréstechnikával megy.
2. FP(0) öt bájtos kódolása (POKE 16422,0) — a v065 BASIC-ben egyelőre nincs
   szám-literál, ez a v066 POKE-körben válik fontossá.
3. A LOAD-név egyezés után a rendszer-állapot (VARS/E_LINE) összhangja a
   SHORT blokkoknál a v0.6.4-ben bizonyított recept szerint marad.

## 6. Hogy áll ez most össze (v065)

- `RTLOAD01` = az **első blokk**: a shell bemutatkozása + ENTER: a programsor
  `LOAD "RTBOOT1M"` fut — a v0.6.4-ben valós emulátorban igazolt,
  programon belüli LOAD-név-minta. Az `RTBOOT1M` a boot-sáv mid-lánc
  változata: egyetlen mezőben tér el, az NXTLIN (0x4029) 0x7B00 → 0x407D
  javítás (a short_image-recept); enélkül a mid-program betöltést követő
  folytatás a képernyőfájl-kópia szavára futott volna.
- INDOK (valós emulátor-megfigyelés): shell → RTBASE16 egyenesen = a motor
  banner + prompt jó, de VÁLASZ nincs — a profil/állapotsorok a boot-ból
  jönnek; a lánc ezért boot-első lett (RTLOAD01 → RTBOOT1M → RTBASE16).
- Az eredeti RTBOOT01 blokk is a kazettán marad (solo használatra), a
  15 v064-es blokk **változatlanul** utazik; a solo `GLM_v065_rtload.p`
  gyorsteszt-képként is készül.
- A szabad tartószóna (0x7E1A fölött, választott zóna 0x7F00-0x7FFC) megléte
  a v066-os motorolvasó figyelmet kapja.

## 7. Emulátor-megfigyelés (a gazda tesztje, v065 után): NE csinálj kézi RAMTOP-váltást a mostani szalagokkal!

A gazda emulátorban a v065 betöltése OK volt, majd a kézi RAMTOP-váltás
(`POKE 16422,0 : POKE 16423,124` + `NEW`, RAMTOP=0x7F00) után gombnyomásra
a legfelső sor vízszintesen elcsúszik, és a gép vékony vízszintes pixel
alakzatokat rajzol. Ok (a lánc-tervezésből következik):

- A SHORT szalagblokkok (RTBASE16, témák) **nem tartalmazzák** a display
  file-t — az a várakozás, hogy a D_FILE-terület (0x7B00-) tartalma az
  előző blokkból ottmaradt és érvényes marad; a betöltés csak a
  rendszerváltozókat frissíti.
- A `NEW` a képernyőt **áthelyezi** az új RAMTOP alá, és a régi D_FILE-terület
  tartalmát otthagyja/érvénytelenné teszi. Ha ezután egy blokk betöltődik,
  annak rendszerváltozói a régi D_FILE-címre mutatnak, ahol már **nincs
  érvényes sorszerkezet** (nincsenek 0x76-sorvégek) — a ROM a "képernyőnek"
  hitt memóriarészt hulladékkódként rendereli: ez a vízszintes csík- és
  sorcsúszás-jelenség.
- Következtetés: a v066-os motoroldali áttérésnél a `LD SP` mellett **együtt
  kell szállítani** az új D_FILE-geometriát és a CHAIN újragondolását is
  (minden blokk vagy tartalmazza a display file-t, vagy a védett zóna-betöltés
  egy lépésben újrarendezi a képernyőt). A kézi POKE+NEW recept addig tilos.

## 8. Ellenőrzés állapota (v065-lezárás)

- `t81verify.py` a v065-ön: OK — 16 blokk, pontos EOF, RTLOAD01 első.
- RTLOAD01 bájt-szintű kézi ellenőrzés: 9 sor (REM + 6×PRINT + `INPUT C` +
  `LOAD "RTBASE16"`), csak biztonságos karakterkódok, **nincs számliterál**
  (nincs FP-rekord), minden sor 0x76-tal zárul; az építő assertjei érvényesülnek
  (`tools/rtlbuild.py`, RAMTOP-guard 0x7FFD megőrizve).
- Javítás (valós emulátor-megfigyelés nyomán): az eredeti PRINT-szövegek
  33-36 karakteresek voltak; a ZX81 32 oszlopnál (szó-nélküli) tördel és
  scrolloz, ezért a shell-képernyő összeomlott. Minden szöveg most max. 30
  karakter, és az építő beépitett asserttel védi (PRINT-sorok <= 30).
- ROM-szimulátor (`romsim.py`) RUN-gépelési teszt: a kontroll-teszt a
  bizonyítottan működő `kazetta/pioco-0.6.p`-vel is UGYANAZT a
  környezeti csődöt adja (sysvars → 0xFFFF, verem-írások 0x3FFF alatt) —
  tehát a crash a romsim RUN-gépelési környezetének tulajdonsága, **nem** a
  v065 bájtjainak hibája. A teljes futás-emuláció valós emulátorban (EightyOne)
  marad a nyári elfogadási út.
