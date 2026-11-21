# Kutatási alapanyagok

- **zx81.rom** — a valódi 8 KB-os ZX81 ROM-kép (forrás: mahjongg2/ZX81plus38
  GitHub-nyilvántartás; az FPGA-projekt a standard, gyári ROMot használja).
  Hitelesítés: első utasítás `OUT (0xFD),A` + `LD BC,0x7FFF`; a karakterkészlet
  végén a ©-minta; a RAM-CHECK/INIT/NMI-kód a Logan–O'Hara listával bájtszinten
  egyezik.
- **romlist.txt** — a teljes ZX81 ROM-disassembly szöveges formában (Ian Logan
  & Frank O'Hara: *The Complete ZX81 ROM Disassembly*; forrás: k1.spdns.de HTML,
  szöveggé konvertálva). A D-3.x döntések elsődleges forrása.

Eszközök, amik ezeket használják: `eszkozok/romsim.py` (ROM-szintű virtuális
gép: teljes Z80 mag + NMI/INT-kadencia + A14-es memóriatükör),  
`eszkozok/romprobe.py` (lépésenkénti nyomkövetés). Állapot: a ROM initje
tisztán fut (RAM-CHECK → INIT → CLS/LOC-ADDR/MAKE-ROOM protokoll igazolva);
a SLOW-képernyő megszakítás-koreográfiájának finomhangolása folyamatban.
