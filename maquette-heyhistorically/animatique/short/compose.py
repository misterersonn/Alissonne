"""Assemble le short vertical « The Army That LOST to Birds » (720×1280, 24 i/s).

Décors, sous-titres, menus façon jeu vidéo, journal, fumée « SUBSCRIBE » et son,
par-dessus les personnages rendus par Blender (shots.py).

  python compose.py --shots <dossier des rendus> --fonts <dossier des polices> --out short.mp4
"""
import argparse
import glob
import math
import os
import random
import subprocess
import wave

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, SR = 720, 1280, 24, 44100
INK = (27, 23, 36)
GOLD = (242, 199, 90)
HOT = (224, 51, 107)


def font(d, name, size):
    return ImageFont.truetype(os.path.join(d, name), size)


# ------------------------------------------------------------ décors
PLATE = Image.open(os.path.join(HERE, "..", "..", "img", "plates", "p3.jpg")).convert("RGB")


def field(x_center=0.5, dark=0.0):
    """Recadrage vertical du décor de champ de blé (déjà peint, sans personnage)."""
    sw, sh = PLATE.size
    cw = sh * W / H
    x0 = int(min(max(0, x_center * sw - cw / 2), sw - cw))
    img = PLATE.crop((x0, 0, x0 + int(cw), sh)).resize((W, H), Image.LANCZOS)
    if dark:
        img = Image.blend(img, Image.new("RGB", img.size, (20, 16, 30)), dark)
    return img


def rays(c1=(255, 214, 120), c2=(240, 150, 60), t=0.0):
    img = Image.new("RGB", (W, H), c2)
    d = ImageDraw.Draw(img)
    cx, cy = W / 2, H * 0.4
    n = 16
    for i in range(n):
        a0 = i / n * 2 * math.pi + t * 0.3
        a1 = a0 + math.pi / n
        d.polygon([(cx, cy), (cx + 2000 * math.cos(a0), cy + 2000 * math.sin(a0)),
                   (cx + 2000 * math.cos(a1), cy + 2000 * math.sin(a1))], fill=c1)
    return img


def pink(t=0.0):
    y = np.linspace(0, 1, H)[:, None]
    top, bot = np.array([250, 205, 230]), np.array([205, 200, 250])
    arr = (top * (1 - y[..., None]) + bot * y[..., None]).repeat(W, axis=1).astype(np.uint8)
    img = Image.fromarray(arr)
    d = ImageDraw.Draw(img)
    r = random.Random(4)
    for k in range(26):
        x, yy = r.uniform(0, W), r.uniform(0, H)
        s = r.uniform(8, 22) * (0.6 + 0.4 * abs(math.sin(t * 3 + k)))
        d.polygon([(x, yy - s), (x + s * 0.25, yy - s * 0.25), (x + s, yy), (x + s * 0.25, yy + s * 0.25),
                   (x, yy + s), (x - s * 0.25, yy + s * 0.25), (x - s, yy), (x - s * 0.25, yy - s * 0.25)], fill=(255, 255, 255))
    return img


def grey(img):
    g = img.convert("L").convert("RGB")
    return Image.blend(g, Image.new("RGB", g.size, (30, 30, 36)), 0.25)


# ------------------------------------------------------------ incrustations
def outlined(d, xy, text, f, fill=(255, 255, 255), stroke=6, anchor="mm"):
    d.text(xy, text, font=f, fill=fill, stroke_width=stroke, stroke_fill=INK, anchor=anchor)


def caption(img, fonts, text, y=930):
    d = ImageDraw.Draw(img)
    f = font(fonts, "figtree.ttf", 40)
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        outlined(d, (W / 2, y + i * 50), ln, f, stroke=6)


