"""PIOCO.PZX (Perfect ZX Tape) kiszállító-gyártó, PZX v1.0 spec szerint.

Miért PZX? A EightyOne (és a legtöbb emulátor) a PZX-t natívan, PULS-SZINTEN
kezeli: nem hangot játszik le, hanem a pontos impulzus-sorozatot nyújtja
a ROM-nak. Így a WAV-lejátszás elindításával kapcsolatos bizonytalanságok
(kiindult-e a lejátszás, jó-e a hangkártya-időzítés) kiesnek.

PZX v1.0 formátum (spec: zxds.raxoft.cz/docs/pzx.txt):
  blokk = [4 bajt TAG][4 bajt LE hossz][adat]
  PZXT: major, minor bajt, majd NUL-lezárt szövegek (cím, majd kulcs/érték)
  PULS: pulzus-sorozat; minden bejegyzés (számláló, időtartam) pár; a szint
        impulzusonként váltakozik; időtartam T-egységekben (1 T = 1/3 500 000 s)
  DATA: bit-stream; count(4B, bit31 = kezdő szint magas), tail(2B),
        p0/p1 (1-1B, az S0/S1 időtartam-listák hossza), majd duration-ok
        (2-2 bajt), végén az adatbájtok; a biteket MSB elszámolja, bitenként
        a saját pulzus-sorozata (S0 = '0', S1 = '1') jön, a szint
        az ütem alternálásával folytatódik biten át
  PAUS: 4B (bit31 = szint, többi = időtartam T) — egyetlen szabad pulzus
  STOP: flags(2B) — szalagmotor megállása

A PIOCO szalag-protokoll megfeleltetése (t81_wav.py v2.6e időzítés):
  impulzus = 150 us magas + 150 us mély  ->  525 T + 525 T
  bit '0' = 4 impulzus, bit '1' = 9 impulzus
  bit UTÁN 1300 us mély csend — ez a bit utolsó mély fél-impulzusával
  összevonva (525 + 4550 = 5075 T), így minden bit-sorozat páros hosszú,
  és a szint bitenként magától, korrekten váltakozik
  lead-in / lead-out = 2 s csend egyenként (PULS, ill. PAUS blokk)

Használat:
    python3 t81_pzx.py <PIOCO.T81> <ki.PZX>       # gyártás + roundtrip
    python3 t81_pzx.py --ellenoriz <PIOCO.T81> <PIOCO.PZX>
"""

import struct
import sys

T_UNIT_S = 1 / 3_500_000       # 1 T = 1/3.5 MHz s (PZX időtartam-egység)
HALF_T = 525                   # 150 us T-egységekben
GAP_T = 4550                   # 1300 us T-egységekben
LAST_LOW_T = HALF_T + GAP_T    # az utolsó mély fél + bit-gap egyben
LEAD_T = 7_000_000             # 2 s (lead-in / lead-out)

S0 = [HALF_T] * 7 + [LAST_LOW_T]
S1 = [HALF_T] * 17 + [LAST_LOW_T]


def kontener_stream(path):
    with open(path, "rb") as f:
        kaz = f.read()
    assert kaz[:4] == b"EO81", "nem EO81 konténer"
    hossz = int(kaz[36:52].decode("ascii"))
    stream = kaz[52:52 + hossz]
    assert len(stream) == hossz, "blokk levágva"
    return stream


# ---- PULS-bejegyzés kódolás (számláló + 15 bites kiterjesztés, a spec ----
# ---- decode-pseudokódjának inverze) ----

def _puls_bejegyzes_bajtok(count, duration):
    assert 1 <= count <= 0x7FFF, "count tartomány"
    assert 0 <= duration <= 0x7FFFFFFF, "időtartam tartomány"
    out = bytearray()
    # A spec szerint a count-prefix KÖTELEZŐ, ha a kiterjesztett időforma
    # felső bitjei nem nullák (különben a felső biteket a dekódoló
    # ismétlésszámnak olvasná).
    needs_ext = duration >= 0x8000
    high_nonzero = duration >> 16 != 0
    if count != 1 or (needs_ext and high_nonzero):
        out += struct.pack("<H", 0x8000 | count)
    if duration < 0x8000:
        out += struct.pack("<H", duration)
    else:
        out += struct.pack("<H", 0x8000 | (duration >> 16))
        out += struct.pack("<H", duration & 0xFFFF)
    return bytes(out)


