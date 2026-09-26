"""Test de dessin Grease Pencil : le fermier qui hurle (plan 3).

Lancer :  xvfb-run -a blender -b --python gp_farmer.py -- <sortie.png> [<fichier.blend>]
Coordonnées en pixels du décor 1600×893 (x vers la droite, y vers le bas),
converties en unités Blender (100 px = 1 unité) ; caméra orthographique.
"""
import math
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "/tmp/gp_farmer.png"
BLEND = argv[1] if len(argv) > 1 else None

PW, PH = 1600, 893


def srgb(h):
    """Hex sRGB → linéaire (les couleurs GP sont en linéaire)."""
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
sc.eevee.taa_render_samples = 8
sc.render.resolution_x, sc.render.resolution_y = PW, PH
sc.render.film_transparent = True
sc.view_settings.view_transform = "Standard"
sc.render.image_settings.color_mode = "RGBA"

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
cam.data.type = "ORTHO"
cam.data.ortho_scale = PW / 100
cam.location = (0, -20, 0)
cam.rotation_euler = (math.pi / 2, 0, 0)
sc.camera = cam

gpd = bpy.data.grease_pencils.new("farmer")
gpd.stroke_depth_order = "2D"
gpd.pixel_factor = 10.0  # épaisseur des traits en pixels du décor
ob = bpy.data.objects.new("farmer", gpd)
sc.collection.objects.link(ob)

MATS = {}


def mat(name, stroke=None, fill=None):
    """Matériau GP : trait seul, remplissage seul, ou les deux."""
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


layer = gpd.layers.new("dessin")
layer.use_lights = False  # couleurs à plat, comme un dessin
frame = layer.frames.new(1)


def P(x, y):
    return ((x - PW / 2) / 100, 0, (PH / 2 - y) / 100)


def stroke(pts, material, width, cyclic=False, taper=True, wobble=0.0, seed=0):
    """Un trait. `taper` : fin aux deux bouts, plus épais au milieu (pinceau)."""
    s = frame.strokes.new()
    s.material_index = material
    s.line_width = int(width)
    s.use_cyclic = cyclic
    s.display_mode = "3DSPACE"
    n = len(pts)
    s.points.add(n)
    for i, (x, y) in enumerate(pts):
        u = i / max(1, n - 1)
        pr = 1.0
        if taper and not cyclic:
            pr = 0.25 + 0.75 * math.sin(math.pi * u) ** 0.6
        if wobble:
            pr *= 1 + wobble * math.sin(i * 1.7 + seed)
        s.points[i].co = P(x, y)
        s.points[i].pressure = pr
        s.points[i].strength = 1.0
    return s


def ellipse(cx, cy, rx, ry, n=64, rot=0.0):
    out = []
    for i in range(n):
        a = i / n * 2 * math.pi
        x, y = rx * math.cos(a), ry * math.sin(a)
        out.append((cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot)))
    return out


def smooth(pts, closed=True, steps=10):
    """Catmull-Rom : quelques points de contrôle → courbe souple."""
    out = []
    n = len(pts)
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0, p1 = pts[(i - 1) % n], pts[i]
        p2, p3 = pts[(i + 1) % n], pts[(i + 2) % n]
        if not closed:
            p0 = pts[max(0, i - 1)]
            p3 = pts[min(n - 1, i + 2)]
        for k in range(steps):
            t = k / steps
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    if not closed:
        out.append(pts[-1])
    return out


INK = mat("ink", stroke="1B1724")
STICKER = mat("sticker", stroke="FFFFFF")
F_WHITE = mat("f_white", fill="FFFFFF")
F_SHIRT = mat("f_shirt", fill="E9D6B4")
F_DENIM = mat("f_denim", fill="5E82AE")
F_MOUTH = mat("f_mouth", fill="6E1220")
F_TONGUE = mat("f_tongue", fill="E9667A")
F_GOLD = mat("f_gold", fill="E0B24A")
F_SHADE = mat("f_shade", fill="C9C3D6")
F_SHIRT_SH = mat("f_shirt_sh", fill="C9AE86")
F_DENIM_SH = mat("f_denim_sh", fill="45679A")
VEIN = mat("vein", stroke="D62434")