def pop(img, fonts, text, xy, t, t0, size=90, color=(255, 255, 255), rot=0):
    if t < t0:
        return
    k = min(1.0, (t - t0) / 0.15)
    k = 1 + 0.3 * math.sin(k * math.pi) if k < 1 else 1.0
    f = font(fonts, "luckiest.ttf", int(size * k))
    lay = Image.new("RGBA", (W, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    outlined(d, (W / 2, 200), text, f, fill=color, stroke=8)
    lay = lay.rotate(rot, resample=Image.BICUBIC)
    img.paste(lay, (int(xy[0] - W / 2), int(xy[1] - 200)), lay)


def ui_box(img, fonts, title, rows, t, t0=0.1, x=60, y=90, w=600):
    """Fenêtre façon jeu vidéo : titre, lignes de stats, barres qui se remplissent."""
    if t < t0:
        return
    k = min(1.0, (t - t0) / 0.2)
    h = 90 + 70 * len(rows)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    yy = y + (1 - k) * -60
    d.rounded_rectangle((x, yy, x + w, yy + h), 18, fill=(40, 30, 24, 235), outline=GOLD, width=6)
    d.text((x + 30, yy + 22), title, font=font(fonts, "luckiest.ttf", 44), fill=GOLD)
    for i, (label, value, bar) in enumerate(rows):
        ry = yy + 90 + i * 70
        d.text((x + 30, ry), label, font=font(fonts, "figtree.ttf", 30), fill=(255, 255, 255))
        d.text((x + w - 30, ry), value, font=font(fonts, "figtree.ttf", 30), fill=GOLD, anchor="ra")
        if bar is not None:
            fillw = (w - 60) * min(1.0, bar) * min(1.0, max(0.0, (t - t0 - 0.2 - i * 0.12) / 0.4))
            d.rounded_rectangle((x + 30, ry + 40, x + w - 30, ry + 54), 7, fill=(80, 70, 60, 255))
            if fillw > 4:
                d.rounded_rectangle((x + 30, ry + 40, x + 30 + fillw, ry + 54), 7,
                                    fill=HOT if bar > 1 else (120, 210, 120, 255))
    img.paste(lay, (0, 0), lay)


def no_sign(img, xy, r=120):
    d = ImageDraw.Draw(img)
    x, y = xy
    d.ellipse((x - r, y - r, x + r, y + r), outline=(220, 30, 40), width=26)
    d.line((x - r * 0.7, y - r * 0.7, x + r * 0.7, y + r * 0.7), fill=(220, 30, 40), width=26)


def arrows(img, t):
    d = ImageDraw.Draw(img)
    for i in range(8):
        a = i / 8 * 2 * math.pi + 0.2
        L = 150 + 60 * min(1.0, t * 3)
        cx, cy = 330, 720
        x1, y1 = cx + 170 * math.cos(a), cy + 170 * math.sin(a)
        x2, y2 = cx + (170 + L) * math.cos(a), cy + (170 + L) * math.sin(a)
        d.line((x1, y1, x2, y2), fill=(220, 30, 40), width=14)
        ha = a + math.pi
        d.polygon([(x2, y2), (x2 + 34 * math.cos(ha + 0.5), y2 + 34 * math.sin(ha + 0.5)),
                   (x2 + 34 * math.cos(ha - 0.5), y2 + 34 * math.sin(ha - 0.5))], fill=(220, 30, 40))


def newspaper(img, fonts, t):
    k = min(1.0, t / 0.6)
    ang = (1 - k) * 720 + 6
    sc = 0.1 + 0.9 * k
    paper = Image.new("RGBA", (560, 700), (238, 230, 210, 255))
    d = ImageDraw.Draw(paper)
    d.rectangle((0, 0, 559, 699), outline=INK, width=8)
    d.text((280, 60), "THE DAILY NEWS", font=font(fonts, "luckiest.ttf", 50), fill=INK, anchor="mm")
    d.line((30, 100, 530, 100), fill=INK, width=4)
    for i, ln in enumerate(("ARMY LOSES", "WAR TO", "BIRDS")):
        d.text((280, 190 + i * 95), ln, font=font(fonts, "luckiest.ttf", 92), fill=INK, anchor="mm")
    d.text((280, 470), "Emus: \"no comment\"", font=font(fonts, "figtree.ttf", 32), fill=INK, anchor="mm")
    for i in range(6):
        d.line((40, 520 + i * 26, 520, 520 + i * 26), fill=(150, 140, 130), width=8)
    p = paper.resize((max(1, int(560 * sc)), max(1, int(700 * sc))), Image.BICUBIC).rotate(ang, expand=True, resample=Image.BICUBIC)
    img.paste(p, (int(W / 2 - p.width / 2), int(H * 0.45 - p.height / 2)), p)


def smoke(img, fonts, t):
    d = ImageDraw.Draw(img)
    r = random.Random(9)
    for k in range(40):
        x, y = r.uniform(-50, W + 50), r.uniform(200, 1100)
        s = r.uniform(90, 200) * (1 + 0.15 * t)
        c = r.randint(170, 215)
        d.ellipse((x - s, y - s * 0.8, x + s, y + s * 0.8), fill=(c, c, c + 4))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    a = int(255 * min(1.0, t / 0.5))
    f = font(fonts, "luckiest.ttf", 150)
    ld.text((W / 2, 560), "SUBS", font=f, fill=(245, 245, 245, a), stroke_width=10, stroke_fill=(120, 120, 128, a), anchor="mm")
    ld.text((W / 2, 720), "CRIBE!", font=f, fill=(245, 245, 245, a), stroke_width=10, stroke_fill=(120, 120, 128, a), anchor="mm")
    img.paste(lay.rotate(-8, resample=Image.BICUBIC), (0, 0), lay.rotate(-8, resample=Image.BICUBIC))


def feathers(img, t, n=18):
    d = ImageDraw.Draw(img)
    r = random.Random(3)
    for k in range(n):
        x = r.uniform(0, W) + 30 * math.sin(t * 2 + k)
        y = (r.uniform(-200, H) + t * 260) % (H + 200) - 100
        a = math.sin(t * 3 + k)
        L = 34
        pts = [(x - L * math.cos(a), y - L * math.sin(a)), (x + 8 * math.sin(a), y - 8 * math.cos(a)),
               (x + L * math.cos(a), y + L * math.sin(a)), (x - 8 * math.sin(a), y + 8 * math.cos(a))]
        d.polygon(pts, fill=(245, 240, 230), outline=INK)


# ------------------------------------------------------------ plans
def chars(shots, name, i):
    fs = sorted(glob.glob(os.path.join(shots, name, "f_*.png")))
    return Image.open(fs[min(i, len(fs) - 1)]).convert("RGBA") if fs else None


def camera(img, z=1.0, sx=0.0, sy=0.0):
    if z == 1.0 and not sx and not sy:
        return img
    cw, ch = W / z, H / z
    x0 = (W - cw) / 2 + sx
    y0 = (H - ch) / 2 + sy
    return img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))


