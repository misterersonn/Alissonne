"""Personnages du plan 3 : le fermier qui hurle et l'émeu qui mâche.

Toutes les pièces sont dessinées en code. Chaque fonction reçoit une pose
(dictionnaire d'angles / d'ouvertures) : l'animation consiste à faire varier
ces valeurs dans le temps.
"""
import math

from toon import (INK, WHITE, capsule, ellipse_path, fist, glove, halftone, ink, rgb,
                  smooth_path)

SHIRT = rgb("E9D6B4")
SHIRT_SH = rgb("B58E62")
DENIM = rgb("5E82AE")
DENIM_SH = rgb("2E4E78")
MOUTH = rgb("6E1220")
TONGUE = rgb("E9667A")
VEIN = rgb("D62434")
GOLD = rgb("E0B24A")

FEATHER = rgb("7C6450")
FEATHER_SH = rgb("3E2F24")
NECK = rgb("B8C3D2")
LEG = rgb("8C919C")
BEAK = rgb("9EA3AC")


def deg(a):
    return math.radians(a)


# ======================================================================
# Le fermier
# ======================================================================
def farmer(c, x, y, p, s=1.0):
    """p : lean, head_rot, head_sy, mouth (0-1), arm_l, fore_l, arm_r, fore_r, spread, vein."""
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    c.rotate(deg(p["lean"]))

    # ---------------------------------------------------------- bras
    def arm(sx, sy, a_up, a_fore, side):
        c.save()
        c.translate(sx, sy)
        c.rotate(deg(a_up))
        capsule(c, 0, 0, 0, -175, 74, SHIRT, 8)
        c.translate(0, -175)
        # revers de manche au coude
        ellipse_path(c, 0, 0, 44, 22)
        ink(c, SHIRT, 7)
        c.rotate(deg(a_fore))
        capsule(c, 0, 0, 0, -140, 58, SHIRT, 8)
        halftone(c, lambda: (c.rectangle(-30, -140, 60, 140)), SHIRT_SH, direction=(side, 0.2), start=0.55, step=8, rmax=3)
        hand = p.get("hand_l" if side < 0 else "hand_r", "open")
        if hand == "open":
            glove(c, 0, -175, 0, 1.35, p["spread"], 7)
        else:
            fist(c, 0, -170, 0, 1.3, 7, point=(hand == "point"))
        c.restore()

    def arms():
        arm(-150, -270, p["arm_l"], p["fore_l"], -1)
        arm(150, -270, p["arm_r"], p["fore_r"], 1)

    if not p.get("arms_front"):
        arms()

    # ---------------------------------------------------------- torse
    shirt = [(-150, -305), (-60, -335), (60, -335), (150, -305), (182, -200), (160, 80), (-160, 80), (-182, -200)]

    def shirt_path():
        smooth_path(c, shirt, True, 0.35)
    shirt_path()
    ink(c, SHIRT, 9)
    halftone(c, shirt_path, SHIRT_SH, direction=(0.9, 0.4), start=0.45)
    # col
    for sgn in (-1, 1):
        smooth_path(c, [(0, -330), (sgn * 70, -335), (sgn * 45, -280)], True, 0.2)
        ink(c, SHIRT, 7)

    bib = [(-100, -175), (100, -175), (118, 80), (-118, 80)]

    def bib_path():
        smooth_path(c, bib, True, 0.08)
    # bretelles
    for sgn in (-1, 1):
        capsule(c, sgn * 88, -165, sgn * 125, -312, 30, DENIM, 7)
    bib_path()
    ink(c, DENIM, 9)
    halftone(c, bib_path, DENIM_SH, direction=(0.8, 0.5), start=0.4)
    c.rectangle(-55, -120, 110, 78)
    ink(c, DENIM, 6)
    c.move_to(-55, -98)
    c.line_to(55, -98)
    c.set_line_width(4)
    c.stroke()
    for sgn in (-1, 1):
        ellipse_path(c, sgn * 82, -160, 13, 13)
        ink(c, GOLD, 5)

    if p.get("arms_front"):
        arms()

    # ---------------------------------------------------------- tête
    c.save()
    c.translate(0, -375)
    c.rotate(deg(p["head_rot"]))
    c.scale(1 / math.sqrt(p["head_sy"]), p["head_sy"])
    c.translate(0, -190)

    def head_path():
        ellipse_path(c, 0, 0, 192, 186)
    head_path()
    ink(c, WHITE, 10)
    halftone(c, head_path, rgb("C9C3D6"), direction=(0.8, 0.9), start=0.62, step=9, rmax=3.2, alpha=0.6)

    # sourcils furieux
    for sgn in (-1, 1):
        c.move_to(sgn * 150, -92)
        c.curve_to(sgn * 120, -80, sgn * 80, -62, sgn * 40, -52)
        c.set_source_rgb(*INK)
        c.set_line_width(18)
        c.stroke()
    # plis du front
    c.set_source_rgb(*INK)
    for k in (-1, 1):
        c.move_to(k * 18, -40)
        c.line_to(k * 10, -10)
        c.set_line_width(5)
        c.stroke()
    # yeux plissés > <
    for sgn in (-1, 1):
        c.move_to(sgn * 125, -45)
        c.line_to(sgn * 62, -22)
        c.line_to(sgn * 122, -2)
        c.set_line_width(10)
        c.stroke()
        # rides de rage
        c.move_to(sgn * 150, -30)
        c.line_to(sgn * 170, -18)
        c.set_line_width(5)
        c.stroke()

    if p.get("face") == "tight":
        # joues gonflées et rouges, bouche pincée en zigzag
        for sgn in (-1, 1):
            ellipse_path(c, sgn * 118, 40, 46, 30)
            c.set_source_rgba(*VEIN, 0.45)
            c.fill()
        pts = [(-70, 70), (-45, 58), (-20, 74), (5, 58), (30, 74), (55, 58), (75, 70)]
        c.move_to(*pts[0])
        for q in pts[1:]:
            c.line_to(*q)
        c.set_source_rgb(*INK)
        c.set_line_width(10)
        c.stroke()
        o = None
    else:
        o = p["mouth"]
    if o is not None:
        _scream_mouth(c, o)
    v = p["vein"]
    if v >= 0.05:
        _vein(c, v)
    c.restore()  # tête
    c.restore()


