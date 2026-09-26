"""Extrait animé Grease Pencil : le fermier du plan 3, dessiné image par image.

Chaque dessin est une image clé Grease Pencil à part (un nouveau dessin toutes
les 2 images à 24 i/s, soit 12 dessins/s). Les poses viennent d'une feuille
d'exposition ; entre deux poses clés, les intervalles sont redessinés (pas
déformés), avec dépassement sur l'explosion et secousse pendant le cri.

Lancer :
  xvfb-run -a blender -b --python gp_anim.py -- <dossier_png> [<fichier.blend>]
"""
import math
import os
import random
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUTDIR = argv[0] if argv else "/tmp/gp_anim"
BLEND = argv[1] if len(argv) > 1 else None
PW, PH = 1600, 893
FPS = 24
FRAMES = 96          # 4 s
ON = 2               # un dessin toutes les 2 images


def srgb(h):
    h = h.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


# ------------------------------------------------------------ scène
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE_NEXT"
sc.eevee.taa_render_samples = 4
sc.render.resolution_x, sc.render.resolution_y = PW, PH
sc.render.film_transparent = True
sc.view_settings.view_transform = "Standard"
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
sc.render.fps = FPS
sc.frame_start, sc.frame_end = 1, FRAMES

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
cam.data.type = "ORTHO"
cam.data.ortho_scale = PW / 100
cam.location = (0, -20, 0)
cam.rotation_euler = (math.pi / 2, 0, 0)
sc.camera = cam

gpd = bpy.data.grease_pencils.new("farmer")
gpd.stroke_depth_order = "2D"
gpd.pixel_factor = 10.0
ob = bpy.data.objects.new("farmer", gpd)
sc.collection.objects.link(ob)
layer = gpd.layers.new("dessin")
layer.use_lights = False

MATS = {}


def mat(name, stroke=None, fill=None):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    bpy.data.materials.create_gpencil_data(m)
    g = m.grease_pencil
    g.show_stroke = stroke is not None
    g.show_fill = fill is not None
    if stroke:
        g.color = srgb(stroke)
    if fill:
        g.fill_color = srgb(fill)
    gpd.materials.append(m)
    MATS[name] = len(gpd.materials) - 1
    return MATS[name]


INK = mat("ink", stroke="1B1724")
STICKER = mat("sticker", stroke="FFFFFF")
GLOVE = mat("glove", stroke="FFFFFF")
SLEEVE = mat("sleeve", stroke="E9D6B4")
STRAP = mat("strap", stroke="5E82AE")
VEIN = mat("vein", stroke="D62434")
BLUSH = mat("blush", fill="F08C96")
F_WHITE = mat("f_white", fill="FFFFFF")
F_SHIRT = mat("f_shirt", fill="E9D6B4")
F_SHIRT_SH = mat("f_shirt_sh", fill="C9AE86")
F_DENIM = mat("f_denim", fill="5E82AE")
F_DENIM_SH = mat("f_denim_sh", fill="45679A")
F_MOUTH = mat("f_mouth", fill="6E1220")
F_TONGUE = mat("f_tongue", fill="E9667A")
F_GOLD = mat("f_gold", fill="E0B24A")
F_SHADE = mat("f_shade", fill="C9C3D6")

CUR = {"frame": None, "seed": 0}


def P(x, y):
    return ((x - PW / 2) / 100, 0, (PH / 2 - y) / 100)


def stroke(pts, material, width, cyclic=False, taper=True, wobble=0.0):
    fr = CUR["frame"]
    s = fr.strokes.new()
    s.material_index = material
    s.line_width = int(max(1, width))
    s.use_cyclic = cyclic
    s.display_mode = "3DSPACE"
    n = len(pts)
    s.points.add(n)
    CUR["seed"] += 1
    # chaque dessin a son petit tremblé de trait, comme redessiné à la main
    r = random.Random(CUR["seed"] * 31 + fr.frame_number)
    j = 1.2
    for i, (x, y) in enumerate(pts):
        u = i / max(1, n - 1)
        pr = 1.0
        if taper and not cyclic:
            pr = 0.25 + 0.75 * math.sin(math.pi * u) ** 0.6
        if wobble:
            pr *= 1 + wobble * math.sin(i * 1.7 + CUR["seed"])
        s.points[i].co = P(x + r.uniform(-j, j), y + r.uniform(-j, j))
        s.points[i].pressure = pr
        s.points[i].strength = 1.0