def build_plan(fonts):
    # (nom, images, fond(t), incrustations(img, t, i), zoom début→fin, secousse)
    return [
        ("s1", 48, lambda t: field(0.3), lambda im, t, i: caption(im, fonts, "1932. Australia declares war..."), (1.0, 1.08), 0),
        ("s2", 48, lambda t: field(0.2), lambda im, t, i: caption(im, fonts, "...on EMUS."), (1.1, 1.0), 0),
        ("s3", 60, lambda t: field(0.15), lambda im, t, i: ui_box(im, fonts, "EMU  STATS", [
            ("SPEED", "50 km/h", 0.95), ("ARMOR", "feathers", 0.3), ("FEAR", "none", 0.02), ("HUNGER", "MAX", 1.2)], t), (1.0, 1.04), 0),
        ("s4", 60, lambda t: rays(t=t), lambda im, t, i: (caption(im, fonts, "Major Meredith.\nVery confident guy."),
                                                         ui_box(im, fonts, "CONFIDENCE", [("LEVEL", "999%", 1.5)], t, 0.6, y=70)),
         (1.12, 1.0), 0),
        ("s5", 48, lambda t: field(0.5, 0.1), lambda im, t, i: caption(im, fonts, "2 machine guns.\n10,000 bullets."), (1.0, 1.05), 9),
        ("s6", 60, lambda t: field(0.6), lambda im, t, i: (pop(im, fonts, "MISS!", (200, 330), t, 0.3, rot=8),
                                                           pop(im, fonts, "MISS!", (520, 480), t, 0.9, rot=-6),
                                                           pop(im, fonts, "MISS!!", (360, 230), t, 1.6, 110, HOT, 4)), (1.0, 1.0), 3),
        ("s7", 48, lambda t: grey(field(0.4)), lambda im, t, i: caption(im, fonts, "The emus... split up."), (1.0, 1.05), 0),
        ("s8", 48, lambda t: pink(t), lambda im, t, i: (arrows(im, t), caption(im, fonts, "Emu tactic:\nrun in ALL directions.", 1060)),
         (1.0, 1.03), 0),
        ("s9", 48, lambda t: field(0.8, 0.25), lambda im, t, i: ui_box(im, fonts, "RESULTS", [
            ("BULLETS", f"{int(min(1, t / 1.2) * 9860):,}", None), ("EMUS HIT", f"{int(min(1, t / 1.2) * 986)}", None)], t, 0.05),
         (1.0, 1.05), 0),
        ("s10", 48, lambda t: field(0.7), lambda im, t, i: newspaper(im, fonts, t), (1.0, 1.0), 0),
        ("s11", 60, lambda t: rays((255, 226, 140), (250, 180, 80), t), lambda im, t, i: (
            feathers(im, t), pop(im, fonts, "EMUS 1 - ARMY 0", (360, 180), t, 0.4, 76, GOLD, -4)), (1.05, 1.0), 0),
        ("s12", 48, lambda t: Image.new("RGB", (W, H), (150, 150, 158)), lambda im, t, i: smoke(im, fonts, t), (1.0, 1.04), 0),
    ]


