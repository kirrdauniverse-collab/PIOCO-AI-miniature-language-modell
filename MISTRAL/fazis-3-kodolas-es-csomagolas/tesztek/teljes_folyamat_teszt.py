"""Teljes valós-folyamat teszt: LOAD "" -> RUN, a PZX-szalaggal.

Ez a teszt a FELHASZNÁLÓ folyamatát szimulálja végponttól végpontig,
a valódi 8K ROM-mal:

  1. boot (reset + RAM-CHECK + INITIAL) 30M tick
  2. a RAM-alapzónák szemétlése 0xEE-vel + 0xA5 sentinel a PROFIL
     zónában — a hamis-pozitív elleni védelem
  3. a kazetta/PIOCO.PZX fájból kiolvasott impulzus-sorozat az
     EAR-vonalra (nem stream_to_ear: a KISZÁLLÍTOTT FÁJLBÓL dolgozik!)
  4. ROM LOAD "" (hijack: PC=0x0347, D=0x80) — a kép utolsó két
     bájtja (0x7DFE/0x7DFF) jelzi a végét; utána bájtpontos
     kép-ellenőrzés
  5. rendszerváltozók + launcher-sor bájtpontos egyezése a 0x406D-n
  6. RUN-egyenérték: a parancssor alól (SP megtartásával) kézi PUSH
     0x09C5 (a ROM parancssori főciklusa), PC = 0x4700 (MOTORBASE);
     várás a splash szövegre a D_FILE-ban — ez a RUN gomb
     gépi szintű egyenértéke
  7. PC-zóna monitoring: a motor nem skálózhat ki a ROM-alapzónába
     (0x0000-0x3FFF tilos), a D_FILE maradjon jogszerű (0xC0+ nincs)

Futtatás:
    python3 teljes_folyamat_teszt.py [/ut/vonal/zx81.rom]

A ROM bináris szerzői jogvédett, NEM kerül a repóba (/tmp/zx81.rom).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "eszkozok"))

from zx81sim import ZX81Sim, set_tape   # noqa: E402
import t81_build                        # noqa: E402
import t81_pzx                          # noqa: E402

MOTORBASE = 0x4700
SZALAG_ELINE = 0x7E00
PARANCSOR_RETURN = 0x09C5       # a ROM parancssori főciklusa
SPLASH_ASCII = b"P I O C O  A I"
LOAD_TICK_HATAR = 3_000_000_000
MOTOR_TICK_HATAR = 60_000_000
FAZIS_GYOKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def rom_helye():
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        return sys.argv[1]
    for hely in ("/tmp/zx81.rom", "../../zx81.rom", "zx81.rom"):
        if os.path.exists(hely):
            return hely
    return None


def Kazetta_utvonal():
    return os.path.join(FAZIS_GYOKER, "kazetta")


def varj_loadhatara(sim):
    sim.boot(ticks=30_000_000)
    assert sim.word(0x4014) == 0x42C1, "boot E_LINE hibas"


def pzx_load(sim, kep):
    """A PZX-fájlból vezetett szalaggal a ROM LOAD ""-ja, bájtpontosig."""
    mem = sim.m.memory
    pzx = os.path.join(Kazetta_utvonal(), "PIOCO.PZX")
    assert os.path.exists(pzx), f"nincs PZX: {pzx}"
    atmenetek = t81_pzx.pzx_atmenetek(pzx)
    set_tape(sim, atmenetek)
    mem[0x4040:SZALAG_ELINE] = b"\xEE" * (SZALAG_ELINE - 0x4040)
    mem[0x7E00:0x8000] = b"\xA5" * 0x200
    sim.m.d = 0x80
    sim.m.e = 0x00
    sim.m.pc = 0x0347
    kezd = sim.ticks
    utolso_ketto = kep[-2:]
    while sim.ticks - kezd < LOAD_TICK_HATAR:
        sim.m.ticks_to_stop = 200
        sim.m.run()
        sim._advance()
        sim.ear_level = sim.ear_at(sim.ticks)
        if mem[0x7DFE] == utolso_ketto[0] and mem[0x7DFF] == utolso_ketto[1]:
            break
    assert mem[0x7DFE] == utolso_ketto[0] and mem[0x7DFF] == utolso_ketto[1], \
        "a LOAD nem ért véget a kijelölt időkeretben"
    assert bytes(mem[0x4009:SZALAG_ELINE]) == kep, \
        "a betöltött kép nem egyezik bájtpontosan"
    assert bytes(mem[0x406D:0x406D + len(t81_build.launcher_sor())]) \
        == t81_build.launcher_sor(), "a launcher-sor nem a helyén van"
    return sim.ticks - kezd


def usr_hivas(sim):
    """RUN-egyenérték: a parancssor alól USR 18176.

    A BASIC RUN a 10-es sort hajtaná végre, amiben RAND USR 18176 áll;
    a gépi szinten az USR-hívás visszatérési címe a ROM parancssori
    főciklusa (0x09C5), a PC a motorba ér, a SP a parancssor szintjén
    marad."""
    mem = sim.m.memory
    sp = sim.m.sp
    assert 0x7FE0 <= sp <= 0x8000, f"parancssori SP rendben: {hex(sp)}"
    mem[sp - 2] = PARANCSOR_RETURN & 0xFF
    mem[sp - 1] = PARANCSOR_RETURN >> 8
    sim.m.sp = sp - 2
    sim.m.pc = MOTORBASE


def futtatas_pc_zonak(sim, hatar):
    """Futtat hatar tickig (200-as chunkenként); várja a splash-t a
    D_FILE-ban, közben PC-zóna-monitoroz. Vissza: (megvolt, zonak, vége)."""
    mem = sim.m.memory
    dfile = sim.word(0x400C)
    vars_cim = sim.word(0x4010)
    motor = open(os.path.join(Kazetta_utvonal(), "motor.bin"), "rb").read()
    idx = motor.find(bytes.fromhex("000b140d15131612"))
    assert idx >= 0, "ASCTAB nem talalhato a motor.bin-ben"
    tab = motor[idx:idx + 64]
    splash = bytes(tab[ord(c) - 32] for c in SPLASH_ASCII.decode("ascii"))
    kezd = sim.ticks
    megvolt = False
    zonak = {}
    while sim.ticks - kezd < hatar:
        sim.m.ticks_to_stop = 200
        sim.m.run()
        sim._advance()
        sim.ear_level = sim.ear_at(sim.ticks)
        zona = hex(sim.m.pc >> 12)
        zonak[zona] = zonak.get(zona, 0) + 1
        if not megvolt and bytes(mem[dfile:dfile + len(splash)]) == splash:
            megvolt = True
        if megvolt:
            # ENTER-nyomogatás, hogy a motor haladjon a splash után
            if (sim.ticks // 400) % 2:
                sim.pressed.add((0xBF, 0x01))
            else:
                sim.pressed.discard((0xBF, 0x01))
    rosszak = [b for b in mem[dfile:vars_cim] if 0xC0 <= b <= 0xFF]
    assert not rosszak, f"D_FILE-ban tiltott bájt a RUN után: {rosszak[:5]}"
    return megvolt, zonak, {"pc": hex(sim.m.pc), "sp": hex(sim.m.sp)}


def main():
    hely = rom_helye()
    if hely is None:
        print("SKIP: nincs ZX81 ROM (/tmp/zx81.rom) — a teljes folyamat nem tesztelt")
        return 0

    kaz_p = os.path.join(Kazetta_utvonal(), "PIOCO.T81")
    with open(kaz_p, "rb") as f:
        kaz = f.read()
    assert kaz[:4] == b"EO81", "EO81 magic hibas"
    hossz = int(kaz[36:52].decode("ascii"))
    szalag = kaz[52:52 + hossz]
    kep = szalag[5:]
    assert len(kep) == 0x7E00 - 0x4009, f"kép méret: {len(kep)}"
    pzx = os.path.join(Kazetta_utvonal(), "PIOCO.PZX")
    if not os.path.exists(pzx):
        with open(pzx, "wb") as f:
            f.write(t81_pzx.pzx_general(szalag))
    assert t81_pzx.pzx_olvas(pzx) == szalag, "PZX roundtrip nem bájtpontos"
    print(f"OK: konténer + PZX roundtrip ({len(szalag)} bajt szalag)")

    sim = ZX81Sim(hely)
    varj_loadhatara(sim)
    idok = pzx_load(sim, kep)
    print(f"OK: LOAD rendben {idok/3.25e6:.0f} szalagmásodperc alatt; "
          f"PC={hex(sim.m.pc)} SP={hex(sim.m.sp)}")

    usr_hivas(sim)
    megvolt, zonak, vegallapot = futtatas_pc_zonak(sim, MOTOR_TICK_HATAR)
    print(f"PC-zónák: {zonak}")
    print(f"végső állapot: {vegallapot}")
    assert megvolt, "a splash nem jött ki a RUN után"
    assert all(int(z, 16) >= 4 for z in zonak), \
        "a motor kicsúszott a RAM-zónából (wild-jump gyanú)"
    print("eredmény: MEGJELENT a splash | splash: True "
          "— a RUN-lánc a gép szintjén érvényes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
