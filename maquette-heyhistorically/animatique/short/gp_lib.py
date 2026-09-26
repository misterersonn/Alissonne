"""Bibliothèque de dessin Grease Pencil pour le short vertical (720×1280).

Personnages « chibi » dans l'esprit de la chaîne : grosse tête blanche ovale,
petit corps, ombre grise à plat, trait moyen. Coordonnées en pixels du cadre
(x vers la droite, y vers le bas).
"""
import math
import os
import random

import bpy

W, H = 720, 1280


def srgb(h):
    h = h.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


class Canvas:
    """Scène Blender + un objet Grease Pencil, un calque, des matériaux par couleur."""

    def __init__(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = self.sc = bpy.context.scene
        sc.render.engine = "BLENDER_EEVEE_NEXT"
        sc.eevee.taa_render_samples = 4
        sc.render.resolution_x, sc.render.resolution_y = W, H
        sc.render.film_transparent = True
        sc.view_settings.view_transform = "Standard"
        sc.render.image_settings.file_format = "PNG"
        sc.render.image_settings.color_mode = "RGBA"
        sc.render.fps = 24
        cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
        sc.collection.objects.link(cam)
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = H / 100
        cam.location = (0, -20, 0)
        cam.rotation_euler = (math.pi / 2, 0, 0)
        sc.camera = cam
        self.gpd = bpy.data.grease_pencils.new("gp")
        self.gpd.stroke_depth_order = "2D"
        self.gpd.pixel_factor = 10.0
        ob = bpy.data.objects.new("gp", self.gpd)
        sc.collection.objects.link(ob)
        self.layer = self.gpd.layers.new("dessin")
        self.layer.use_lights = False
        self.mats = {}
        self.frame = None
        self.seed = 0

    # ---------------------------------------------------------- matériaux
    def stroke_mat(self, hexcol):
        key = "s" + hexcol
        if key not in self.mats:
            m = bpy.data.materials.new(key)
            bpy.data.materials.create_gpencil_data(m)
            m.grease_pencil.show_stroke = True
            m.grease_pencil.show_fill = False
            m.grease_pencil.color = srgb(hexcol)
            self.gpd.materials.append(m)
            self.mats[key] = len(self.gpd.materials) - 1
        return self.mats[key]

    def fill_mat(self, hexcol):
        key = "f" + hexcol
        if key not in self.mats:
            m = bpy.data.materials.new(key)
            bpy.data.materials.create_gpencil_data(m)
            m.grease_pencil.show_stroke = False
            m.grease_pencil.show_fill = True
            m.grease_pencil.fill_color = srgb(hexcol)
            self.gpd.materials.append(m)
            self.mats[key] = len(self.gpd.materials) - 1
        return self.mats[key]

    # ---------------------------------------------------------- dessin
    def new_drawing(self, frame):
        self.frame = self.layer.frames.new(frame)
        self.seed = frame * 1000

    def clear(self):
        for f in list(self.layer.frames):
            self.layer.frames.remove(f)

    def line(self, pts, color="1B1724", width=6, taper=True, cyclic=False, jitter=0.8):
        s = self.frame.strokes.new()
        s.material_index = self.stroke_mat(color)
        s.line_width = int(max(1, width))
        s.use_cyclic = cyclic
        s.display_mode = "3DSPACE"
        n = len(pts)
        s.points.add(n)
        self.seed += 1
        r = random.Random(self.seed)
        for i, (x, y) in enumerate(pts):
            u = i / max(1, n - 1)
            pr = 0.3 + 0.7 * math.sin(math.pi * u) ** 0.5 if (taper and not cyclic) else 1.0
            s.points[i].co = ((x + r.uniform(-jitter, jitter) - W / 2) / 100, 0,
                              (H / 2 - y - r.uniform(-jitter, jitter)) / 100)
            s.points[i].pressure = pr
            s.points[i].strength = 1.0

    def fill(self, pts, color):
        s = self.frame.strokes.new()
        s.material_index = self.fill_mat(color)
        s.line_width = 1
        s.use_cyclic = True
        s.display_mode = "3DSPACE"
        s.points.add(len(pts))
        for i, (x, y) in enumerate(pts):
            s.points[i].co = ((x - W / 2) / 100, 0, (H / 2 - y) / 100)

    def shape(self, pts, color, lw=6, sticker=0):
        if sticker:
            self.line(pts, "FFFFFF", lw + sticker, taper=False, cyclic=True, jitter=0)
        self.fill(pts, color)
        self.line(pts, "1B1724", lw, taper=False, cyclic=True)

    def render(self, outdir, f0, f1):
        os.makedirs(outdir, exist_ok=True)
        self.sc.frame_start, self.sc.frame_end = f0, f1
        self.sc.render.filepath = os.path.join(outdir, "f_")
        bpy.ops.render.render(animation=True)


# ------------------------------------------------------------ géométrie
def ellipse(cx, cy, rx, ry, n=48, rot=0.0, a0=0.0, a1=2 * math.pi):
    out = []
    closed = abs(a1 - a0 - 2 * math.pi) < 1e-6
    m = n if closed else n + 1
    for i in range(m):
        a = a0 + (a1 - a0) * i / n
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


def xf(pts, cx, cy, s=1.0, rot=0.0, flip=False):
    """Place des points définis autour de (0,0) : échelle, rotation, miroir, position."""
    ca, sa = math.cos(rot), math.sin(rot)
    out = []
    for x, y in pts:
        if flip:
            x = -x
        x, y = x * s, y * s
        out.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    return out


INK = "1B1724"
SHADE = "CFC9DA"


# ------------------------------------------------------------ tête
def head(cv, cx, cy, r=110, rot=0.0, eyes="dot", mouth="flat", look=(0, 0), mustache=False, sweat=False, blush=False,
         sticker=14, flip=False):
    """Tête blanche ovale vue de 3/4 : les traits du visage sont décalés vers la droite."""
    T = lambda pts: xf(pts, cx, cy, 1.0, rot, flip)  # noqa: E731
    outline = T(ellipse(0, 0, r * 0.94, r, 56))
    cv.shape(outline, "FFFFFF", 7, sticker)
    # ombre grise à plat, côté gauche-bas
    cv.line(T(ellipse(0, 0, r * 0.84, r * 0.9, 30, 0, 1.9, 3.9)), SHADE, r * 0.2, taper=True)
    cv.line(outline, INK, 7, taper=False, cyclic=True)
    ex = r * 0.18  # visage tourné de 3/4
    lx, ly = look
    if eyes == "dot":
        for dx in (-r * 0.28, r * 0.36):
            cv.shape(T(ellipse(ex + dx + lx * 6, -r * 0.08 + ly * 6, r * 0.07, r * 0.12, 16)), INK, 2)
    elif eyes == "wide":
        for dx in (-r * 0.28, r * 0.36):
            cv.shape(T(ellipse(ex + dx, -r * 0.1, r * 0.17, r * 0.2, 20)), "FFFFFF", 5)
            cv.shape(T(ellipse(ex + dx + lx * r * 0.07, -r * 0.08 + ly * r * 0.07, r * 0.07, r * 0.09, 14)), INK, 2)
    elif eyes == "closed":
        for dx in (-r * 0.28, r * 0.36):
            cv.line(T(ellipse(ex + dx, -r * 0.12, r * 0.12, r * 0.08, 10, 0, 0.2, math.pi - 0.2)), INK, 6)
    elif eyes == "angry":
        for dx, sg in ((-r * 0.28, -1), (r * 0.36, 1)):
            cv.line(T([(ex + dx - sg * r * 0.12, -r * 0.18), (ex + dx + sg * r * 0.02, -r * 0.1),
                       (ex + dx - sg * r * 0.12, -r * 0.02)]), INK, 7, taper=False)
            cv.line(T([(ex + dx - sg * r * 0.2, -r * 0.34), (ex + dx + sg * r * 0.08, -r * 0.24)]), INK, 9)
    elif eyes == "sad":
        for dx, sg in ((-r * 0.28, -1), (r * 0.36, 1)):
            cv.shape(T(ellipse(ex + dx, -r * 0.08, r * 0.07, r * 0.11, 14)), INK, 2)
            cv.line(T([(ex + dx - sg * r * 0.14, -r * 0.3), (ex + dx + sg * r * 0.06, -r * 0.36)]), INK, 6)
    if blush:
        for dx in (-r * 0.36, r * 0.5):
            cv.fill(T(ellipse(ex + dx, r * 0.14, r * 0.13, r * 0.07, 16)), "F2A0AA")
    my = r * 0.36
    if mustache:
        for sg in (-1, 1):
            cv.shape(T(smooth([(ex + r * 0.05, my - r * 0.18), (ex + r * 0.05 + sg * r * 0.3, my - r * 0.22),
                               (ex + r * 0.05 + sg * r * 0.42, my - r * 0.1), (ex + r * 0.05 + sg * r * 0.2, my - r * 0.08)],
                              True, 5)), "7A4E2C", 5)
    if mouth == "flat":
        cv.line(T([(ex - r * 0.1, my), (ex + r * 0.18, my - r * 0.02)]), INK, 6)
    elif mouth == "smile":
        cv.line(T(ellipse(ex + r * 0.04, my - r * 0.1, r * 0.2, r * 0.12, 12, 0, 0.3, math.pi - 0.3)), INK, 6)
    elif mouth == "frown":
        cv.line(T(ellipse(ex + r * 0.04, my + r * 0.06, r * 0.16, r * 0.1, 12, 0, math.pi + 0.4, 2 * math.pi - 0.4)), INK, 6)
    elif mouth == "wobble":
        pts = [(ex - r * 0.2 + k * r * 0.08, my + (r * 0.03 if k % 2 else -r * 0.03)) for k in range(6)]
        cv.line(T(pts), INK, 5, taper=False)
    elif mouth in ("open", "scream"):
        big = 1.0 if mouth == "open" else 1.6
        mo = T(smooth([(ex - r * 0.16 * big, my - r * 0.05), (ex + r * 0.04, my - r * 0.1), (ex + r * 0.22 * big, my - r * 0.05),
                       (ex + r * 0.12 * big, my + r * 0.2 * big), (ex - r * 0.08 * big, my + r * 0.2 * big)], True, 6))
        cv.fill(mo, "6E1220")
        cv.fill(T(ellipse(ex + r * 0.03, my + r * 0.12 * big, r * 0.1 * big, r * 0.06 * big, 14)), "E9667A")
        cv.line(mo, INK, 6, taper=False, cyclic=True)
    elif mouth == "o":
        cv.shape(T(ellipse(ex + r * 0.04, my, r * 0.08, r * 0.1, 14)), "6E1220", 5)
    if sweat:
        d = T(smooth([(r * 0.8, -r * 0.62), (r * 0.9, -r * 0.4), (r * 0.8, -r * 0.3), (r * 0.7, -r * 0.4)], True, 5))
        cv.shape(d, "9ED8F0", 4)


# ------------------------------------------------------------ chapeaux
def slouch_hat(cv, cx, cy, r=110, rot=0.0, flip=False):
    """Chapeau australien à bord relevé sur un côté."""
    T = lambda pts: xf(pts, cx, cy, 1.0, rot, flip)  # noqa: E731
    brim = T(smooth([(-r * 1.25, -r * 0.55), (-r * 0.2, -r * 0.72), (r * 0.9, -r * 0.62), (r * 1.2, -r * 0.5),
                     (r * 0.4, -r * 0.4), (-r * 0.9, -r * 0.4)], True, 6))
    cv.shape(brim, "8A7A48", 7, 10)
    crown = T(smooth([(-r * 0.75, -r * 0.55), (-r * 0.6, -r * 1.05), (0, -r * 1.2), (r * 0.6, -r * 1.05), (r * 0.72, -r * 0.55)],
                     True, 6))
    cv.shape(crown, "9C8B55", 7, 10)
    cv.fill(T([(-r * 0.74, -r * 0.62), (r * 0.72, -r * 0.62), (r * 0.7, -r * 0.74), (-r * 0.72, -r * 0.74)]), "5E4A2C")
    # bord relevé côté gauche avec l'insigne
    up = T(smooth([(-r * 1.05, -r * 0.55), (-r * 0.95, -r * 1.05), (-r * 0.7, -r * 1.0), (-r * 0.72, -r * 0.6)], True, 5))
    cv.shape(up, "7C6C3E", 6)
    cv.shape(T(ellipse(-r * 0.86, -r * 0.8, r * 0.07, r * 0.07, 12)), "E0B24A", 3)


def peaked_cap(cv, cx, cy, r=110, rot=0.0, flip=False):
    T = lambda pts: xf(pts, cx, cy, 1.0, rot, flip)  # noqa: E731
    top = T(smooth([(-r * 0.95, -r * 0.62), (-r * 0.8, -r * 1.02), (r * 0.1, -r * 1.12), (r * 1.0, -r * 0.95), (r * 0.95, -r * 0.62)],
                   True, 6))
    cv.shape(top, "6E6A3E", 7, 10)
    cv.fill(T([(-r * 0.94, -r * 0.6), (r * 0.94, -r * 0.6), (r * 0.94, -r * 0.72), (-r * 0.94, -r * 0.72)]), "8A2A2A")
    visor = T(smooth([(-r * 0.3, -r * 0.58), (r * 0.95, -r * 0.6), (r * 1.1, -r * 0.46), (r * 0.2, -r * 0.44)], True, 5))
    cv.shape(visor, "2A2420", 6)
    cv.shape(T(ellipse(r * 0.2, -r * 0.84, r * 0.09, r * 0.08, 12)), "E0B24A", 3)


# ------------------------------------------------------------ corps
def glove(cv, cx, cy, s=1.0, rot=0.0, mode="open"):
    T = lambda pts: xf(pts, cx, cy, s, rot)  # noqa: E731
    if mode == "open":
        segs = [[(0, -6), (math.sin(a) * L, -6 - math.cos(a) * L)] for a, L in ((-0.6, 34), (-0.2, 40), (0.2, 38), (0.6, 32))]
        segs.append([(-4, 6), (-34, -2)])
        for sg in segs:
            cv.line(T(sg), "FFFFFF", 36 * s, taper=False, jitter=0)
        for sg in segs:
            cv.line(T(sg), INK, 24 * s, taper=False, jitter=0)
        for sg in segs:
            cv.line(T(sg), "FFFFFF", 14 * s, taper=False, jitter=0)
    body = T(smooth([(-24, -16), (0, -26), (24, -16), (28, 12), (10, 26), (-18, 24), (-30, 6)], True, 5))
    cv.shape(body, "FFFFFF", 5, 8)
    if mode == "fist":
        for k in range(3):
            cv.line(T([(-14 + k * 12, -20), (-12 + k * 12, -2)]), INK, 4)
    if mode == "open":
        for sg in segs:
            cv.line(T([sg[0], ((sg[0][0] + sg[1][0]) / 2, (sg[0][1] + sg[1][1]) / 2)]), "FFFFFF", 13 * s, taper=False, jitter=0)


def limb(cv, pts, color, width):
    cv.line(pts, "FFFFFF", width + 14, taper=False, jitter=0)
    cv.line(pts, INK, width + 8, taper=False)
    cv.line(pts, color, width, taper=False, jitter=0)


def soldier(cv, cx, cy, s=1.0, head_rot=0.0, eyes="dot", mouth="flat", hand_l=None, hand_r=None, look=(0, 0),
            sweat=False, blush=False, hat="slouch", mustache=False, body_col="A08A58", bob=0.0, gl_l="open", gl_r="open"):
    """Soldat chibi. (cx, cy) = centre de la tête ; le corps fait ~1,1 tête de haut."""
    r = 110 * s
    by = cy + r * 0.95 + bob
    # bras (derrière le torse)
    sh_l, sh_r = (cx - r * 0.55, by + r * 0.25), (cx + r * 0.55, by + r * 0.25)
    hl = hand_l or (cx - r * 0.75, by + r * 0.95)
    hr = hand_r or (cx + r * 0.75, by + r * 0.95)
    # torse en veste
    torso = smooth([(cx - r * 0.62, by + r * 0.1), (cx, by - r * 0.02), (cx + r * 0.62, by + r * 0.1), (cx + r * 0.72, by + r * 1.2),
                    (cx - r * 0.72, by + r * 1.2)], True, 6)
    cv.shape(torso, body_col, 6, 12)
    cv.fill(smooth([(cx - r * 0.62, by + r * 0.3), (cx - r * 0.2, by + r * 0.2), (cx - r * 0.3, by + r * 1.2), (cx - r * 0.72, by + r * 1.2)],
                   True, 4), "7E6A40")
    cv.line(torso, INK, 6, taper=False, cyclic=True)
    cv.line([(cx - r * 0.7, by + r * 0.85), (cx + r * 0.7, by + r * 0.85)], "5A3E24", 14 * s, taper=False, jitter=0)
    for k in range(3):
        cv.shape(ellipse(cx + r * 0.05, by + r * (0.3 + k * 0.22), r * 0.04, r * 0.04, 10), "E0B24A", 2)
    for sh, hd in ((sh_l, hl), (sh_r, hr)):
        mx, my = (sh[0] + hd[0]) / 2, (sh[1] + hd[1]) / 2 + r * 0.08
        limb(cv, smooth([sh, (mx, my), hd], False, 6), body_col, 34 * s)
    glove(cv, *hl, s * 1.05, 0, gl_l)
    glove(cv, *hr, s * 1.05, 0, gl_r)
    head(cv, cx, cy + bob, r, head_rot, eyes, mouth, look, mustache, sweat, blush)
    if hat == "slouch":
        slouch_hat(cv, cx, cy + bob, r, head_rot)
    elif hat == "cap":
        peaked_cap(cv, cx, cy + bob, r, head_rot)


def emu(cv, cx, cy, s=1.0, phase=None, eyes="wide", look=(1, 0), beak_open=False, crown=False, flip=False, bob=0.0):
    """Émeu : (cx, cy) = centre du corps. `phase` 0-3 = cycle de course, None = debout."""
    T = lambda pts: xf(pts, cx, cy + bob, s, 0, flip)  # noqa: E731
    # pattes
    if phase is None:
        legs = [[(-30, 60), (-45, 150), (-35, 240)], [(30, 60), (45, 150), (40, 240)]]
    else:
        a = phase * math.pi / 2
        legs = []
        for off in (0, math.pi):
            k = math.sin(a + off)
            c = math.cos(a + off)
            legs.append([(0, 60), (40 * k, 150 - 20 * max(0, c)), (90 * k, 230 - 60 * max(0, c))])
    for lg in legs:
        cv.line(T(lg), "FFFFFF", 30 * s, taper=False, jitter=0)
        cv.line(T(lg), INK, 22 * s, taper=False)
        cv.line(T(lg), "8C919C", 12 * s, taper=False, jitter=0)
        fx, fy = lg[-1]
        for ta in (-0.5, 0.0, 0.5):
            cv.line(T([(fx, fy), (fx + 30 * math.sin(ta + 1.3), fy + 6 * math.cos(ta))]), INK, 8 * s)
    # corps en plumes
    pts = []
    for i in range(26):
        a = i / 26 * 2 * math.pi
        rnd = (math.sin(i * 12.9898) * 43758.5453) % 1.0
        shag = 1 + 0.9 * max(0, math.sin(a)) ** 2
        rr = 1 + (0.09 * shag * (0.5 + rnd) if i % 2 else -0.02)
        tail = 0.3 * max(0, -math.cos(a)) ** 3
        pts.append((140 * (rr + tail) * math.cos(a), 100 * rr * math.sin(a) - tail * 30))
    body = T(smooth(pts, True, 3))
    cv.shape(body, "7C6450", 7, 12)
    for (fx, fy, L) in ((-70, -30, 40), (-20, 10, 46), (30, -20, 40), (-90, 20, 36), (60, 20, 34), (0, -50, 30)):
        cv.line(T([(fx, fy), (fx + L * 0.4, fy + L * 0.5), (fx + L * 0.3, fy + L)]), "4E3C2E", 5 * s)
    # cou
    neck = T(smooth([(90, -40), (130, -120), (125, -210)], False, 6))
    cv.line(neck, "FFFFFF", 56 * s, taper=False, jitter=0)
    cv.line(neck, INK, 46 * s, taper=False)
    cv.line(neck, "B8C3D2", 34 * s, taper=False, jitter=0)
    # tête
    hx, hy = 125, -240
    cv.shape(T(ellipse(hx, hy, 46, 44, 30)), "FFFFFF", 6, 10)
    beak_top = T(smooth([(hx + 30, hy - 8), (hx + 100, hy + 6), (hx + 98, hy + 14), (hx + 34, hy + 12)], True, 4))
    cv.shape(beak_top, "9EA3AC", 5)
    if beak_open:
        cv.shape(T(smooth([(hx + 32, hy + 16), (hx + 90, hy + 34), (hx + 86, hy + 42), (hx + 30, hy + 28)], True, 4)), "7F848E", 5)
    for ex, rr in ((hx - 4, 17), (hx + 26, 15)):
        if eyes == "wide":
            cv.shape(T(ellipse(ex, hy - 12, rr, rr * 1.1, 14)), "FFFFFF", 4)
            cv.shape(T(ellipse(ex + look[0] * rr * 0.45, hy - 10 + look[1] * rr * 0.4, rr * 0.45, rr * 0.5, 10)), INK, 1)
        elif eyes == "angry":
            cv.shape(T(ellipse(ex, hy - 10, rr * 0.5, rr * 0.55, 10)), INK, 1)
            cv.line(T([(ex - rr, hy - 30), (ex + rr, hy - 20)]), INK, 6)
        elif eyes == "closed":
            cv.line(T(ellipse(ex, hy - 10, rr * 0.8, rr * 0.5, 8, 0, 0.3, math.pi - 0.3)), INK, 5)
    for k, a in enumerate((-0.4, 0.0, 0.4)):
        cv.line(T([(hx - 10 + k * 10, hy - 42), (hx - 10 + k * 10 + 14 * math.sin(a), hy - 60)]), INK, 5)
    if crown:
        cr = T([(hx - 30, hy - 40), (hx - 34, hy - 86), (hx - 12, hy - 60), (hx + 6, hy - 96), (hx + 22, hy - 60),
                (hx + 42, hy - 86), (hx + 36, hy - 40)])
        cv.shape(cr, "F2C75A", 5, 8)


def lewis_gun(cv, cx, cy, s=1.0, rot=0.0):
    T = lambda pts: xf(pts, cx, cy, s, rot)  # noqa: E731
    cv.shape(T([(-150, -16), (180, -16), (180, 16), (-150, 16)]), "4A4A50", 6, 10)
    for k in range(8):
        cv.line(T([(-60 + k * 26, -16), (-60 + k * 26, 16)]), "2A2A30", 5, taper=False)
    cv.shape(T([(180, -8), (260, -8), (260, 8), (180, 8)]), "3A3A40", 5)
    cv.shape(T(ellipse(-40, -44, 70, 16, 24)), "5A5A62", 6)
    cv.shape(T([(-150, -10), (-250, 10), (-250, 44), (-150, 20)]), "7A5236", 6)
    for lx in (-30, 50):
        cv.line(T([(0, 16), (lx, 120)]), INK, 12, taper=False)


def muzzle(cv, cx, cy, s=1.0, seed=0):
    r = random.Random(seed)
    pts = []
    for i in range(18):
        a = i / 18 * 2 * math.pi
        rr = (r.uniform(0.9, 1.3) if i % 2 == 0 else r.uniform(0.35, 0.5)) * 70 * s
        pts.append((cx + rr * math.cos(a) * 1.3, cy + rr * math.sin(a)))
    cv.shape(pts, "FFCE54", 6)
    cv.fill([(cx + (x - cx) * 0.5, cy + (y - cy) * 0.5) for x, y in pts], "FFFBE0")
