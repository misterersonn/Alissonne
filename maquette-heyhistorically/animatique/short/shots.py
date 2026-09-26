"""Rend les personnages de chaque plan du short (PNG transparents, 24 i/s).

Un nouveau dessin toutes les 2 images (12 dessins/s). Lancer :
  xvfb-run -a blender -b --python shots.py -- <dossier_sortie> [plan ...]
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gp_lib import Canvas, emu, lewis_gun, muzzle, soldier  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
OUT = argv[0]
ONLY = set(argv[1:])
ON = 2


def jit(f, amp, seed=0):
    r = random.Random(f * 7 + seed)
    return r.uniform(-amp, amp), r.uniform(-amp, amp)


def s1(cv, f):  # gros plan : le soldat transpire
    dx, dy = jit(f, 3)
    soldier(cv, 360 + dx, 520 + dy, 2.3, eyes="wide", mouth="wobble", sweat=True, look=(1 if f > 24 else 0, 0),
            hand_l=(150, 1150), hand_r=(570, 1150))


def s2(cv, f):  # gros plan : l'émeu fixe la caméra, clignement
    blink = 26 <= f < 30
    emu(cv, 250, 1050, 2.4, None, eyes="closed" if blink else "wide", look=(0.2, 0.1), bob=-4 * math.sin(f / 6))


def s3(cv, f):  # l'émeu debout, on affiche ses stats
    emu(cv, 300, 820, 1.25, None, eyes="wide", look=(0.6, 0), beak_open=(f // 6) % 2 == 1, bob=-6 * abs(math.sin(f / 5)))


def s4(cv, f):  # le major salue, très sûr de lui
    up = min(1.0, f / 8)
    hr = (360 + 250, 470 - 150 * up) if f >= 4 else (590, 900)
    soldier(cv, 330, 450, 1.9, hat="cap", mustache=True, eyes="dot", mouth="smile", hand_r=hr,
            hand_l=(130, 980), bob=-4 * abs(math.sin(f / 4)))


def s5(cv, f):  # la mitrailleuse tire
    dx, dy = jit(f, 6, 5)
    lewis_gun(cv, 330 + dx, 700 + dy, 1.35, -0.12)
    if (f // 2) % 2 == 0:
        muzzle(cv, 690 + dx, 650 + dy, 1.3, f)


def s6(cv, f):  # les émeus s'enfuient dans tous les sens
    ph = (f // 2) % 4
    for i, (x0, y0, sp, sc) in enumerate(((-150, 700, 16, 0.8), (-420, 900, 19, 1.0), (-260, 1120, 14, 0.9))):
        emu(cv, x0 + sp * f, y0 - 10 * abs(math.sin((f + i * 3) / 3)), sc, (ph + i) % 4, eyes="wide", look=(1, 0))


def s7(cv, f):  # le soldat, désabusé
    soldier(cv, 360, 560, 2.0, eyes="closed", mouth="frown", hand_r=(470, 560), gl_r="open",
            hand_l=(160, 1080), head_rot=-0.08 + 0.02 * math.sin(f / 5))


def s8(cv, f):  # la tactique des émeus (fond rose)
    emu(cv, 330, 800, 1.25, None, eyes="closed", beak_open=False, bob=-8 * abs(math.sin(f / 5)))


def s9(cv, f):  # le compteur : le soldat déprime
    soldier(cv, 360, 640, 2.0, eyes="sad", mouth="frown", sweat=True, hand_l=(170, 1150), hand_r=(550, 1150))


def s11(cv, f):  # l'émeu couronné, triomphant
    emu(cv, 330, 850, 1.3, None, eyes="angry", beak_open=(f // 8) % 2 == 0, crown=True, bob=-10 * abs(math.sin(f / 4)))


SHOTS = [("s1", s1, 48), ("s2", s2, 48), ("s3", s3, 60), ("s4", s4, 60), ("s5", s5, 48), ("s6", s6, 60),
         ("s7", s7, 48), ("s8", s8, 48), ("s9", s9, 48), ("s11", s11, 60)]

cv = Canvas()
for name, fn, n in SHOTS:
    if ONLY and name not in ONLY:
        continue
    cv.clear()
    for f in range(1, n + 1, ON):
        cv.new_drawing(f)
        fn(cv, f)
    cv.render(os.path.join(OUT, name), 1, n)
    print("SHOT_OK", name, flush=True)
