"""Rigs et effets de chaque plan (coordonnées en pixels des images 1600×893)."""
import math

from puppet import (Move, Rig, Rot, Squash, action_marks, casings, feathers, ink_line,
                    layer_for, muzzle, puffs, rocks, sweat, tears, vein, on_twos)

sin, cos, pi = math.sin, math.cos, math.pi


def osc(freq, amp, phase=0.0):
    return lambda t: amp * sin(2 * pi * freq * t + phase)


def bob(freq, amp, phase=0.0):
    """Rebond de course : toujours vers le haut."""
    return lambda t: (0, -amp * abs(sin(pi * freq * t + phase)))


def firing(t):
    return (t % 0.9) < 0.45 and t < 4.2


def build(imgs):
    S = {}

    # ---------------------------------------------------- 1. le soldat pleure
    r1 = Rig(imgs["p1"], [
        # tête qui sanglote : balancement + hoquets verticaux
        Rot(270, 420, 300, 360, (290, 760), lambda t: 2.2 * sin(2 * pi * 0.7 * t) + 1.2 * sin(2 * pi * 3.1 * t)),
        Squash(270, 420, 300, 360, (280, 720), lambda t: (1.0, 1 + 0.018 * abs(sin(2 * pi * 1.6 * t)))),
        # bouche qui tremble
        Move(275, 500, 120, 60, lambda t: (4 * sin(2 * pi * 5 * t), 3 * sin(2 * pi * 2.5 * t)), inner=0.3),
        # sourcils qui se froncent par à-coups
        Move(160, 320, 90, 50, lambda t: (0, -5 * abs(sin(2 * pi * 0.8 * t))), inner=0.3),
        Move(350, 280, 90, 50, lambda t: (0, -5 * abs(sin(2 * pi * 0.8 * t + 0.4))), inner=0.3),
        # les émeus galopent
        Move(930, 500, 170, 230, bob(2.6, 12)),
        Move(720, 450, 130, 150, bob(2.6, 10, 1.1)),
        Move(1140, 420, 110, 130, bob(2.6, 9, 2.0)),
        Move(1340, 450, 130, 160, bob(2.6, 11, 0.6)),
        Move(1500, 420, 110, 140, bob(2.6, 9, 1.6)),
        Move(830, 330, 80, 90, bob(2.6, 6, 2.4)),
        Move(1030, 320, 80, 90, bob(2.6, 6, 0.3)),
    ])

    def p1(t):
        img = r1.pose(t).copy()
        lay, d = layer_for(img)
        tears(d, t, [(150, 400), (140, 470), (128, 560), (125, 660)], rate=1.8, seed=1)
        tears(d, t, [(400, 380), (412, 450), (420, 530), (425, 610)], rate=2.1, seed=2)
        puffs(d, t, 980, 700, seed=1, count=6, spread=140, size=38)
        puffs(d, t, 1360, 620, seed=2, count=4, spread=100, size=30)
        img.paste(lay, (0, 0), lay)
        return img
    S["p1"] = p1

    # ---------------------------------------------------- 2. les fermiers
    r2 = Rig(imgs["p2"], [
        Rot(310, 360, 160, 150, (320, 500), osc(0.5, 3.0)),
        Rot(635, 335, 135, 135, (640, 480), osc(0.45, -3.0, 1.0)),
        Rot(870, 330, 125, 125, (870, 460), osc(0.55, 3.5, 2.0)),
        # respiration fière (torse gonflé)
        Squash(330, 560, 170, 140, (330, 700), lambda t: (1 + 0.015 * sin(2 * pi * 0.5 * t), 1 + 0.02 * sin(2 * pi * 0.5 * t))),
        Squash(650, 560, 170, 130, (650, 700), lambda t: (1 + 0.02 * sin(2 * pi * 0.45 * t + 1), 1 + 0.02 * sin(2 * pi * 0.45 * t + 1))),
        # la fourche tape le sol
        Move(1040, 560, 110, 330, lambda t: (0, -10 * max(0, sin(2 * pi * 0.9 * t)) ** 3), inner=0.6),
        # l'émeu passe la tête hors du blé puis se cache
        Move(1420, 720, 230, 260, lambda t: (0, 90 * (1 - min(1, max(0, (t - 0.8) / 0.5))) + (70 * min(1, max(0, (t - 4.0) / 0.4)))), inner=0.7),
        Rot(1420, 690, 150, 120, (1420, 820), lambda t: 12 * sin(2 * pi * 0.6 * max(0, t - 1.3))),
        # éolienne qui tourne
        Rot(1325, 160, 150, 150, (1325, 160), lambda t: -120 * t, inner=0.75),
    ])

    def p2(t):
        img = r2.pose(t).copy()
        lay, d = layer_for(img)
        puffs(d, t, 490, 60, seed=3, count=5, spread=20, size=24, color=(214, 214, 214), drift=(40, -120), life=1.6)
        if 1.3 < t < 4.0 and int(t * 4) % 3 == 0:
            action_marks(d, t, 1420, 610, seed=4, size=70, angle=-1.9)
        img.paste(lay, (0, 0), lay)
        return img
    S["p2"] = p2

    # ---------------------------------------------------- 3. le fermier hurle
    r3 = Rig(imgs["p3"], [
        Rot(1230, 340, 200, 200, (1230, 540), lambda t: 3.5 * sin(2 * pi * 6 * t)),
        Squash(1230, 360, 190, 190, (1230, 540), lambda t: (1 - 0.03 * abs(sin(2 * pi * 3 * t)), 1 + 0.04 * abs(sin(2 * pi * 3 * t)))),
        # bouche qui s'ouvre plus grand
        Squash(1235, 380, 110, 100, (1235, 300), lambda t: (1, 1 + 0.08 * abs(sin(2 * pi * 2 * t)))),
        # bras qui s'agitent
        Rot(990, 230, 130, 130, (1040, 390), lambda t: 14 * sin(2 * pi * 4 * t)),
        Rot(1500, 300, 130, 150, (1440, 460), lambda t: -14 * sin(2 * pi * 4 * t + 1)),
        # l'émeu mâche tranquillement
        Rot(650, 280, 130, 110, (560, 420), osc(0.6, 5)),
        Move(700, 320, 70, 50, lambda t: (0, 6 * abs(sin(2 * pi * 2.5 * t))), inner=0.3),
        Squash(400, 520, 230, 200, (400, 700), lambda t: (1 + 0.012 * sin(2 * pi * 0.5 * t), 1 + 0.012 * sin(2 * pi * 0.5 * t))),
        # émeus du fond qui picorent
        Move(470, 240, 90, 110, bob(1.5, 10)),
        Move(820, 230, 110, 120, bob(1.5, 10, 1)),
        Move(250, 230, 90, 110, bob(1.5, 8, 2)),
        Move(100, 280, 90, 110, bob(1.5, 8, 0.5)),
    ])

    def p3(t):
        img = r3.pose(t).copy()
        lay, d = layer_for(img)
        vein(d, t, 1345, 270, size=40, seed=5)
        action_marks(d, t, 960, 170, seed=6, size=60, angle=-2.4)
        action_marks(d, t, 1545, 240, seed=7, size=60, angle=-0.7)
        # brins de blé qui volent
        tq = on_twos(t)
        for k in range(7):
            x = 440 + ((k * 137 + tq * 220) % 520)
            y = 90 + 40 * sin(tq * 3 + k) + k * 22
            a = tq * 4 + k
            ink_line(d, [(x - 22 * cos(a), y - 22 * sin(a)), (x + 22 * cos(a), y + 22 * sin(a))], t, 40 + k, width=7, color=(222, 176, 70))
        puffs(d, t, 880, 640, seed=8, count=4, spread=120, size=40)
        img.paste(lay, (0, 0), lay)
        return img
    S["p3"] = p3

    # ---------------------------------------------------- 4. le major
    def salute(t):
        # le salut claque au début avec un rebond, puis vibre de fierté
        k = min(1.0, t / 0.35)
        snap = -35 * (1 - k) ** 2 + 6 * math.exp(-6 * t) * sin(20 * t)
        return snap + 1.2 * sin(2 * pi * 1.5 * t)

    r4 = Rig(imgs["p4"], [
        Rot(590, 380, 300, 290, (590, 690), lambda t: 2.0 * sin(2 * pi * 0.6 * t)),
        Move(650, 265, 110, 60, lambda t: (0, -10 * max(0, sin(2 * pi * 1.1 * t)) ** 2), inner=0.3),  # sourcil
        Move(520, 420, 140, 70, lambda t: (0, -4 * abs(sin(2 * pi * 2.2 * t))), inner=0.3),              # moustache
        Rot(270, 330, 130, 150, (340, 450), salute),
        Squash(560, 720, 330, 180, (560, 893), lambda t: (1 + 0.015 * sin(2 * pi * 0.6 * t), 1 + 0.02 * sin(2 * pi * 0.6 * t))),
        Move(1050, 480, 170, 330, bob(1.6, 10)),
        Move(1320, 480, 170, 330, bob(1.6, 10, 1.6)),
    ])

    def p4(t):
        img = r4.pose(t).copy()
        lay, d = layer_for(img)
        if t < 1.0:
            action_marks(d, t, 250, 250, seed=9, size=80, angle=-2.3)
        # étincelle sur le sourire
        if int(on_twos(t) * 12) % 10 < 3:
            s = 26
            ink_line(d, [(700, 440 - s), (700, 440 + s)], t, 50, width=8, color=(255, 250, 220))
            ink_line(d, [(700 - s, 440), (700 + s, 440)], t, 51, width=8, color=(255, 250, 220))
        img.paste(lay, (0, 0), lay)
        return img
    S["p4"] = p4

    # ---------------------------------------------------- 5. la bataille
    r5 = Rig(imgs["p5"], [
        Move(830, 450, 260, 230, lambda t: (7 * sin(2 * pi * 12 * t) if firing(t) else 0, 0), inner=0.6),
        Rot(905, 290, 85, 85, (905, 360), lambda t: 6 * sin(2 * pi * 7 * t)),
        Rot(1080, 330, 90, 90, (1080, 400), lambda t: -5 * sin(2 * pi * 6 * t + 1)),
        Move(1110, 470, 120, 90, lambda t: (0, 5 * sin(2 * pi * 5 * t))),  # passe la bande
        Move(190, 270, 200, 170, lambda t: (0, -14 * abs(sin(pi * 3 * t)))),
        Move(290, 660, 280, 250, lambda t: (0, -16 * abs(sin(pi * 3 * t + 1)))),
        Move(1330, 700, 190, 190, lambda t: (0, -14 * abs(sin(pi * 3 * t + 2)))),
        Squash(1480, 260, 180, 170, (1480, 260), lambda t: (1 + 0.05 * sin(2 * pi * 2 * t), 1 + 0.05 * sin(2 * pi * 2 * t))),
        Squash(570, 170, 130, 110, (570, 170), lambda t: (1 + 0.06 * sin(2 * pi * 2.4 * t), 1 + 0.06 * sin(2 * pi * 2.4 * t))),
    ])

    def p5(t):
        img = r5.pose(t).copy()
        lay, d = layer_for(img)
        if firing(t):
            muzzle(d, t, 590, 420, seed=10, size=95)
            casings(d, t, 850, 380, seed=11)
        sweat(d, t, 985, 290, period=0.9, seed=12)
        sweat(d, t, 1150, 330, period=1.1, seed=13)
        puffs(d, t, 250, 830, seed=14, count=5, spread=160, size=40, drift=(-80, -30))
        puffs(d, t, 1300, 830, seed=15, count=4, spread=120, size=36, drift=(80, -30))
        puffs(d, t, 330, 360, seed=16, count=3, spread=90, size=30, drift=(-60, -20))
        img.paste(lay, (0, 0), lay)
        return img
    S["p5"] = p5

    # ---------------------------------------------------- 6. le camion
    r6 = Rig(imgs["p6"], [
        Rot(560, 430, 470, 330, (560, 640), lambda t: 3.5 * sin(2 * pi * 2.2 * t), inner=0.7),
        Move(560, 430, 470, 330, lambda t: (0, -18 * abs(sin(pi * 2.2 * t))), inner=0.7),
        Rot(600, 255, 60, 60, (600, 300), lambda t: 8 * sin(2 * pi * 6 * t)),
        # le soldat éjecté tournoie et flotte
        Rot(970, 170, 230, 150, (970, 170), lambda t: 8 * sin(2 * pi * 0.9 * t) + 4 * t, inner=0.7),
        Move(970, 170, 230, 150, lambda t: (10 * t, -12 * sin(2 * pi * 0.8 * t)), inner=0.7),
        Rot(870, 105, 80, 60, (930, 130), lambda t: 20 * sin(2 * pi * 3 * t)),
        Rot(1130, 205, 70, 60, (1080, 190), lambda t: -20 * sin(2 * pi * 3 * t + 1)),
        # l'émeu court sans effort
        Move(1250, 520, 280, 260, bob(3.2, 10)),
        Rot(1240, 740, 200, 160, (1270, 600), lambda t: 9 * sin(2 * pi * 1.6 * t)),
        Rot(1400, 170, 120, 110, (1380, 330), osc(0.7, 4)),
    ])

    def p6(t):
        img = r6.pose(t).copy()
        lay, d = layer_for(img)
        rocks(d, t, 420, 700, seed=17, n=7)
        rocks(d, t, 1120, 800, seed=18, n=5, spread=120)
        puffs(d, t, 130, 520, seed=19, count=6, spread=110, size=60, drift=(-120, -40), life=1.1)
        puffs(d, t, 1110, 840, seed=20, count=4, spread=90, size=34, drift=(-80, -10))
        action_marks(d, t, 1180, 90, seed=21, size=50, angle=-0.4)
        img.paste(lay, (0, 0), lay)
        return img
    S["p6"] = p6

    # ---------------------------------------------------- 7. le parlement
    laughers = [(120, 320, 75), (230, 480, 110), (400, 420, 85), (300, 265, 50), (385, 310, 50),
                (460, 320, 45), (580, 370, 50), (1030, 365, 45), (1140, 320, 50), (1225, 330, 55),
                (1290, 265, 45), (1200, 430, 90), (1480, 350, 80), (1450, 240, 45), (1560, 230, 50),
                (1360, 490, 85), (50, 220, 50)]
    defs = []
    for i, (x, y, r) in enumerate(laughers):
        f = 3.2 + (i % 4) * 0.5
        defs.append(Move(x, y, r, r, (lambda f, i: lambda t: (0, -r * 0.12 * abs(sin(pi * f * t + i))))(f, i)))
        defs.append(Rot(x, y, r, r, (x, y + r), (lambda f, i: lambda t: 5 * sin(2 * pi * f * 0.5 * t + i))(f, i)))
    defs += [
        Move(270, 350, 70, 40, lambda t: (8 * sin(2 * pi * 2 * t), 0)),   # doigts pointés
        Move(470, 515, 80, 40, lambda t: (8 * sin(2 * pi * 2 * t + 1), 0)),
        Move(1040, 485, 70, 40, lambda t: (-8 * sin(2 * pi * 2 * t + 2), 0)),
        Rot(810, 320, 105, 100, (810, 420), lambda t: 1.5 * sin(2 * pi * 9 * t)),  # le ministre tremble
        Move(810, 500, 150, 110, lambda t: (2.5 * sin(2 * pi * 11 * t), 0), inner=0.7),
    ]
    r7 = Rig(imgs["p7"], defs)

    def p7(t):
        img = r7.pose(t).copy()
        lay, d = layer_for(img)
        sweat(d, t, 915, 262, period=1.3, fall=90, seed=22, size=20)
        sweat(d, t, 745, 300, period=1.0, fall=60, seed=23, size=14)
        tears(d, t, [(1335, 480), (1332, 520)], rate=2.5, seed=24, size=10)
        img.paste(lay, (0, 0), lay)
        return img
    S["p7"] = p7

    # ---------------------------------------------------- 8. la victoire
    r8 = Rig(imgs["p8"], [
        Rot(790, 110, 100, 95, (790, 240), osc(0.8, 6)),
        Squash(860, 320, 180, 150, (860, 460), lambda t: (1 + 0.02 * sin(2 * pi * 0.8 * t), 1 + 0.03 * sin(2 * pi * 0.8 * t))),
        Rot(300, 450, 110, 120, (390, 500), lambda t: 16 * sin(2 * pi * 2.5 * t)),
        Rot(510, 420, 90, 110, (460, 480), lambda t: -16 * sin(2 * pi * 2.5 * t)),
        Rot(1060, 420, 100, 130, (1120, 480), lambda t: 16 * sin(2 * pi * 2.3 * t + 1)),
        Rot(1270, 380, 100, 130, (1200, 460), lambda t: -16 * sin(2 * pi * 2.3 * t + 1)),
        Move(440, 375, 60, 60, bob(2.5, 12)),
        Move(385, 440, 55, 55, bob(2.5, 10, 1)),
        Move(1135, 345, 60, 60, bob(2.3, 12, 0.5)),
        Move(1335, 470, 60, 60, bob(2.3, 10, 1.5)),
        # soldats qui repartent, tête basse
        Move(150, 760, 170, 120, lambda t: (-8 * t, -6 * abs(sin(pi * 2 * t)))),
        Move(1480, 740, 150, 120, lambda t: (8 * t, -6 * abs(sin(pi * 2 * t + 1)))),
        Move(1150, 760, 90, 110, lambda t: (0, -5 * abs(sin(pi * 1.8 * t)))),
        Move(1350, 810, 80, 90, lambda t: (0, -5 * abs(sin(pi * 1.8 * t + 1)))),
    ])

    def p8(t):
        img = r8.pose(t).copy()
        lay, d = layer_for(img)
        feathers(d, t, (80, -40, 1540, 560), n=9, seed=25, speed=110)
        img.paste(lay, (0, 0), lay)
        return img
    S["p8"] = p8

    return S