def ellipse(cx, cy, rx, ry, n=64, rot=0.0):
    out = []
    for i in range(n):
        a = i / n * 2 * math.pi
        x, y = rx * math.cos(a), ry * math.sin(a)
        out.append((cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot)))
    return out


def smooth(pts, closed=True, steps=8):
    out = []
    n = len(pts)
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0, p1 = pts[(i - 1) % n], pts[i]
        p2, p3 = pts[(i + 1) % n], pts[(i + 2) % n]
        if not closed:
            p0, p3 = pts[max(0, i - 1)], pts[min(n - 1, i + 2)]
        for k in range(steps):
            t = k / steps
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[q]) + (-p0[q] + p2[q]) * t + (2 * p0[q] - 5 * p1[q] + 4 * p2[q] - p3[q]) * t2
                                    + (-p0[q] + 3 * p1[q] - 3 * p2[q] + p3[q]) * t3) for q in (0, 1)))
    if not closed:
        out.append(pts[-1])
    return out


def shape(pts, fill, outline=9, sticker=0, shade=None):
    if sticker:
        stroke(pts, STICKER, outline + sticker, cyclic=True, taper=False)
    stroke(pts, fill, 1, cyclic=True, taper=False)
    if shade:
        stroke(shade[0], shade[1], 1, cyclic=True, taper=False)
    stroke(pts, INK, outline, cyclic=True, taper=False, wobble=0.18)


def rot_pts(pts, cx, cy, a):
    ca, sa = math.cos(a), math.sin(a)
    return [(cx + (x - cx) * ca - (y - cy) * sa, cy + (x - cx) * sa + (y - cy) * ca) for x, y in pts]


# ------------------------------------------------------------ pièces
def glove(cx, cy, angle, spread=1.0, s=1.3):
    ca, sa = math.cos(angle), math.sin(angle)

    def R(x, y):
        return (cx + (x * ca - y * sa) * s, cy + (x * sa + y * ca) * s)
    fingers = [(-0.62, 60), (-0.2, 70), (0.2, 68), (0.6, 58)]
    segs = [[R(0, -8), R(math.sin(a * spread) * L, -8 - math.cos(a * spread) * L)] for a, L in fingers]
    segs.append([R(-6, 12), R(-60, -4)])
    for sg in segs:
        stroke(sg, STICKER, 58 * s, taper=False)
    for sg in segs:
        stroke(sg, INK, 40 * s, taper=False)
    for sg in segs:
        stroke(sg, GLOVE, 26 * s, taper=False)
    palm = ellipse(*R(0, 10), 42 * s, 38 * s, 40, angle)
    stroke(palm, STICKER, 26, cyclic=True, taper=False)
    shape(palm, F_WHITE, 8)
    for (x0, y0), (x1, y1) in segs:
        stroke([(x0, y0), (x0 + (x1 - x0) * 0.5, y0 + (y1 - y0) * 0.5)], GLOVE, 24 * s, taper=False)


def fist(cx, cy, angle, s=1.3, point=False):
    ca, sa = math.cos(angle), math.sin(angle)

    def R(x, y):
        return (cx + (x * ca - y * sa) * s, cy + (x * sa + y * ca) * s)
    if point:
        seg = [R(6, -30), R(6, -112)]
        stroke(seg, STICKER, 58 * s, taper=False)
        stroke(seg, INK, 40 * s, taper=False)
        stroke(seg, GLOVE, 26 * s, taper=False)
    body = smooth([R(-44, -30), R(0, -46), R(44, -30), R(50, 20), R(20, 44), R(-30, 40), R(-52, 10)], True, 6)
    stroke(body, STICKER, 26, cyclic=True, taper=False)
    shape(body, F_WHITE, 8)
    if point:
        stroke([R(6, -40), R(6, -70)], GLOVE, 24 * s, taper=False)
    for k in range(3 if point else 4):
        xx = -30 + k * 20 + (18 if point else 0)
        stroke(smooth([R(xx, -36), R(xx + 4, -16), R(xx, 4)], False, 4), INK, 5)
    stroke(smooth([R(-50, 2), R(-20, 14), R(10, 2)], False, 4), INK, 5)