def _blokk(tag, adat):
    return tag.encode("ascii") + struct.pack("<I", len(adat)) + adat


def pzx_general(stream, cim="PIOCO AI miniature language modell"):
    """PZX v1.0 fájl-gyártás a szalag-streamből (EO81-ből kiszedett kép)."""
    assert len(S0) <= 255 and len(S1) <= 255, "az S0/S1 lista max 255 elem"
    pzxt = bytes([1, 0]) + cim.encode("ascii") + b"\x00"
    pzxt += b"Creator\x00PIOCO build tools v2.6f (t81_pzx.py)\x00"
    pzxt += b"Machine\x00ZX81\x00"
    ki = _blokk("PZXT", pzxt)
    # lead-in: 2 s mély csend (egy pulzus; a PULS-blokk alap szintje mély)
    ki += _blokk("PULS", _puls_bejegyzes_bajtok(1, LEAD_T))
    # DATA: minden bit S0 (0) vagy S1 (1) sorozata; kezdő szint = magas
    fejl = struct.pack("<I", (len(stream) * 8) | 0x80000000)
    fejl += struct.pack("<H", 0)             # tail (a stream végén csend van)
    fejl += bytes([len(S0), len(S1)])
    for d in S0 + S1:
        assert d < 0x8000, f"időtartam nem fér 15 bitbe: {d}"
        fejl += struct.pack("<H", d)
    ki += _blokk("DATA", fejl + stream)
    # lead-out: 2 s mély csend (PAUS), majd STOP (emulátor-szalagállj)
    ki += _blokk("PAUS", struct.pack("<I", LEAD_T))
    ki += _blokk("STOP", struct.pack("<H", 0))
    return ki


# ---- szigorú PZX-olvasó (roundtrip-igazolás) ----

def _blokkok(be):
    pos, ki = 0, []
    while pos < len(be):
        assert pos + 8 <= len(be), f"befejezetlen blokk-fej ennél: {pos}"
        tag = be[pos:pos + 4].decode("ascii")
        (hossz,) = struct.unpack_from("<I", be, pos + 4)
        assert pos + 8 + hossz <= len(be), f"{tag} blokk rovidebb a deklaráltnál"
        ki.append((tag, be[pos + 8:pos + 8 + hossz]))
        pos += 8 + hossz
    return ki


def _puls_bejegyzes_olvas(adat):
    """PULS-adat visszaolvasása (count, duration) párok listájába
    (a spec decode-pseudokódja szerint)."""
    pos, ki = 0, []
    while pos < len(adat):
        count = 1
        d = struct.unpack_from("<H", adat, pos)[0]
        pos += 2
        if d > 0x8000:
            count = d & 0x7FFF
            d = struct.unpack_from("<H", adat, pos)[0]
            pos += 2
        dur = d
        if d >= 0x8000:
            alacsony = struct.unpack_from("<H", adat, pos)[0]
            pos += 2
            dur = ((d & 0x7FFF) << 16) | alacsony
        ki.append((count, dur))
    return ki


def pzx_bitfolyam(path):
    """Szigorú visszaolvasás: a szalag-bájt-stream a PZX-fájlból.

    Ellenőrzi a szerkezetet is: PZXT + PULS(lead-in 2 s) + DATA(S0/S1 =
    szabványos 525/525+4550 T kódolás, 4/9 impulzus, tail = 0) +
    PAUS(lead-out 2 s) + STOP."""
    fajl = _blokkok(open(path, "rb").read())
    assert fajl[0][0] == "PZXT", "első blokk nem PZXT"
    assert fajl[1][0] == "PULS", "második blokk nem PULS (lead-in)"
    lead = _puls_bejegyzes_olvas(fajl[1][1])
    assert lead == [(1, LEAD_T)], f"lead-in eltér: {lead}"
    tag, adat = fajl[2]
    assert tag == "DATA", f"harmadik blokk nem DATA, hanem {tag}"
    (count_mezo,) = struct.unpack_from("<I", adat)
    assert bool(count_mezo & 0x80000000), "a DATA kezdő szintje nem magas"
    bit_count = count_mezo & 0x7FFFFFFF
    (tail,) = struct.unpack_from("<H", adat, 4)
    assert tail == 0, f"tail nem 0: {tail}"
    p0, p1 = adat[6], adat[7]
    assert p0 == len(S0) and p1 == len(S1), f"S0/S1 hossz: {p0}/{p1}"
    s0 = [struct.unpack_from("<H", adat, 8 + 2 * i)[0] for i in range(p0)]
    s1 = [struct.unpack_from("<H", adat, 8 + 2 * p0 + 2 * i)[0] for i in range(p1)]
    assert s0 == S0 and s1 == S1, "S0/S1 sorozat eltér a szabványostól"
    datum_hossz = (bit_count + 7) // 8
    stream = adat[8 + 2 * p0 + 2 * p1:]
    assert len(stream) == datum_hossz, \
        f"adat méret: {len(stream)} != {datum_hossz} (bitcount {bit_count})"
    tagok = [b[0] for b in fajl[3:]]
    assert tagok == ["PAUS", "STOP"], f"végblokkok: {tagok}"
    return stream


