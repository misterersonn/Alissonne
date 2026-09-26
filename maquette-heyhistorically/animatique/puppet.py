"""Animation « découpage » sur une image peinte.

Chaque personnage est animé par des déformateurs locaux (rotation autour d'une
articulation, translation, étirement) appliqués dans une zone elliptique avec un
bord adouci : c'est l'équivalent d'un rig cut-out, sans avoir à détourer les
pièces. Les poses sont tenues deux images (12 i/s) comme en animation dessinée,
et un léger « line boil » fait vibrer le trait comme un dessin refait à la main.
Les effets (larmes, sueur, poussière, plumes, flashs…) sont dessinés image par
image avec un trait encré irrégulier.
"""
import math
import random

import cv2
import numpy as np
from PIL import Image, ImageDraw

INK = (27, 23, 36)
DRAW_FPS = 12  # cadence des poses : « on twos » à 24 i/s


def on_twos(t):
    return math.floor(t * DRAW_FPS) / DRAW_FPS


def tick(t):
    return int(math.floor(t * DRAW_FPS))


# ------------------------------------------------------------ déformateurs
class Deformer:
    """Zone elliptique (cx, cy, rx, ry) ; `inner` = part pleinement rigide."""

    def __init__(self, cx, cy, rx, ry=None, inner=0.55):
        self.cx, self.cy = cx, cy
        self.rx, self.ry = rx, ry or rx
        self.inner = inner

    def weight(self, xs, ys):
        d = np.sqrt(((xs - self.cx) / self.rx) ** 2 + ((ys - self.cy) / self.ry) ** 2)
        k = np.clip((1 - d) / (1 - self.inner), 0, 1)
        return k * k * (3 - 2 * k)

    def bbox(self, w, h):
        x0 = max(0, int(self.cx - self.rx) - 2)
        x1 = min(w, int(self.cx + self.rx) + 2)
        y0 = max(0, int(self.cy - self.ry) - 2)
        y1 = min(h, int(self.cy + self.ry) + 2)
        return x0, x1, y0, y1


class Rot(Deformer):
    """Rotation de `angle(t)` degrés autour de l'articulation (px, py)."""

    def __init__(self, cx, cy, rx, ry, pivot, angle, **kw):
        super().__init__(cx, cy, rx, ry, **kw)
        self.px, self.py = pivot
        self.angle = angle

    def offset(self, xs, ys, t):
        w = self.weight(xs, ys)
        a = -math.radians(self.angle(t)) * w
        c, s = np.cos(a), np.sin(a)
        dx, dy = xs - self.px, ys - self.py
        return (self.px + c * dx - s * dy) - xs, (self.py + s * dx + c * dy) - ys


class Move(Deformer):
    """Translation (dx(t), dy(t)) en pixels source."""

    def __init__(self, cx, cy, rx, ry, dxy, **kw):
        super().__init__(cx, cy, rx, ry, **kw)
        self.dxy = dxy

    def offset(self, xs, ys, t):
        w = self.weight(xs, ys)
        dx, dy = self.dxy(t)
        return -w * dx, -w * dy


class Squash(Deformer):
    """Étirement (sx(t), sy(t)) autour de l'ancre (ax, ay) : respiration, sanglots."""

    def __init__(self, cx, cy, rx, ry, anchor, sxy, **kw):
        super().__init__(cx, cy, rx, ry, **kw)
        self.ax, self.ay = anchor
        self.sxy = sxy

    def offset(self, xs, ys, t):
        w = self.weight(xs, ys)
        sx, sy = self.sxy(t)
        sx = 1 + (sx - 1) * w
        sy = 1 + (sy - 1) * w
        return (self.ax + (xs - self.ax) / sx) - xs, (self.ay + (ys - self.ay) / sy) - ys


