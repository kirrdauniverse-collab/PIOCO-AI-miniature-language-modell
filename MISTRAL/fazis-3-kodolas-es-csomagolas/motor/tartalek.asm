; TARTALEK: kis szovegek a motorzona tehermentesitesere — cim: 0x7D00 (v2.5)
; Az 0x7D00-0x7DFF zona (512 bajt) korabban tartalek volt; most a SZOTAR-zona
; utan a masodik "tulcsszott" adatteruletkent tonk: mar 92 bajt.
; A t81_build.py "TARTALEK" blokk-tipuskent (08) tolti.
;
;   ASKH      EQU 0x7D00   (30 B)
;   ASKS      EQU 0x7D1E   (27 B)
;   TXTDUNNO  EQU 0x7D39   (27 B)
;   TXTABORT  EQU 0x7D54   ( 8 B)

        ORG 0x7D00
ASKH:
        db "i remember head pain. better?",0
ASKS:
        db "i remember unwell. better?",0
TXTDUNNO:
        db "Still learning about that.",0
TXTABORT:
        db "[abort]",0