# ------------------------------------------------------------ son
def build_audio(plan):
    total = sum(n for _, n, *_ in plan) / FPS
    n = int(total * SR)
    out = np.zeros(n, np.float32)
    rng = np.random.default_rng(1)

    def add(sig, at, g=1.0):
        i = int(at * SR)
        j = min(n, i + len(sig))
        if j > i:
            out[i:j] += sig[:j - i] * g

    def env(L, a=0.004, dcy=8.0):
        tt = np.arange(int(L * SR)) / SR
        return np.minimum(1, tt / a) * np.exp(-tt * dcy)

    def tone(freq, L, dcy=6.0, square=False):
        tt = np.arange(int(L * SR)) / SR
        w = np.sin(2 * np.pi * freq * tt)
        if square:
            w = np.sign(w) * 0.6
        return w * env(L, 0.003, dcy)

    def noise(L, dcy=30.0):
        return rng.standard_normal(int(L * SR)).astype(np.float32) * env(L, 0.001, dcy)

    # petite marche militaire en fond : caisse claire + basse
    beat = 60 / 118
    notes = [98, 98, 131, 98, 110, 110, 147, 110]
    k = 0
    tt = 0.0
    while tt < total - 1.5:
        add(noise(0.12, 28) * 0.35, tt)
        add(noise(0.06, 40) * 0.2, tt + beat / 2)
        add(tone(notes[k % 8], beat * 0.9, 5, True) * 0.18, tt)
        k += 1
        tt += beat
    starts = np.cumsum([0] + [nn / FPS for _, nn, *_ in plan])
    for s in starts[1:-1]:
        wh = rng.standard_normal(int(0.25 * SR)).astype(np.float32)
        wh = np.convolve(wh, np.ones(30) / 30, "same") * np.sin(np.linspace(0, np.pi, len(wh))) ** 2
        add(wh * 0.8, s - 0.12)
    idx = {name: starts[i] for i, (name, *_) in enumerate(plan)}
    add(tone(880, 0.3, 10), idx["s3"] + 0.1, 0.4)          # « ding » du menu
    add(tone(1320, 0.3, 10), idx["s3"] + 0.15, 0.3)
    for j in range(4):
        add(tone(660 + 110 * j, 0.12, 20), idx["s3"] + 0.3 + j * 0.12, 0.25)
    add(tone(523, 0.5, 4), idx["s4"] + 0.2, 0.35)
    add(tone(659, 0.5, 4), idx["s4"] + 0.35, 0.35)
    add(tone(784, 0.8, 3), idx["s4"] + 0.5, 0.35)
    for j in range(0, 22):                                 # rafales
        add(noise(0.07, 45) * 0.9 + tone(70, 0.07, 30) * 0.8, idx["s5"] + j * 0.09)
    for a in (0.3, 0.9, 1.6):                              # MISS
        add(tone(300, 0.25, 10) * np.linspace(1, 0.2, int(0.25 * SR)), idx["s6"] + a, 0.5)
    add(tone(196, 1.2, 1.5), idx["s7"], 0.3)               # accord triste
    add(tone(233, 1.2, 1.5), idx["s7"], 0.25)
    for j in range(10):                                    # compteur
        add(tone(1200, 0.04, 40), idx["s9"] + 0.05 + j * 0.11, 0.2)
    add(noise(0.6, 4) * 0.4, idx["s10"])                   # journal
    for j, fq in enumerate((523, 659, 784, 1046)):         # fanfare
        add(tone(fq, 0.6, 3), idx["s11"] + 0.4 + j * 0.12, 0.3)
    add(noise(1.4, 1.5) * 0.3, idx["s12"])                 # fumée
    out /= max(1e-6, np.abs(out).max()) / 0.85
    return out


def write_wav(path, samples):
    data = (np.clip(samples, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", required=True)
    ap.add_argument("--fonts", required=True)
    ap.add_argument("--out", default=os.path.join(HERE, "emu_war_short.mp4"))
    ap.add_argument("--stills", default=None)
    a = ap.parse_args()
    plan = build_plan(a.fonts)
    wav = a.out + ".wav"
    write_wav(wav, build_audio(plan))
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-crf", "21", "-pix_fmt", "yuv420p",
                             "-c:a", "aac", "-shortest", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    for name, n, bg, fx, (z0, z1), shake in plan:
        for i in range(n):
            t = i / FPS
            img = bg(t).convert("RGBA")
            ch = chars(a.shots, name, i)
            if ch is not None:
                img = Image.alpha_composite(img, ch)
            img = img.convert("RGB")
            if name == "s7":
                img = grey(img)
            r = random.Random(i * 13)
            u = i / max(1, n - 1)
            img = camera(img, z0 + (z1 - z0) * (u * u * (3 - 2 * u)), r.uniform(-shake, shake), r.uniform(-shake, shake))
            fx(img, t, i)
            proc.stdin.write(img.tobytes())
            if a.stills and i == n // 2:
                img.save(os.path.join(a.stills, f"{name}.jpg"), quality=80)
    proc.stdin.close()
    proc.wait()
    os.remove(wav)
    print("ok", a.out)


if __name__ == "__main__":
    main()
