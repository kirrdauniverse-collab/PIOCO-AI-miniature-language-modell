"""Teljes kazetta vegponti teszt: PIOCO.T81 -> ROM LOAD "" -> motor boot.

Lepesek:
  1. EO81 kontener szetszedese (mik, meretek, adatblokkok ellenorzese)
  2. ROM LOAD "" (NEXT-PROG, PC=0x0347, D=0x80) a valodi ZX81 ROM-mal:
     a RAM 0xEE-vel szemetelve, a PROFIL-zonaba a 0xA5 sentinellel;
     a teljes kep bajtponossan kell visszajoennie
  3. rendszervaltzo-ellenorzes (D_FILE/VARS/E_LINE/STKBOT/STKEND/E_PPC)
  4. launcher-sor: bajtponos egyezes a builder launcher_sor()-aval
  5. profiltisztseg: a szalagon levo E_LINE miatt a LOAD a 0x7DFF-nel
     all meg, a 0x7E00..0x7FFF (PROFIL) sentinelle tolt marad
  6. motor-boot: PC=0x4700 (MOTORBASE), SP=0x7FFF; varas a splash
     szovegre a D_FILE-ban, ENTER-t kuld, a hello kepernyot ellenorzi;
     kozben a D_FILE egyetlen bajtja sem lehet 0xC0+ (parancskod/fagyas

Futtatas:
    python3 kazetta_teszt.py [/ut/vonal/zx81.rom]

A ROM binaris szerzoi jogvevedett, NEM kerul a repoba.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "eszkozok"))

from zx81sim import ZX81Sim, stream_to_ear, set_tape   # noqa: E402
import t81_build                                       # noqa: E402

MOTORBASE = 0x4700
SZALAG_ELINE = 0x7E00
KEP_HELYEK = {
    0x400A: 10,            # E_PPC
    0x400C: t81_build.D_FILE,
    0x4010: t81_build.VARS_CIM,
    0x4016: 0,             # X_PTR
    0x401A: t81_build.STKBOT_CIM,
    0x401C: t81_build.STKEND,
}
SPLASH_ASCII = b"P I O C O  A I"
PROFIL_NEZO = 0xA5


def rom_helye():
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        return sys.argv[1]
    for hely in ("/tmp/zx81.rom", "zx81.rom"):
        if os.path.exists(hely):
            return hely
    return None


def kontener_kiszed(path):
    with open(path, "rb") as f:
        kaz = f.read()
    assert kaz[:4] == b"EO81", "EO81 magic hibas"
    blokkok = []
    i = 4
    while i < len(kaz):
        nev = kaz[i:i + 32].rstrip(b"\x00")
        hossz = int(kaz[i + 32:i + 48].decode("ascii"))
        adat = kaz[i + 48:i + 48 + hossz]
        assert len(adat) == hossz, f"blokk {nev}: levagt meret"
        blokkok.append((nev, adat))
        i += 48 + hossz
    return blokkok


def varj_loadhatara(sim):
    """Bebootol 30M tickig, majd ellenorzi a telepedett allapotot."""
    sim.boot(ticks=30_000_000)
    w = sim.word
    assert w(0x4014) == 0x42C1, "boot E_LINE hibas"
    assert w(0x400C) == 0x407D, "boot D_FILE hibas"


PROFIL_VEDDES = 0x7FE8   # efölött a CPU-verem dolgozik (a hijack RETURN-ei)


def rom_load(sim, szalag, kep):
    mem = sim.m.memory
    atmenetek = stream_to_ear(szalag)
    set_tape(sim, atmenetek)
    mem[0x4040:SZALAG_ELINE] = b"\xEE" * (SZALAG_ELINE - 0x4040)
    mem[t81_build.PROFIL_ZONA[0]:0x8000] = bytes([PROFIL_NEZO]) * (0x8000 - t81_build.PROFIL_ZONA[0])
    sim.m.d = 0x80
    sim.m.e = 0x00
    sim.m.pc = 0x0347
    kezd = sim.ticks
    veg = False
    utolso_ketto = kep[-2:]
    while sim.ticks - kezd < 3_000_000_000:
        sim.m.ticks_to_stop = 200
        sim.m.run()
        sim._advance()
        sim.ear_level = sim.ear_at(sim.ticks)
        # a hijack utani pitykegés alatt a ROM LD H,D-nel HL-be irja
        # a D/E-regisztert (0x8000 kornyeki fiktiv cím), ezert HL-t nem
        # hasznaljuk; a vegezeset a kep utolso ket bajtjanak megérkezese
        # dönti el (0x7DFE, 0x7DFF)
        if mem[0x7DFE] == utolso_ketto[0] and mem[0x7DFF] == utolso_ketto[1]:
            veg = True
            break
    assert veg, "a LOAD nem ert veget a kijelolt idokeretben"
    kapott = bytes(mem[0x4009:SZALAG_ELINE])
    assert kapott == kep, "a betoltott kep nem egyezik bajtponosan"
    vam = t81_build.PROFIL_ZONA[0]
    assert mem[vam:PROFIL_VEDDES] == bytes([PROFIL_NEZO]) * (PROFIL_VEDDES - vam), \
        "a LOAD felulirta a PROFIL-zonat (a veremsav felett is)"


def asctab_zx(motor):
    idx = motor.find(bytes.fromhex("000b140d15131612"))
    assert idx >= 0, "ASCTAB nem talalhato a motor.bin-ben"
    tab = motor[idx:idx + 128]
    return tab   # ASCTAB[ord(c)-32] = a c karakter ZX81-kodja


def dfile_jogszeru(mem, dfile, vars_cim):
    resz = mem[dfile:vars_cim]
    rosszak = [b for b in resz if 0xC0 <= b <= 0xFF]
    assert not rosszak, f"D_FILE-ban tiltott bajt: {rosszak[:5]}"
    return resz


def motor_boot(sim, motor):
    mem = sim.m.memory
    dfile = sim.word(0x400C)
    vars_cim = sim.word(0x4010)
    tab = asctab_zx(motor)
    sim.m.sp = 0x7FFF
    sim.m.pc = MOTORBASE
    splash = bytes(tab[ord(c) - 32] for c in SPLASH_ASCII.decode("ascii"))
    kezd = sim.ticks
    megvolt = False
    kozepek = 0
    while sim.ticks - kezd < 40_000_000:
        sim.m.ticks_to_stop = 200
        sim.m.run()
        sim._advance()
        sim.ear_level = sim.ear_at(sim.ticks)
        if not megvolt and bytes(mem[dfile:dfile + len(splash)]) == splash:
            megvolt = True
            assert bytes(mem[dfile:dfile + len(splash)]) == splash, \
                "a splash bajtjai nem egyeznek"
            sim.pressed.add((0xBF, 0x01))      # ENTER fel
        if megvolt:
            kozepek += 1
            if kozepek % 2 == 0:
                sim.pressed.add((0xBF, 0x01))
            else:
                sim.pressed.discard((0xBF, 0x01))
    dfile_jogszeru(mem, dfile, vars_cim)
    assert megvolt, "a splash nem jott a kepernyore a kijelolt idokeretben"
    return sim.ticks - kezd


def main():
    hely = rom_helye()
    if hely is None:
        print("SKIP: nincs ZX81 ROM (l. kazetta_teszt.py fejlec)")
        return 0

    kaz_p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "kazetta", "PIOCO.T81")
    blokkok = kontener_kiszed(kaz_p)
    assert blokkok, "a kontenerben nincs blokk"
    nev, szalag = blokkok[0]
    assert nev == b"PIOCO", f"elso blokk neve: {nev}"
    assert szalag[:5] == b"PIOCO" and szalag[5] & 0x80, "stream fejlec/lezaro hibas"
    kep = szalag[6:]
    assert len(kep) == 0x7E00 - 0x4009, f"kep meret: {len(kep)} (15863 kell)"
    assert kep[0x4014 - 0x4009:0x4016 - 0x4009] == SZALAG_ELINE.to_bytes(2, "little"), \
        "a szalagon levo E_LINE nem 0x7E00"
    print(f"OK: kontener ({len(blokkok)} blokk), kep {len(kep)} B")

    sim = ZX81Sim(hely)
    varj_loadhatara(sim)
    rom_load(sim, szalag, kep)
    print("OK: bajtponos LOAD, a PROFIL szenitjeke meg serul Allapoton")

    mem = sim.m.memory
    def w(a):
        return mem[a] | (mem[a + 1] << 8)
    for cim, ertek in KEP_HELYEK.items():
        assert w(cim) == ertek, f"rendszervaltzo {hex(cim)}: {hex(w(cim))} != {hex(ertek)}"
    sor = t81_build.launcher_sor()
    assert bytes(mem[0x406D:0x406D + len(sor)]) == sor, "launcher-sor eltavozott"
    dfile_jogszeru(mem, w(0x400C), w(0x4010))
    print("OK: rendszervaltozok, launcher-sor, D_FILE jogsertetlen (0xC0+ nincs)")

    motor = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "kazetta", "motor.bin"), "rb").read()
    szer = motor_boot(sim, motor)
    print(f"OK: motor splash + hello kepernyon {szer/3.25e6:.1f} vaslagmp alatt, jogsertetlen kep")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