def pzx_atmenetek(path):
    """A PZX-fájl teljes szalagjele: [(zx81-tick, szint)] váltás-lista,
    a szimulátornak set_tape()-be (1 T = 1/3.5 MHz s; a ZX81 óra 3.25 MHz)."""
    fajl = _blokkok(open(path, "rb").read())
    atmenetek = []
    szint = 0
    t_T = 0.0
    for tag, adat in fajl[1:]:
        if tag == "PULS":
            for count, dur in _puls_bejegyzes_olvas(adat):
                for _ in range(count):
                    t_T += dur
                    szint = 1 - szint
                    atmenetek.append((round(t_T * 3.25 / 3.5), szint))
        elif tag == "DATA":
            (count_mezo,) = struct.unpack_from("<I", adat)
            szint = 1 if count_mezo & 0x80000000 else 0
            bit_count = count_mezo & 0x7FFFFFFF
            (tail,) = struct.unpack_from("<H", adat, 4)
            p0, p1 = adat[6], adat[7]
            s0 = [struct.unpack_from("<H", adat, 8 + 2 * i)[0] for i in range(p0)]
            s1 = [struct.unpack_from("<H", adat, 8 + 2 * p0 + 2 * i)[0]
                  for i in range(p1)]
            adatbajtok = adat[8 + 2 * p0 + 2 * p1:8 + 2 * p0 + 2 * p1
                              + (bit_count + 7) // 8]
            assert tail == 0, "tail-es DATA-t az atmenet-generator nem kezel"
            for i in range(bit_count):
                bajt = adatbajtok[i // 8]
                sorozat = s1 if (bajt >> (7 - i % 8)) & 1 else s0
                for d in sorozat:
                    t_T += d
                    szint = 1 - szint
                    atmenetek.append((round(t_T * 3.25 / 3.5), szint))
        elif tag == "PAUS":
            (v,) = struct.unpack_from("<I", adat)
            szint_uj = (v >> 31) & 1
            t_T += v & 0x7FFFFFFF
            if szint_uj != szint:
                szint = szint_uj
                atmenetek.append((round(t_T * 3.25 / 3.5), szint))
        else:
            break   # STOP vagy ismeretlen záróblokk: a jel véget ért
    return atmenetek


def pzx_olvas(path):
    """PZX-fájlból vissza a szalag-bájtok (tiszta kényelmi burkoló)."""
    return pzx_bitfolyam(path)


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--ellenoriz":
        stream = kontener_stream(sys.argv[2])
        vissza = pzx_olvas(sys.argv[3])
        assert vissza == stream, f"roundtrip HIBA: {len(vissza)} / {len(stream)} bajt"
        print(f"Roundtrip OK: {len(vissza)} bajt bájtpontosan visszakerült")
        return 0
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    be, ki = sys.argv[1], sys.argv[2]
    stream = kontener_stream(be)
    fajl = pzx_general(stream)
    with open(ki, "wb") as f:
        f.write(fajl)
    vissza = pzx_olvas(ki)
    assert vissza == stream, "a most gyártott PZX nem szigorú roundtrip"
    print(f"PZX: {ki}: {len(fajl)} bajt, {len(stream)*8} bit, "
          f"{(len(stream)*8)/len(stream):.0f} bit/bájt; dekódoló-igazolás OK")


if __name__ == "__main__":
    sys.exit(main())