def _scream_mouth(c, o):
    mw, mh = 50 + 60 * o, 14 + 166 * o
    mouth_pts = [(-mw * 0.8, 30), (-mw * 0.45, 4), (0, -2), (mw * 0.45, 4), (mw * 0.8, 30),
                 (mw, 18 + mh * 0.75), (mw * 0.55, 18 + mh), (-mw * 0.55, 18 + mh), (-mw, 18 + mh * 0.75)]

    def mouth_path():
        smooth_path(c, mouth_pts, True, 0.45)
    mouth_path()
    c.set_source_rgb(*MOUTH)
    c.fill()
    c.save()
    mouth_path()
    c.clip()
    ellipse_path(c, 0, 18 + mh * 0.92, mw * 0.62, mh * 0.34)
    c.set_source_rgb(*TONGUE)
    c.fill()
    c.rectangle(-mw, -10, mw * 2, 34)
    c.set_source_rgb(*WHITE)
    c.fill()
    c.move_to(-mw, 24)
    c.curve_to(-mw * 0.4, 18, mw * 0.4, 18, mw, 24)
    c.set_source_rgb(*INK)
    c.set_line_width(4)
    c.stroke()
    c.rectangle(-mw * 0.5, 18 + mh - 16, mw, 20)  # dents du bas
    c.set_source_rgb(*WHITE)
    c.fill()
    ellipse_path(c, 0, 18 + mh * 0.55, mw * 0.3, mh * 0.18)
    c.set_source_rgba(0, 0, 0, 0.45)
    c.fill()
    c.restore()
    mouth_path()
    c.set_source_rgb(*INK)
    c.set_line_width(10)
    c.stroke()


def _vein(c, v):
    """Veine de colère (croix de quatre arcs rouges)."""
    c.save()
    c.translate(118, -118)
    c.scale(v, v)
    for q in range(4):
        c.save()
        c.rotate(q * math.pi / 2 + math.pi / 4)
        c.move_to(-14, -26)
        c.curve_to(-4, -12, 4, -12, 14, -26)
        c.set_source_rgb(*VEIN)
        c.set_line_width(9)
        c.stroke()
        c.restore()
    c.restore()