def arm(sx, sy, hx, hy, bend):
    """Bras en deux segments ; le coude est placé sur le côté (`bend`)."""
    mx, my = (sx + hx) / 2, (sy + hy) / 2
    dx, dy = hx - sx, hy - sy
    L = math.hypot(dx, dy) or 1
    ex, ey = mx - dy / L * bend, my + dx / L * bend
    path = smooth([(sx, sy), (ex, ey), (hx, hy)], closed=False, steps=8)
    stroke(path, STICKER, 118, taper=False)
    stroke(path, INK, 96, taper=False)
    stroke(path, SLEEVE, 80, taper=False)
    return math.atan2(hy - ey, hx - ex) + math.pi / 2


def farmer(p):
    ox, oy = p["body"]
    # bras (derrière la tête, devant le torse quand ils sont repliés)
    def arms():
        for side in ("l", "r"):
            sx = 1030 + ox if side == "l" else 1330 + ox
            hx, hy = p["hand_" + side]
            a = arm(sx, 635 + oy, hx, hy, p["bend_" + side])
            mode = p["mode_" + side]
            if mode == "open":
                glove(hx, hy - 20, a, p["spread"])
            else:
                fist(hx, hy - 10, a, point=(mode == "point"))
    if not p["arms_front"]:
        arms()

    # torse
    shirt = smooth([(1030, 600), (1120, 570), (1240, 570), (1330, 600), (1362, 705), (1340, 985), (1020, 985), (998, 705)])
    shirt = [(x + ox, y + oy) for x, y in shirt]
    shirt_sh = [(x + ox, y + oy) for x, y in smooth([(1260, 600), (1330, 610), (1360, 705), (1340, 985), (1250, 985), (1275, 800)])]
    shape(shirt, F_SHIRT, 9, sticker=18, shade=(shirt_sh, F_SHIRT_SH))
    for sgn in (-1, 1):
        shape([(1180 + ox, 575 + oy), (1180 + sgn * 70 + ox, 570 + oy), (1180 + sgn * 45 + ox, 625 + oy)], F_SHIRT, 7)
        seg = [(1180 + sgn * 88 + ox, 740 + oy), (1180 + sgn * 125 + ox, 593 + oy)]
        stroke(seg, INK, 44, taper=False)
        stroke(seg, STRAP, 30, taper=False)
    bib = [(1080 + ox, 730 + oy), (1280 + ox, 730 + oy), (1298 + ox, 985 + oy), (1062 + ox, 985 + oy)]
    bib_sh = [(1220 + ox, 730 + oy), (1280 + ox, 730 + oy), (1298 + ox, 985 + oy), (1240 + ox, 985 + oy)]
    shape(bib, F_DENIM, 9, shade=(bib_sh, F_DENIM_SH))
    shape([(1125 + ox, 785 + oy), (1235 + ox, 785 + oy), (1235 + ox, 863 + oy), (1125 + ox, 863 + oy)], F_DENIM, 6)
    for sgn in (-1, 1):
        shape(ellipse(1180 + sgn * 82 + ox, 745 + oy, 13, 13, 20), F_GOLD, 5)
    if p["arms_front"]:
        arms()

    # tête (tout ce qui suit tourne autour du cou)
    hx, hy = 1185 + ox + p["head"][0], 350 + oy + p["head"][1]
    sy = p["head_sy"]
    ang = math.radians(p["head_rot"])
    neck = (hx, hy + 186 * sy)

    def H(pts):
        return rot_pts([(x, hy + (y - hy) * sy) for x, y in pts], *neck, ang)
    head = H(ellipse(hx, hy, 192, 186, 72))
    shape(head, F_WHITE, 11, sticker=20)
    # ombre : un coup de pinceau épais le long du bord bas-droit, à l'intérieur
    arc = [i / 30 for i in range(31)]
    sh = [(hx + 168 * math.cos(-0.35 + 2.3 * u), hy + 162 * math.sin(-0.35 + 2.3 * u)) for u in arc]
    stroke(H(sh), mat("shade", stroke="C9C3D6"), 38)
    stroke(head, INK, 11, cyclic=True, taper=False, wobble=0.18)

    for sgn in (-1, 1):
        stroke(H(smooth([(hx + sgn * 150, hy - 92), (hx + sgn * 100, hy - 74), (hx + sgn * 40, hy - 52)], False, 8)), INK, 22)
        stroke(H([(hx + sgn * 125, hy - 45), (hx + sgn * 62, hy - 22), (hx + sgn * 122, hy - 2)]), INK, 12, taper=False)
        stroke(H([(hx + sgn * 150, hy - 30), (hx + sgn * 172, hy - 17)]), INK, 6)
        stroke(H([(hx + sgn * 18, hy - 40), (hx + sgn * 10, hy - 10)]), INK, 6)

    o = p["mouth"]
    if p["face"] == "tight":
        for sgn in (-1, 1):
            stroke(H(ellipse(hx + sgn * 118, hy + 40, 46, 30, 30)), BLUSH, 1, cyclic=True, taper=False)
        stroke(H([(hx - 70, hy + 70), (hx - 45, hy + 58), (hx - 20, hy + 74), (hx + 5, hy + 58), (hx + 30, hy + 74),
                  (hx + 55, hy + 58), (hx + 75, hy + 70)]), INK, 11, taper=False)
    else:
        mw, mh = 50 + 60 * o, 14 + 166 * o
        mouth = H(smooth([(hx - mw * 0.8, hy + 30), (hx - mw * 0.45, hy + 4), (hx, hy - 2), (hx + mw * 0.45, hy + 4),
                          (hx + mw * 0.8, hy + 30), (hx + mw, hy + 18 + mh * 0.75), (hx + mw * 0.55, hy + 18 + mh),
                          (hx - mw * 0.55, hy + 18 + mh), (hx - mw, hy + 18 + mh * 0.75)], True, 8))
        stroke(mouth, F_MOUTH, 1, cyclic=True, taper=False)
        if o > 0.35:
            tw = mw * 0.56
            stroke(H(smooth([(hx - tw, hy + 18 + mh * 0.88), (hx, hy + 18 + mh * 0.7), (hx + tw, hy + 18 + mh * 0.88),
                             (hx + tw * 0.8, hy + 16 + mh), (hx - tw * 0.8, hy + 16 + mh)], True, 6)),
                   F_TONGUE, 1, cyclic=True, taper=False)
            stroke(H(smooth([(hx - mw * 0.7, hy + 20), (hx, hy + 2), (hx + mw * 0.7, hy + 20), (hx + mw * 0.55, hy + 38),
                             (hx, hy + 32), (hx - mw * 0.55, hy + 38)], True, 5)), F_WHITE, 1, cyclic=True, taper=False)
        stroke(mouth, INK, 12, cyclic=True, taper=False, wobble=0.2)

    v = p["vein"]
    if v > 0.05:
        vx, vy = hx + 118, hy - 118
        for q in range(4):
            a = q * math.pi / 2 + math.pi / 4
            pts = []
            for k in range(9):
                u = k / 8
                lx, ly = (-16 + 32 * u) * v, (-28 + 14 * math.sin(math.pi * u)) * v
                pts.append((vx + lx * math.cos(a) - ly * math.sin(a), vy + lx * math.sin(a) + ly * math.cos(a)))
            stroke(H(pts), VEIN, 12 * v)

    for (cx, cy, base) in p["marks"]:
        for k in range(3):
            a = base + (k - 1) * 0.45
            stroke([(cx + math.cos(a) * 80, cy + math.sin(a) * 80), (cx + math.cos(a) * 140, cy + math.sin(a) * 140)], INK, 10)