def shape(pts, fill, outline=9, sticker=0, shade=None):
    """Forme remplie + contour encré (+ liseré blanc extérieur)."""
    if sticker:
        stroke(pts, STICKER, outline + sticker, cyclic=True, taper=False)
    stroke(pts, fill, 1, cyclic=True, taper=False)
    if shade:
        stroke(shade[0], shade[1], 1, cyclic=True, taper=False)
    stroke(pts, INK, outline, cyclic=True, taper=False, wobble=0.18, seed=len(pts))


# ------------------------------------------------------------ le fermier
HX, HY = 1180, 905          # hanches
HEAD = (1185, 350)          # centre de la tête


def arm(sx, sy, ex, ey, hx, hy, side):
    # manche : un trait très épais encré, puis la couleur par-dessus
    path = smooth([(sx, sy), (ex, ey), (hx, hy)], closed=False, steps=8)
    stroke(path, STICKER, 118, taper=False)
    stroke(path, INK, 96, taper=False)
    stroke(path, mat("sleeve", stroke="E9D6B4"), 80, taper=False)


def glove(cx, cy, angle, spread=1.0, s=1.3):
    """Main-gant à quatre doigts : chaque doigt est un trait épais encré, puis la paume."""
    ca, sa = math.cos(angle), math.sin(angle)

    def R(x, y):
        return (cx + (x * ca - y * sa) * s, cy + (x * sa + y * ca) * s)
    fingers = [(-0.62, 60), (-0.2, 70), (0.2, 68), (0.6, 58)]
    tips = []
    for (a, L) in fingers:
        a *= spread
        tips.append(([R(0, -8), R(math.sin(a) * L, -8 - math.cos(a) * L)]))
    thumb = [R(-6, 12), R(-60, -4)]
    for seg in tips + [thumb]:
        stroke(seg, STICKER, 58 / 10 * 10 * s, taper=False)
    for seg in tips + [thumb]:
        stroke(seg, INK, 40 * s, taper=False)
    for seg in tips + [thumb]:
        stroke(seg, mat("glove", stroke="FFFFFF"), 26 * s, taper=False)
    palm = ellipse(*R(0, 10), 42 * s, 38 * s, 40, angle)
    stroke(palm, STICKER, 26, cyclic=True, taper=False)
    shape(palm, F_WHITE, 8)
    # repasser le blanc sur les jonctions doigts / paume
    for seg in tips + [thumb]:
        (x0, y0), (x1, y1) = seg
        stroke([(x0, y0), (x0 + (x1 - x0) * 0.5, y0 + (y1 - y0) * 0.5)], mat("glove", stroke="FFFFFF"), 24 * s, taper=False)
    for (a, _) in fingers[1:]:
        a *= spread
        stroke([R(math.sin(a - 0.3) * 32, -8 - math.cos(a - 0.3) * 32),
                R(math.sin(a - 0.3) * 20, -8 - math.cos(a - 0.3) * 20)], INK, 5)


# bras levés
arm(1030, 635, 900, 470, 860, 300, -1)
arm(1330, 635, 1450, 470, 1500, 300, 1)
glove(860, 250, -0.35)
glove(1500, 250, 0.35)

# torse : chemise + salopette
shirt = smooth([(1030, 600), (1120, 570), (1240, 570), (1330, 600), (1362, 705), (1340, 985), (1020, 985), (998, 705)])
shirt_sh = smooth([(1260, 600), (1330, 610), (1360, 705), (1340, 985), (1250, 985), (1275, 800)])
shape(shirt, F_SHIRT, 9, sticker=18, shade=(shirt_sh, F_SHIRT_SH))
for sgn in (-1, 1):
    shape([(1180, 575), (1180 + sgn * 70, 570), (1180 + sgn * 45, 625)], F_SHIRT, 7)
for sgn in (-1, 1):
    stroke([(1180 + sgn * 88, 740), (1180 + sgn * 125, 593)], INK, 44, taper=False)
    stroke([(1180 + sgn * 88, 740), (1180 + sgn * 125, 593)], mat("strap", stroke="5E82AE"), 30, taper=False)
