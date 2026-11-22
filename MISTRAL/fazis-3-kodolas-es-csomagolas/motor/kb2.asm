; KB2T: v2.6 beépített kész-válasz-lánc — cím: 0x7C00 (256 B zóna).
; A motor GEN_KB-je a KB_BASE (ALAPMAG) és a KBTAB után járja (KBWALK:
; [kulcsszó][0][tény][0]... lánc; a kulcsszó a BLINE elejére prefix-egyezés alapján illeszkedik).
; A kulcsszavak NAGYBETŰSEK (a BLINE is az; a KEYTBL nagybetűs marad).
; A "WHAT ARE" tétel a zona-hiány miatt kikerult — a "WHO ARE" fedi az
; azonosito-kerdeseket. A ':' karakter a v2.6-os mini-
; billentyuzeten meg nem gepelheto be, ezert a :) es a :(
; bejegyzesek a kesobbi billentyu-bovitesre keszultek.
;
;   KB2T      EQU 0x7C00   (kb2.bin; a t81_build.py "KB2T" zona tolti)
;
; A zona az 0x7B00-0x7BFF CSOMAG-foglalas es a TARTALEK (0x7D00) kozott
; esik: a csomagok (max. 924 B at 0x7800) nem ernek fel ide.

        ORG 0x7C00
KB2T:
        db "WHO MADE",0,"Sandor Safar, with GLM's help.",0
        db "WHO ARE",0,"I am PIOCO, a tiny AI.",0
        db "CAN YOU",0,"English only, for now.",0
        db "HAHA",0,"Haha! Glad.",0
        db "WOW",0,"Wow! Thanks.",0
        db "NOO",0,"Do not be sad.",0
        db "HAPPY",0,"I am glad!",0
        db "SAD",0,"Do not be sad.",0
        db "SAFAR",0,"A bus driver, writer and astronomer.",0
        db 0