# ------------------------------------------------------------ poses clés
BASE = dict(body=(0, 0), head=(0, 0), head_rot=0, head_sy=1.0, mouth=0.15, face="open", vein=0.0,
            hand_l=(960, 900), hand_r=(1400, 900), bend_l=40, bend_r=-40, mode_l="open", mode_r="open",
            spread=0.8, arms_front=False, marks=())
KEYS = {
    "calm": dict(BASE),
    "hold": dict(BASE, body=(0, 22), head=(0, 26), head_sy=0.92, face="tight", vein=0.8, mode_l="fist", mode_r="fist",
                 hand_l=(1130, 690), hand_r=(1230, 690), bend_l=-70, bend_r=70, arms_front=True),
    "scream": dict(BASE, body=(0, -14), head=(0, -24), head_sy=1.06, mouth=1.0, vein=1.15, hand_l=(860, 300),
                   hand_r=(1500, 300), bend_l=-30, bend_r=30, spread=1.1,
                   marks=((790, 190, -2.4), (1570, 190, -0.7))),
    "scream2": dict(BASE, body=(0, -8), head=(6, -18), head_rot=5, head_sy=1.03, mouth=0.85, vein=1.35,
                    hand_l=(840, 240), hand_r=(1530, 250), bend_l=-20, bend_r=20, spread=1.25,
                    marks=((770, 150, -2.5), (1590, 160, -0.6))),
    "point": dict(BASE, body=(-20, -6), head=(-24, -10), head_rot=-8, mouth=0.9, vein=1.2, hand_l=(700, 520),
                  hand_r=(1420, 330), bend_l=-10, bend_r=40, mode_l="point", mode_r="fist"),
    "point2": dict(BASE, body=(-16, -4), head=(-20, -6), head_rot=-5, mouth=0.72, vein=1.35, hand_l=(690, 530),
                   hand_r=(1450, 300), bend_l=-14, bend_r=50, mode_l="point", mode_r="fist"),
}