class Rig:
    def __init__(self, image, deformers, hold=True):
        self.src = np.asarray(image.convert("RGB"))
        self.h, self.w = self.src.shape[:2]
        self.deformers = deformers
        self.hold = hold
        gx, gy = np.meshgrid(np.arange(self.w, dtype=np.float32), np.arange(self.h, dtype=np.float32))
        self.gx, self.gy = gx, gy
        self._cache = (None, None)

    def pose(self, t):
        tq = on_twos(t) if self.hold else t
        if self._cache[0] == tq:
            return self._cache[1]
        mx, my = self.gx.copy(), self.gy.copy()
        for d in self.deformers:
            x0, x1, y0, y1 = d.bbox(self.w, self.h)
            xs, ys = self.gx[y0:y1, x0:x1], self.gy[y0:y1, x0:x1]
            ox, oy = d.offset(xs, ys, tq)
            mx[y0:y1, x0:x1] += ox.astype(np.float32)
            my[y0:y1, x0:x1] += oy.astype(np.float32)
        out = cv2.remap(self.src, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        img = Image.fromarray(out)
        self._cache = (tq, img)
        return img


# ------------------------------------------------------------ line boil
class Boil:
    """Trois variantes de bruit de déplacement, alternées à 12 i/s."""

    def __init__(self, w, h, amp=1.3, seed=3):
        rng = np.random.default_rng(seed)
        gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
        self.maps = []
        for _ in range(3):
            small = rng.uniform(-1, 1, (2, h // 18 + 2, w // 18 + 2)).astype(np.float32)
            dx = cv2.resize(small[0], (w, h), interpolation=cv2.INTER_CUBIC) * amp
            dy = cv2.resize(small[1], (w, h), interpolation=cv2.INTER_CUBIC) * amp
            self.maps.append((gx + dx, gy + dy))

    def __call__(self, frame, t):
        mx, my = self.maps[tick(t) % 3]
        arr = cv2.remap(np.asarray(frame), mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return Image.fromarray(arr)


# ------------------------------------------------------------ trait dessiné
def _jit(pts, seed, amp):
    r = random.Random(seed)
    return [(x + r.uniform(-amp, amp), y + r.uniform(-amp, amp)) for x, y in pts]


def ink_poly(d, pts, fill, t, seed=0, width=5, jitter=1.6, outline=INK):
    pts = _jit(pts, seed * 131 + tick(t), jitter)
    d.polygon(pts, fill=fill)
    d.line(pts + [pts[0]], fill=outline, width=width, joint="curve")


def ink_line(d, pts, t, seed=0, width=5, color=INK, jitter=1.4):
    pts = _jit(pts, seed * 173 + tick(t), jitter)
    d.line(pts, fill=color, width=width, joint="curve")


def drop_shape(cx, cy, size, stretch=1.0):
    """Goutte : pointe en haut, ventre rond en bas."""
    pts = []
    for i in range(20):
        a = i / 20 * 2 * math.pi
        x = cx + size * 0.95 * math.sin(a) * math.sin(a / 2)
        y = cy - size * math.cos(a) * stretch
        pts.append((x, y))
    return pts


BLUE = (150, 214, 240)
BLUE_HI = (230, 248, 255)


def tears(d, t, path, rate=2.2, seed=0, size=13):
    """Gouttes qui glissent le long d'un chemin (liste de points)."""
    tq = on_twos(t)
    segs = [(path[i], path[i + 1]) for i in range(len(path) - 1)]
    lens = [math.dist(a, b) for a, b in segs]
    total = sum(lens)
    # filet continu
    ink_line(d, path, t, seed, width=14, color=BLUE, jitter=2.0)
    for k in range(4):
        u = ((tq * rate + k / 4 + seed * 0.37) % 1.0)
        dist = u * total
        for (a, b), L in zip(segs, lens):
            if dist <= L:
                x = a[0] + (b[0] - a[0]) * dist / L
                y = a[1] + (b[1] - a[1]) * dist / L
                break
            dist -= L
        s = size * (0.7 + 0.6 * u)
        ink_poly(d, drop_shape(x, y, s, 1.1), BLUE, t, seed * 7 + k, width=4)
        d.ellipse((x - s * 0.35, y - s * 0.2, x - s * 0.05, y + s * 0.2), fill=BLUE_HI)


def sweat(d, t, x, y, period=1.2, fall=70, seed=0, size=16):
    u = (on_twos(t) / period + seed * 0.29) % 1.0
    yy = y + fall * u * u
    ink_poly(d, drop_shape(x, yy, size * (1 - 0.3 * u), 1.2), BLUE, t, seed, width=4)
    d.ellipse((x - size * 0.35, yy - size * 0.2, x - size * 0.05, yy + size * 0.25), fill=BLUE_HI)


def vein(d, t, x, y, size=34, seed=0):
    """Veine de colère qui pulse."""
    s = size * (1 + 0.25 * abs(math.sin(on_twos(t) * 9)))
    red = (214, 36, 52)
    for q in range(4):
        a = q * math.pi / 2 + math.pi / 4
        cx, cy = x + math.cos(a) * s * 0.55, y + math.sin(a) * s * 0.55
        p0 = (cx - math.cos(a + math.pi / 2) * s * 0.4, cy - math.sin(a + math.pi / 2) * s * 0.4)
        p1 = (cx + math.cos(a) * s * -0.25, cy + math.sin(a) * s * -0.25)
        p2 = (cx + math.cos(a + math.pi / 2) * s * 0.4, cy + math.sin(a + math.pi / 2) * s * 0.4)
        ink_line(d, [p0, p1, p2], t, seed + q, width=int(s * 0.28), color=red, jitter=1.2)


def puffs(d, t, x, y, seed=0, count=5, spread=90, life=0.9, size=34, color=(236, 214, 178), drift=(0, -40)):
    """Nuages de poussière qui naissent, gonflent et s'effacent (dessinés à 12 i/s)."""
    tq = on_twos(t)
    for k in range(count):
        r = random.Random(seed * 97 + k)
        born = r.uniform(0, life)
        u = ((tq + born) % life) / life
        gen = int((tq + born) // life)
        r2 = random.Random(seed * 991 + k * 31 + gen)
        px = x + r2.uniform(-spread, spread) + drift[0] * u
        py = y + r2.uniform(-spread * 0.3, spread * 0.3) + drift[1] * u
        s = size * (0.4 + u) * r2.uniform(0.7, 1.2)
        if u > 0.85:
            continue
        pts = [(px + s * math.cos(a) * (1 + 0.12 * math.sin(a * 5 + k)),
                py + s * 0.8 * math.sin(a) * (1 + 0.12 * math.cos(a * 4 + k)))
               for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
        fade = int(190 * (1 - u / 0.85) ** 0.6)
        ink_poly(d, pts, color + (fade,), t, seed * 13 + k, width=3, jitter=2.0,
                 outline=(120, 96, 70, int(fade * 0.6)))


def feathers(d, t, box, n=12, seed=0, speed=110):
    x0, y0, x1, y1 = box
    tq = on_twos(t)
    for k in range(n):
        r = random.Random(seed * 71 + k)
        x = r.uniform(x0, x1) + math.sin(tq * 2.2 + k) * 30
        y = y0 + ((r.uniform(0, y1 - y0) + tq * speed * r.uniform(0.7, 1.3)) % (y1 - y0))
        a = math.sin(tq * 3 + k * 1.7) * 0.9
        L = r.uniform(26, 40)
        ca, sa = math.cos(a), math.sin(a)
        pts = [(x - L * ca, y - L * sa), (x - 4 * sa, y + 9 * ca), (x + L * ca, y + L * sa), (x + 4 * sa, y - 9 * ca)]
        ink_poly(d, pts, (246, 242, 232), t, seed * 5 + k, width=2, jitter=1.0, outline=(90, 74, 60))
        ink_line(d, [(x - L * ca, y - L * sa), (x + L * ca * 1.2, y + L * sa * 1.2)], t, seed + k, width=2, color=(90, 74, 60))


def muzzle(d, t, x, y, seed=0, size=90):
    r = random.Random(seed * 5 + tick(t))
    pts = []
    n = 11
    for i in range(n * 2):
        a = i / (n * 2) * 2 * math.pi + r.uniform(-0.1, 0.1)
        rr = size * (r.uniform(0.8, 1.25) if i % 2 == 0 else r.uniform(0.3, 0.45))
        pts.append((x + rr * math.cos(a) * 1.4, y + rr * math.sin(a) * 0.8))
    ink_poly(d, pts, (255, 206, 84), t, seed, width=5, jitter=0)
    inner = [(x + (px - x) * 0.5, y + (py - y) * 0.5) for px, py in pts]
    d.polygon(inner, fill=(255, 250, 214))


def casings(d, t, x, y, seed=0, rate=6):
    tq = on_twos(t)
    for k in range(5):
        u = (tq * rate / 5 + k / 5) % 1.0
        px = x + 140 * u
        py = y - 120 * u + 260 * u * u
        a = u * 12 + k
        L = 12
        pts = [(px - L * math.cos(a), py - L * math.sin(a)), (px + L * math.cos(a), py + L * math.sin(a))]
        ink_line(d, pts, t, seed + k, width=12, color=(214, 164, 58), jitter=0)
        ink_line(d, pts, t, seed + k, width=3, color=INK, jitter=0)


def rocks(d, t, x, y, seed=0, n=6, spread=160):
    tq = on_twos(t)
    for k in range(n):
        r = random.Random(seed * 17 + k)
        life = r.uniform(0.6, 1.0)
        u = ((tq + r.uniform(0, life)) % life) / life
        vx, vy = r.uniform(-1, 1) * spread, r.uniform(-1.4, -0.8) * spread
        px, py = x + vx * u, y + vy * u + 380 * u * u
        s = r.uniform(8, 16)
        pts = [(px + s * math.cos(a + u * 6), py + s * math.sin(a + u * 6)) for a in np.linspace(0, 2 * math.pi, 5, endpoint=False)]
        ink_poly(d, pts, (176, 84, 52), t, seed + k, width=3, jitter=1)


def action_marks(d, t, x, y, seed=0, size=40, n=3, angle=-0.6):
    """Petits traits de mouvement autour d'une main ou d'une tête."""
    if tick(t) % 4 >= 2:
        angle += 0.25
    for k in range(n):
        a = angle + (k - (n - 1) / 2) * 0.45
        p0 = (x + math.cos(a) * size, y + math.sin(a) * size)
        p1 = (x + math.cos(a) * size * 1.8, y + math.sin(a) * size * 1.8)
        ink_line(d, [p0, p1], t, seed + k, width=6)


def layer_for(img):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    return lay, ImageDraw.Draw(lay)
