; TADAT: fix adattabla-blokk — cim: 0x6B00 (v2.3)
; A motorzónán (0x4600-0x55FF) kívüli, kihasználatlan zóna: a PB-munkaterület
; (0x6800-0x69FF) és az ALAPMAG-zóna (0x6C00) között. A betöltő eszköz
; (t81_build.py) "TADAT" blokk-típusként tölti (07).
; A motor TAB13/DOWTAB/TXTDAYP/TXTTIS/WTAB/TIMTAB/IMAGTAB/IMAGSEED néven
; hivatkozik rá — az eltolásokat a pico.asm EQU-sorai rögzítik:
;   TAB13     TADAT+0x00   (15 B)
;   DOWTAB    TADAT+0x0F   (28 B)
;   TXTDAYP   TADAT+0x2B   ( 6 B)
;   TXTTIS    TADAT+0x31   ( 9 B)
;   WTAB      TADAT+0x3A   (12 B)
;   TIMTAB    TADAT+0x46   ( 6 B)
;   IMAGTAB   TADAT+0x4C   (21 B)
;   IMAGSEED  TADAT+0x61   (28 B)  -> blokk vége: 0x6B7C
;
; TAB13: honap-index m' = 1..14 (13/14 = jan/fev +12); a teljes 2000-2099
; tartományra brute-force ellenőrizve a Python calendar moduljával (0 hiba)
        ORG 0x6B00
TAB13:
        db 0                    ; 0. index: nem használt
        db 5,0,3,6,1,4,6,2,5,0,3,5,1,4

; DOWTAB: napnevek, 4 bájt bejegyzésenként (A = 0..6, 0 = vasárnap)
DOWTAB:
        db "SUN",0
        db "MON",0
        db "TUE",0
        db "WED",0
        db "THU",0
        db "FRI",0
        db "SAT",0

; naptar-/ora-valasz kezdetei
TXTDAYP:
        db "it's ",0
TXTTIS:
        db "time is ",0

; WTAB: "what day is it today?" felismero szavai
WTAB:
        db "TODAY",0
        db "DATE",0
        db 0

; TIMTAB: "what time is it?" felismero szavai
TIMTAB:
        db "TIME",0
        db 0

; IMAGTAB: kepzelet-modul aktivator szavai (IMAGF = 1)
IMAGTAB:
        db "IF",0
        db "WOULD",0
        db "COULD",0
        db "WISH",0
        db 0

; IMAGSEED: kepzelet-indito szavak (mind szotari szo)
IMAGSEED:
        db "DREAM",0
        db "HUMAN",0
        db "MAYBE",0
        db "SOMETHING",0