def mix(a, b, u):
    """Intervalle entre deux poses (les choix discrets basculent à mi-chemin)."""
    out = {}
    for k in a:
        va, vb = a[k], b[k]
        if isinstance(va, (int, float)) and not isinstance(va, bool):
            out[k] = va + (vb - va) * u
        elif isinstance(va, tuple) and va and isinstance(va[0], (int, float)):
            out[k] = tuple(x + (y - x) * u for x, y in zip(va, vb))
        else:
            out[k] = vb if u >= 0.5 else va
    return out


def back(u, s=2.4):
    u -= 1
    return u * u * ((s + 1) * u + s) + 1


def ease(u):
    return u * u * (3 - 2 * u)


def pose_at(f):
    """Feuille d'exposition (images à 24 i/s)."""
    r = random.Random(f)
    if f < 10:
        return KEYS["calm"]
    if f < 16:
        return mix(KEYS["calm"], KEYS["hold"], ease((f - 10) / 6))
    if f < 24:
        p = dict(KEYS["hold"])
        p["body"] = (r.uniform(-3, 3), 22 + r.uniform(-2, 2))
        return p
    if f < 30:
        return mix(KEYS["hold"], KEYS["scream"], back((f - 24) / 6))
    if f < 62:
        base = KEYS["scream"] if (f // ON) % 2 == 0 else KEYS["scream2"]
        p = dict(base)
        p["body"] = (base["body"][0] + r.uniform(-7, 7), base["body"][1] + r.uniform(-5, 5))
        return p
    if f < 68:
        return mix(KEYS["scream"], KEYS["point"], back((f - 62) / 6, 1.6))
    base = KEYS["point"] if (f // (ON * 2)) % 2 == 0 else KEYS["point2"]
    p = dict(base)
    p["body"] = (base["body"][0] + r.uniform(-4, 4), base["body"][1] + r.uniform(-3, 3))
    return p


# ------------------------------------------------------------ un dessin toutes les 2 images
for f in range(1, FRAMES + 1, ON):
    CUR["frame"] = layer.frames.new(f)
    farmer(pose_at(f))

os.makedirs(OUTDIR, exist_ok=True)
sc.render.filepath = os.path.join(OUTDIR, "f_")
bpy.ops.render.render(animation=True)
if BLEND:
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
print("ANIM_OK", OUTDIR)
