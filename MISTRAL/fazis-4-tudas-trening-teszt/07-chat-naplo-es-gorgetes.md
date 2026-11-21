# CHAT-napló, inverz fejlécek és görgetés (SHIFT+5/6) — 4. fázis, negyedik lépés

Állapot: elkészült és automatikusan ellenőrizve. A `PIOCO.T81` most
**5907 bájt, 6 blokk**; a motor **3557 B** a 4096-os keretből (544 B
tartalék), a kilencféle vizsgálat zöld.

## 1. Kimért számok

| Elem | előző lépés | most | Határ |
| --- | --- | --- | --- |
| Motor | 2729 B | **3557 B** | 4096 B |
| CHAT-napló zóna | — | **0x6000–0x66FF = 1792 B** | 0x6700-ig (EMLÉKEZET) |
| EMLÉKEZET | 254 B | 254 B | 256 B |
| PIOCO.T81 | 5079 B / 6 blokk | **5907 B / 6 blokk** | — |

## 2. Új nyomtatómag (sor-/oszlopkurzor)

A régi, nyers mutatószámítás helyett a kurzor most két bájt
(`DFROW`, `DFCOL`) a PB-ben, és minden írásnál a
`DFILE + 33×sor + oszlop` tiszta címét számolja (`CALCUR`). Ez három
rendes javítást ad:

- **hosszú sorok:** a 32. oszlop után automatikus sortörés — a
  felhasználó 62 karakteres beírása már **nem írja felül a 0x76-os
  sorterminátorokat** (ez a régi kódban rejtett sérülés volt);
- **görgetés:** a 23. (alsó) sornál a kép tartalma eggyel felfelé
  csúszik (`SCRUP`), az utolsó sor üresen indul — a beszélgetés
  bármilyen hosszú lehet;
- **0x76-tiltás:** sortörés közben sem keletkezik se 0x76, se 0xC0+
  kód (a `PUTA` szűri), a sorterminátorok minden körülmények között a
  helyükön maradnak;



## 3. CHAT-napló formátuma

```
[0x6000] mágnes 0xA5
[0x6001] rekordok: [fejléc][0][szöveg][0]
fejléc:  YOU m:ss [tt]        (felhasználó)
         PIOCO m:ss [tt] sS   (modell)
```

- `m:ss` = a gép órája (FRAMES/50) az üzenet pillanatában,
- `tt` = a sorhoz felhasznált tokenek száma (a TOKENIZE után
  mérve, a modellnél a generált szavak számlálójával),
- `sS` = a generálás eltelt másodperce (ELAPSEC: FRAMES-pillanatkép
  különbsége, 99 mp-nél nem ugrik át).

A régi fejlécek **inverzen** jelennek meg (ZX81 bit7, csak a
0x00–0x3F tartomány invertálva — 0x76-tiltva). A napló elölről
újraindul, ha a zóna betelik (~14–20 üzenet), így mindig a legfrissebb
beszélgetés marad meg.

## 4. Görgetés: SHIFT+5 / SHIFT+6

- SHIFT+5 (vagy SHIFT+6): belépés a böngészőbe, az **utolsó üzenet**,
  fejléces képernyővel;
- SHIFT+5: egy korábbi üzenet, SHIFT+6: egy újabb (a legújabb határon
  megáll);
- bármely más billentyű: kilépés, a képernyő kiürül, a főciklus folytatódik.

## 5. Ellenőrzés

- teljes futószalag újrafuttatva: **MINDEN ELLENŐRZÉS RENDBEN**
- Z80-logika Python-szimulációban is bejárva: 32 oszlopos sortörés és
  görgetés pontossága (terminátorok a helyükön maradnak), fejlécforma
  (`YOU 1:15 [12]`, `PIOCO 21:05 [45] s07`), napló-túlfolyás-átírás
  (60 feltöltés után is 0x6700 alatt marad), böngészőkorlátok;
- a szimuláció egy **valódi hibát is lelutakolt**: a CHAT-mágnes
  (0xA5) nem íródott be soha — javítva, a napló így tényleg felépül.
- garble-szkan: 0 találat

## 6. Batnyvegzodes megjegyzesek

- a fejléc a felhasználó üzeneténél a gépelt sor **alatt** jelenik meg
  (a gépelés visszaverődése előbb megtörténik); a böngészőben viszont
  már felül van — a kettő együtt olvasható;
- a görgetés után a képernyő kiürül, a főciklus a 0. sortól folytatja.
