# Vezérlők a motorban + bigramm-generátor (4. fázis, második lépés)

Állapot: elkészült és automatikusan ellenőrizve. A `PIOCO.T81` most
**4144 bájt, 5 blokk**; a nyolcféle vizsgálat (méret, mágnesjel, XOR,
PROFIL-védelem, RAM-határ, 0x76-tiltás, szótárforma, bigramm-forma) zöld.

## 1. Kimért számok

| Elem | v1 (angol váltás után) | v2 (most) | Zónahatár |
| --- | --- | --- | --- |
| Motor (`motor.bin`) | 1118 B | **1819 B** | 4096 B |
| Szótár (`szotar.bin`) | 90 token / 661 B | **111 token / 740 B** | 2560 B |
| Bigrammtábla (`bg.bin`) | — | **550 B, 212 átmenet** | a szótárzóna tartalékában |
| SZOTAR-blokk (szótár + bigramm) | 661 B | **1290 B** | 2560 B |

A szótárzóna tehát félig tele: marad kb. 1270 B az utólagos bővítéshez.

## 2. Új billentyűzet-motor

Teljes, 8 soros ZX81-mátrix (port 0xFE, sorkiválasztás; a 0. bit = a sor
„bal oldali” gombja):

| Sor | 0. bit | ... | 4. bit |
| --- | --- | --- | --- |
| 0xFE | SHIFT | Z X C | V |
| 0xFD | A | S D F | G |
| 0xFB | Q | W E R | T |
| 0xF7 | 1 | 2 3 4 | 5 |
| 0xEF | 0 | 9 8 7 | 6 |
| 0xDF | P | O I U | Y |
| 0xBF | ENTER | L K J | H |
| 0x7F | SPACE | . M N | B |

- A 0. sor 0. bitje a SHIFT: GETKEY ezt a `SHIFTF` változóba teszi,
  önmagában nem ad karaktert.
- Minden leütés csak a felengedés után adódik vissza, így nincs
  karakter-ismétlés; az emulátorteszt dönt arról, kell-e ismétlés.
- **ENTER benne van a táblában**, a READLINE valóban le tudja zárni a sort.

## 3. SHIFT-vezérlők (bekötve a SHIFTCMD-be)

| Billentyű | Hatás |
| --- | --- |
| SHIFT+1..4 | hőmérséklet 1..4; kiírja: `[temp n]` |
| SHIFT+9 | érveléskijelzés ki/be; kiírja: `[reasoning on]` / `[reasoning off]` |
| SHIFT+S | mentés-stub; kiírja: `[save stub: later]` (az EMLEKEZET-blokk a következő lépés) |
| SHIFT+SPACE | megszakításjelző (`ABRT`), sor eldobása; generálás közben: `[abort]` |
| SHIFT+5 / SHIFT+6 | görgetés — még nincs bekötve (a kurzormatematika kész) |

## 4. Bigramm-generátor

A válasz nem sablonból jön: a motor token-ID-folyamból komponál szavakat
a tanított átmeneti súlyok mentén.

- **Indítás:** az ATTN token (a felhasználó első szótári szava); ha nincs,
  STARTTAB-szó (HELLO / THE / MY / YOU) véletlenszerűen.
- **Járás:** mindig a beépített fókusz-token csoportjából választ a motor,
  hőmérséklet szerint:
  - 1: legnagyobb súlyú elem,
  - 2: súlyozott rulett,
  - 3: rulett + 1/4-es újdonságlöket (egyenletes szavazásra átlendülés),
  - 4: egyenletes szavazás az összes szomszéd közt.
- **Szó a válaszba:** a token-ID szótári karakterei kerülnek a RESP-be
  + szóköz; a RESP 30 karakternél lezárul.
- **Tudáshívás:** WHAT / WHO / WHY intentre a motor előbb az ALAPMAG-láncot
  (0x6C00) járja, aztán a beépített KBTAB-ot; ha sincs találat, bigrammal
  generál tovább (nem „nem tudom” a válasz).

## 5. Mintaválaszok (szimuláció, az emulátorteszt kiindulása)

A szimuláció pontosan a motor NXTENT-páras olvasását követi, így a
formátum és a logika a valós futás előtt is ellenőrzött:

```
hello friend i am pico the small thinking machine
computer is place where ideas live
memory is memory is mind
```

## 6. Hátravan a 4. fázisból

- EMLEKEZET (06-os) blokkírás a SHIFT+S alatt + 14 napos elavulás
- görgetés (SHIFT+5/6) bekötése
- ROM-INPUT kapcsolás
- turbószalag engedélyezési bit (FLAG-A bit3) a valós futtatáshoz
- emulátorszevetés a KEYTBL és az ASCTAB véglegesítésére
