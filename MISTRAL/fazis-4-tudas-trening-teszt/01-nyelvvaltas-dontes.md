# Nyelvváltás: ANGOL prototípus (döntés rögzítése)

**Döntés (tulaj):** a prototípus angol nyelven fut; a magyar nyelvi
finomítás később, a kiforrott modell után jön.

## Miért jó ez a 16 KB-os keretben?

| Szempont | Magyar | Angol | Bevált tényleges mérésünk |
| --- | --- | --- | --- |
| Szótár-blob (91→90 szó) | 776 B | **661 B** | ~15% helymegtakarítás ugyanazzal a lefedettséggel |
| Toldalékolás | agglutináló: `-ban/-ben/-nak/-nek...` külön token-készlet | prediktív (of/in/at...) | angolban nincs toldalék-tábla → tiszta motor-hely |
| Kód-egységesség | ékezetes karakterek (UTF-8 bájtok a forrásban) | tiszta ASCII | a 0x76-tiltás egyszerűbb, kockázat kisebb |
| Vázak hossza | hosszabb mondatvázak | rövidebb vázak | több váz fér az 50–150 B-s tartalékon belül |

## Mit jelent ez a motorban?

- Az INTKWTAB kulcsszavak angolul (WHAT / WHO / WHY / REMEMBER / DRAW / SAVE).
- A KBTAB tények angolul.
- A szótár-blob az angol alapcorpuszból tréningelve.
- A SAFEPCHR maszk nem változik (0x76 és 0xC0+ tiltva) — angolnál
  automatikusan ritkábban riaszt.

## A magyar visszahozatalának terve (kiforrott modell után)

1. nagyobb SZÓTÁR (a 2. fázisbeli toldalék-tokenek: `-ban/-ben`, `-nak/-nek`,
   `-ra/-re`, `-val/-vel`, `-t`, `-ok/-ek/-ök`) — a 3. fázisbeli
   kb. 400–460 tokenes terv szerint;
2. a chat-rekord és a generálási lánc nyelvi szempontból: csak a tokenhalmaz és
   a vázak cserélődnek — **motor-átírás nélkül vált**;
3. emulátorvizsgálat az ékezet-konverziós táblával (4. fázisbeli
   ASCTAB-eszköz bővítésével).

Ez a döntés **nem veszíti el a magyar célt** — csak késlelteti a finom
állapotát, miközben a motor-architektúra (tokenizálás → reasoning →
generálás) nyelvfüggetlenül változatlan marad.