# ======================================================================
# L'émeu
# ======================================================================
def _feather_blob(cx, cy, rx, ry, n=30, bump=0.07, tail=0.0):
    """Contour de plumage : touffes irrégulières, plus longues en bas et à la queue."""
    pts = []
    for i in range(n):
        a = i / n * 2 * math.pi
        rnd = (math.sin(i * 12.9898) * 43758.5453) % 1.0
        shag = 1 + 0.9 * max(0, math.sin(a)) ** 2  # frange qui pend en bas
        r = 1 + (bump * shag * (0.4 + 0.8 * rnd) if i % 2 else -bump * 0.15)
        tl = tail * max(0, -math.cos(a)) ** 3
        pts.append((cx + rx * (r + tl) * math.cos(a), cy + ry * r * math.sin(a) - tl * 40 * max(0, -math.sin(a))))
    return pts


def emu(c, x, y, p, s=1.0):
    """p : body_sy, neck (sway), head_rot, jaw (deg), look (-1..1), blink (0-1), stalk."""
    c.save()
    c.translate(x, y)
    c.scale(s, s)

    # ---------------------------------------------------------- pattes
    for (hx, kx, fx) in ((-40, -75, -55), (45, 70, 80)):
        c.move_to(hx, -250)
        c.line_to(kx, -120)
        c.line_to(fx, 0)
        c.set_source_rgb(*INK)
        c.set_line_width(40)
        c.stroke()
        c.move_to(hx, -250)
        c.line_to(kx, -120)
        c.line_to(fx, 0)
        c.set_source_rgb(*LEG)
        c.set_line_width(26)
        c.stroke()
        # écailles
        for k in range(4):
            u = 0.2 + k * 0.2
            ex, ey = kx + (fx - kx) * u, -120 + 120 * u
            c.move_to(ex - 10, ey)
            c.line_to(ex + 10, ey + 3)
            c.set_source_rgb(*INK)
            c.set_line_width(3)
            c.stroke()
        for ta in (-0.5, 0.0, 0.5):
            capsule(c, fx, 0, fx + 42 * math.sin(ta + 1.2), 6 + 8 * math.cos(ta), 9, LEG, 5)

    # ---------------------------------------------------------- corps
    c.save()
    c.translate(0, -250)
    c.scale(1, p["body_sy"])
    c.translate(0, 250)
    body = _feather_blob(0, -350, 215, 165, 30, 0.08, tail=0.3)

    def body_path():
        smooth_path(c, body, True, 0.8)
    body_path()
    ink(c, FEATHER, 10)
    halftone(c, body_path, FEATHER_SH, direction=(0.4, 1), start=0.4, step=10, rmax=4.4, alpha=0.6)
    # texture peinte : mèches de plumes claires et sombres
    c.save()
    body_path()
    c.clip()
    for k in range(90):
        rx_ = (math.sin(k * 91.7) * 4375.85) % 1.0
        ry_ = (math.sin(k * 37.3) * 9173.13) % 1.0
        fx, fy = -230 + 460 * rx_, -520 + 340 * ry_
        L = 26 + 22 * ((k * 7) % 5) / 5
        col = rgb("9C8268") if k % 3 == 0 else rgb("5E4938")
        c.move_to(fx, fy)
        c.curve_to(fx + L * 0.4, fy + L * 0.3, fx + L * 0.6, fy + L * 0.7, fx + L * 0.5, fy + L)
        c.set_source_rgba(*col, 0.85)
        c.set_line_width(5)
        c.stroke()
    c.restore()
    # traits de plumes
    c.set_source_rgb(*INK)
    c.set_line_width(4)
    for (fx, fy, L, a) in [(-120, -380, 60, 0.5), (-60, -300, 70, 0.4), (10, -380, 60, 0.3), (60, -290, 70, 0.5),
                           (-150, -300, 50, 0.7), (110, -350, 50, 0.3), (-20, -240, 60, 0.6),
                           (-180, -400, 50, 0.6), (140, -280, 45, 0.5), (-90, -440, 55, 0.3), (40, -450, 50, 0.4),
                           (-100, -230, 50, 0.8), (150, -410, 40, 0.4)]:
        c.move_to(fx, fy)
        c.curve_to(fx + L * 0.3, fy + L * 0.2, fx + L * 0.7, fy + L * 0.3, fx + L * math.cos(a), fy + L * math.sin(a))
        c.stroke()
    c.restore()

    # ---------------------------------------------------------- cou
    sway = p["neck"]
    base = (120, -430)
    top = (175 + sway, -655)
    ctrl = (205 + sway * 0.3, -520)
    for col, w in ((INK, 84), (NECK, 66)):
        c.move_to(*base)
        c.curve_to(ctrl[0], ctrl[1], ctrl[0], ctrl[1] - 60, *top)
        c.set_source_rgb(*col)
        c.set_line_width(w)
        c.stroke()
    # plumes à la base du cou
    smooth_path(c, _feather_blob(128, -445, 62, 40, 18, 0.2), True, 0.8)
    ink(c, FEATHER, 6)

    # ---------------------------------------------------------- tête
    c.save()
    c.translate(*top)
    c.rotate(deg(p["head_rot"]))

    def head_path():
        ellipse_path(c, 18, -38, 66, 62, 0.15)
    # bec du bas (mâchoire qui bouge)
    c.save()
    c.translate(70, -22)
    c.rotate(deg(p["jaw"]))
    smooth_path(c, [(0, -6), (78, 6), (74, 16), (0, 14)], True, 0.2)
    ink(c, rgb("7F848E"), 7)
    # brin de blé dans le bec
    st = p["stalk"]
    c.move_to(40, 6)
    c.curve_to(80, 30, 110, 60 + st * 10, 140, 90 + st * 20)
    c.set_source_rgb(*INK)
    c.set_line_width(9)
    c.stroke_preserve()
    c.set_source_rgb(*rgb("E3B654"))
    c.set_line_width(4)
    c.stroke()
    for k in range(5):
        gx, gy = 100 + k * 9, 48 + k * 10 + st * (4 + k * 3)
        ellipse_path(c, gx, gy, 12, 6, 0.8)
        ink(c, rgb("E3B654"), 4)
    c.restore()
    # bec du haut
    smooth_path(c, [(58, -38), (150, -14), (152, -6), (66, -4)], True, 0.25)
    ink(c, BEAK, 7)
    c.move_to(118, -22)
    c.line_to(126, -20)
    c.set_line_width(4)
    c.stroke()
    head_path()
    ink(c, WHITE, 9)
    halftone(c, head_path, rgb("C9C3D6"), direction=(-0.5, 1), start=0.6, step=8, rmax=2.8)
    # yeux ronds
    look = p["look"]
    for ex, ey, r in ((20, -62, 24), (62, -58, 21)):
        ellipse_path(c, ex, ey, r, r * 1.05)
        ink(c, WHITE, 6)
        ellipse_path(c, ex + look * r * 0.45, ey + 2, r * 0.42, r * 0.46)
        c.set_source_rgb(*INK)
        c.fill()
        b = p["blink"]
        if b > 0:
            c.save()
            ellipse_path(c, ex, ey, r + 1, r * 1.05 + 1)
            c.clip()
            c.rectangle(ex - r - 3, ey - r * 1.1 - 3, 2 * r + 6, (2 * r * 1.1 + 6) * b)
            c.set_source_rgb(*rgb("D8D2E2"))
            c.fill()
            c.move_to(ex - r, ey - r * 1.1 + (2 * r * 1.1) * b)
            c.line_to(ex + r, ey - r * 1.1 + (2 * r * 1.1) * b)
            c.set_source_rgb(*INK)
            c.set_line_width(5)
            c.stroke()
            c.restore()
    # houppette
    for k, a in enumerate((-0.4, 0.0, 0.4)):
        c.move_to(10 + k * 10, -96)
        c.line_to(10 + k * 10 + 18 * math.sin(a), -96 - 22 * math.cos(a))
        c.set_source_rgb(*INK)
        c.set_line_width(5)
        c.stroke()
    c.restore()  # tête

    c.restore()
