"""Personnages vectoriels dessinés en pièces détachées, dans le style de la chaîne.

Chaque personnage est dessiné en code avec cairo : tête blanche ovale, trait
encré épais, mains-gants à quatre doigts, ombres en trame de points, liseré
blanc « sticker » autour de la silhouette et léger décalage rouge / cyan.
Les pièces (tête, bouche, yeux, bras, mains, cou, bec…) ont chacune leur
articulation, ce qui permet de les animer comme un rig cut-out.
"""
import math

import cairo
import cv2
import numpy as np

INK = (27 / 255, 23 / 255, 36 / 255)
WHITE = (1, 1, 1)


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


# ------------------------------------------------------------ surfaces
def new_layer(w, h):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    c = cairo.Context(s)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.set_line_cap(cairo.LINE_CAP_ROUND)
    return s, c


def layer_rgba(surface):
    w, h = surface.get_width(), surface.get_height()
    buf = np.ndarray((h, surface.get_stride() // 4, 4), np.uint8, surface.get_data())[:, :w]
    b, g, r, a = [buf[..., i].astype(np.float32) for i in range(4)]
    af = np.maximum(a, 1) / 255.0
    out = np.dstack([r / af, g / af, b / af, a]).clip(0, 255).astype(np.uint8)
    return out


def stickerize(rgba, outline=10, aberration=3, hot=(224, 51, 107), teal=(31, 165, 151)):
    """Ajoute le liseré blanc extérieur et le décalage rouge / cyan."""
    a = rgba[..., 3]
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * outline + 1, 2 * outline + 1))
    halo = cv2.dilate(a, k)
    halo = cv2.GaussianBlur(halo, (0, 0), 0.8)
    h, w = a.shape
    out = np.zeros((h, w, 4), np.float32)

    def over(dst, rgb_arr, alpha):
        al = alpha[..., None] / 255.0
        dst[..., :3] = rgb_arr * al + dst[..., :3] * (1 - al)
        dst[..., 3:] = alpha[..., None] + dst[..., 3:] * (1 - al)

    shift = np.float32([[1, 0, aberration], [0, 1, 0]])
    red_a = cv2.warpAffine(halo, shift, (w, h)) * 0.55
    shift[0, 2] = -aberration
    cy_a = cv2.warpAffine(halo, shift, (w, h)) * 0.55
    over(out, np.full((h, w, 3), hot, np.float32), red_a)
    over(out, np.full((h, w, 3), teal, np.float32), cy_a)
    over(out, np.full((h, w, 3), 255, np.float32), halo.astype(np.float32))
    over(out, rgba[..., :3].astype(np.float32), a.astype(np.float32))
    return out.clip(0, 255).astype(np.uint8)


def composite(base_rgb, rgba):
    al = rgba[..., 3:4].astype(np.float32) / 255.0
    return (rgba[..., :3] * al + base_rgb * (1 - al)).astype(np.uint8)


# ------------------------------------------------------------ tracés
def smooth_path(c, pts, closed=True, tension=0.5):
    """Catmull-Rom → Bézier : des courbes souples à partir de quelques points."""
    n = len(pts)
    if n < 2:
        return
    c.move_to(*pts[0])
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        p0 = pts[(i - 1) % n] if (closed or i > 0) else pts[i]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if (closed or i + 2 < n) else p2
        k = tension / 3
        c.curve_to(p1[0] + (p2[0] - p0[0]) * k, p1[1] + (p2[1] - p0[1]) * k,
                   p2[0] - (p3[0] - p1[0]) * k, p2[1] - (p3[1] - p1[1]) * k,
                   p2[0], p2[1])
    if closed:
        c.close_path()


def ellipse_path(c, cx, cy, rx, ry, rot=0.0):
    c.save()
    c.translate(cx, cy)
    c.rotate(rot)
    c.scale(rx, ry)
    c.arc(0, 0, 1, 0, 2 * math.pi)
    c.restore()


def ink(c, fill=None, lw=8, color=INK):
    if fill is not None:
        c.set_source_rgb(*fill)
        c.fill_preserve()
    c.set_source_rgb(*color)
    c.set_line_width(lw)
    c.stroke()


def halftone(c, path_fn, color, direction=(0.7, 0.7), start=0.35, step=9, rmax=3.6, alpha=0.55):
    """Ombre en trame de points, du côté `direction` de la forme."""
    c.save()
    path_fn()
    x0, y0, x1, y1 = c.fill_extents()
    c.clip()
    c.set_source_rgba(*color, alpha)
    dx, dy = direction
    L = math.hypot(dx, dy)
    dx, dy = dx / L, dy / L
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    half = max(1.0, 0.5 * (abs(x1 - x0) * abs(dx) + abs(y1 - y0) * abs(dy)))
    y = y0
    row = 0
    while y <= y1:
        x = x0 + (step / 2 if row % 2 else 0)
        while x <= x1:
            u = ((x - cx) * dx + (y - cy) * dy) / half  # -1 .. 1
            k = (u - (start * 2 - 1)) / (1 - (start * 2 - 1) + 1e-6)
            if k > 0:
                r = min(rmax, rmax * k * 1.4)
                c.arc(x, y, r, 0, 2 * math.pi)
                c.new_sub_path()
            x += step
        y += step * 0.87
        row += 1
    c.fill()
    c.restore()


def capsule(c, x0, y0, x1, y1, width, fill, lw=7):
    """Membre (bras, doigt, patte) : un trait épais encré."""
    c.move_to(x0, y0)
    c.line_to(x1, y1)
    c.set_source_rgb(*INK)
    c.set_line_width(width + lw * 2)
    c.stroke()
    c.move_to(x0, y0)
    c.line_to(x1, y1)
    c.set_source_rgb(*fill)
    c.set_line_width(width)
    c.stroke()


def glove(c, x, y, angle, size=1.0, spread=1.0, lw=7):
    """Main-gant blanche à quatre doigts, paume vers la caméra."""
    c.save()
    c.translate(x, y)
    c.rotate(angle)
    c.scale(size, size)
    fingers = [(-0.62, 62), (-0.2, 72), (0.2, 70), (0.6, 60)]
    # contour encré des doigts
    for a, L in fingers:
        a *= spread
        capsule(c, 0, -10, math.sin(a) * L, -10 - math.cos(a) * L, 26, WHITE, lw)
    capsule(c, -8, 10, -58, -6, 26, WHITE, lw)  # pouce
    ellipse_path(c, 0, 8, 42, 38)
    ink(c, WHITE, lw)
    # repasser le blanc pour fondre les jonctions
    for a, L in fingers:
        a *= spread
        c.move_to(0, -10)
        c.line_to(math.sin(a) * L * 0.55, -10 - math.cos(a) * L * 0.55)
        c.set_source_rgb(*WHITE)
        c.set_line_width(24)
        c.stroke()
    c.move_to(-8, 10)
    c.line_to(-34, 2)
    c.set_line_width(24)
    c.stroke()
    # plis des doigts
    c.set_source_rgb(*INK)
    c.set_line_width(4)
    for a, _ in fingers[1:]:
        a *= spread
        c.move_to(math.sin(a - 0.2) * 30, -10 - math.cos(a - 0.2) * 30)
        c.line_to(math.sin(a - 0.2) * 18, -10 - math.cos(a - 0.2) * 18)
        c.stroke()
    c.restore()