bib = [(1080, 730), (1280, 730), (1298, 985), (1062, 985)]
bib_sh = [(1220, 730), (1280, 730), (1298, 985), (1240, 985)]
shape(bib, F_DENIM, 9, shade=(bib_sh, F_DENIM_SH))
shape([(1125, 785), (1235, 785), (1235, 863), (1125, 863)], F_DENIM, 6)
for sgn in (-1, 1):
    shape(ellipse(1180 + sgn * 82, 745, 13, 13, 20), F_GOLD, 5)

# tête
hx, hy = HEAD
head = ellipse(hx, hy, 192, 186, 72)
# ombre en croissant sur le bord bas-droit de la tête
arc = [i / 40 for i in range(41)]
outer = [(hx + 192 * math.cos(-0.5 + 2.6 * u), hy + 186 * math.sin(-0.5 + 2.6 * u)) for u in arc]
inner = [(hx - 34 + 190 * math.cos(-0.5 + 2.6 * u), hy - 34 + 184 * math.sin(-0.5 + 2.6 * u)) for u in reversed(arc)]
head_sh = outer + inner
shape(head, F_WHITE, 11, sticker=20, shade=(head_sh, F_SHADE))

# sourcils, yeux plissés, rides
for sgn in (-1, 1):
    stroke(smooth([(hx + sgn * 150, hy - 92), (hx + sgn * 100, hy - 74), (hx + sgn * 40, hy - 52)], False, 8), INK, 22)
    stroke([(hx + sgn * 125, hy - 45), (hx + sgn * 62, hy - 22), (hx + sgn * 122, hy - 2)], INK, 12, taper=False)
    stroke([(hx + sgn * 150, hy - 30), (hx + sgn * 172, hy - 17)], INK, 6)
    stroke([(hx + sgn * 18, hy - 40), (hx + sgn * 10, hy - 10)], INK, 6)

# bouche hurlante : fond, langue, dents, contour
mw, mh = 110, 180
mouth = smooth([(hx - mw * 0.8, hy + 30), (hx - mw * 0.45, hy + 4), (hx, hy - 2), (hx + mw * 0.45, hy + 4), (hx + mw * 0.8, hy + 30),
                (hx + mw, hy + 18 + mh * 0.75), (hx + mw * 0.55, hy + 18 + mh), (hx - mw * 0.55, hy + 18 + mh),
                (hx - mw, hy + 18 + mh * 0.75)], True, 8)
stroke(mouth, F_MOUTH, 1, cyclic=True, taper=False)
stroke(smooth([(hx - 62, hy + 160), (hx, hy + 128), (hx + 62, hy + 160), (hx + 50, hy + 190), (hx - 50, hy + 190)], True, 6),
       F_TONGUE, 1, cyclic=True, taper=False)
stroke(smooth([(hx - 78, hy + 20), (hx - 40, hy + 6), (hx, hy + 2), (hx + 40, hy + 6), (hx + 78, hy + 20), (hx + 60, hy + 38),
               (hx, hy + 32), (hx - 60, hy + 38)], True, 5), F_WHITE, 1, cyclic=True, taper=False)
stroke(smooth([(hx - 70, hy + 34), (hx, hy + 28), (hx + 70, hy + 34)], False, 6), INK, 5)
stroke(mouth, INK, 12, cyclic=True, taper=False, wobble=0.2, seed=3)

# veine de colère
vx, vy = hx + 118, hy - 118
for q in range(4):
    a = q * math.pi / 2 + math.pi / 4
    pts = []
    for k in range(9):
        u = k / 8
        lx, ly = -16 + 32 * u, -28 + 14 * math.sin(math.pi * u)
        pts.append((vx + lx * math.cos(a) - ly * math.sin(a), vy + lx * math.sin(a) + ly * math.cos(a)))
    stroke(pts, VEIN, 12)

# traits de mouvement autour des mains
for (cx, cy, base) in ((790, 190, -2.4), (1570, 190, -0.7)):
    for k in range(3):
        a = base + (k - 1) * 0.45
        stroke([(cx + math.cos(a) * 80, cy + math.sin(a) * 80), (cx + math.cos(a) * 140, cy + math.sin(a) * 140)], INK, 10)

sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
if BLEND:
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
print("RENDER_OK", OUT)
