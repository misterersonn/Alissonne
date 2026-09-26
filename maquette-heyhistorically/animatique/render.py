"""Animatique de l'épisode pilote « The Army That LOST to Birds… ».

Monte les 8 plans du storyboard (img/p1..p8.jpg) et la miniature en une vidéo
MP4 : mouvements de caméra, tremblements, flashs, textes, sous-titres de la
voix off et bruitages synthétisés.

    pip install pillow numpy imageio-ffmpeg
    python render.py --fonts <dossier contenant luckiest.ttf et figtree.ttf>
"""
import argparse
import math
import os
import random
import subprocess
import wave

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1280, 720, 30
SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "..", "img")

INK = (27, 23, 36)
HOT = (224, 51, 107)
TEAL = (31, 165, 151)
GOLD = (231, 181, 58)


# --------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_io(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def back_out(x, s=2.2):
    x = clamp(x)
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


def lerp(a, b, t):
    return a + (b - a) * t


# --------------------------------------------------------------- drawing
class Kit:
    def __init__(self, fonts):
        self.fonts = fonts
        self.cache = {}

    def font(self, name, size):
        key = (name, size)
        if key not in self.cache:
            self.cache[key] = ImageFont.truetype(os.path.join(self.fonts, name), size)
        return self.cache[key]


def camera(src, cx, cy, zoom, dx=0.0, dy=0.0, rot=0.0):
    """Crop around (cx, cy) in 0..1 source coords at `zoom`, return W×H."""
    sw, sh = src.size
    cw = sw / zoom
    ch = cw * H / W
    if ch > sh:
        ch = sh
        cw = ch * W / H
    x = clamp(cx * sw - cw / 2 + dx * cw, 0, sw - cw)
    y = clamp(cy * sh - ch / 2 + dy * ch, 0, sh - ch)
    frame = src.resize((W, H), Image.BILINEAR, box=(x, y, x + cw, y + ch))
    if rot:
        frame = frame.rotate(rot, resample=Image.BILINEAR, expand=False, fillcolor=INK)
    return frame


def shake(seed, t, amp):
    r = random.Random(seed * 1000 + int(t * FPS))
    return (r.uniform(-1, 1) * amp, r.uniform(-1, 1) * amp)


def pop_text(frame, kit, text, size, center, t, color=(255, 255, 255), rot=0.0,
             appear=0.0, dur=None, font="luckiest.ttf"):
    """Comic text that bounces in with a red/cyan split and white/ink outline."""
    if t < appear or (dur is not None and t > appear + dur):
        return
    k = back_out((t - appear) / 0.28)
    if dur is not None:
        k *= 1 - ease_io((t - appear - dur + 0.18) / 0.18)
    if k <= 0.01:
        return
    f = kit.font(font, size)
    pad = size
    bbox = f.getbbox(text, stroke_width=8)
    tw, th = bbox[2] - bbox[0] + 2 * pad, bbox[3] - bbox[1] + 2 * pad
    layer = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ox, oy = pad - bbox[0], pad - bbox[1]
    d.text((ox + 5, oy + 4), text, font=f, fill=TEAL + (230,), stroke_width=8, stroke_fill=TEAL + (230,))
    d.text((ox - 4, oy - 3), text, font=f, fill=HOT + (230,), stroke_width=8, stroke_fill=HOT + (230,))
    d.text((ox, oy), text, font=f, fill=color, stroke_width=8, stroke_fill=INK)
    if rot:
        layer = layer.rotate(rot, resample=Image.BICUBIC, expand=True)
    nw, nh = max(1, int(layer.width * k)), max(1, int(layer.height * k))
    layer = layer.resize((nw, nh), Image.BICUBIC)
    frame.paste(layer, (int(center[0] - nw / 2), int(center[1] - nh / 2)), layer)


def subtitle(frame, kit, text, t, start, end):
    if not (start <= t <= end):
        return
    a = min(ease_out((t - start) / 0.2), ease_out((end - t) / 0.2))
    f = kit.font("figtree.ttf", 34)
    layer = Image.new("RGBA", (W, 120), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    tw = d.textlength(text, font=f)
    d.text(((W - tw) / 2, 40), text, font=f, fill=(255, 255, 255, int(255 * a)),
           stroke_width=5, stroke_fill=INK + (int(255 * a),))
    frame.paste(layer, (0, H - 130), layer)


def chapter(frame, kit, tc, label, t):
    """Chapter chip top-left, like the chapter list in the description."""
    k = ease_out(t / 0.35)
    fm = kit.font("figtree.ttf", 22)
    text = f"{tc}  {label}"
    d0 = ImageDraw.Draw(frame)
    tw = d0.textlength(text, font=fm)
    x = int(lerp(-tw - 60, 28, k))
    d0.rectangle((x - 4, 28, x + tw + 28, 70), fill=HOT)
    d0.rectangle((x - 10, 22, x + tw + 22, 64), fill=INK)
    d0.text((x + 6, 30), text, font=fm, fill=(255, 255, 255))


def flash(frame, t, at=0.0, length=0.18, color=(255, 255, 255)):
    x = (t - at) / length
    if 0 <= x <= 1:
        overlay = Image.new("RGB", frame.size, color)
        return Image.blend(frame, overlay, (1 - x) * 0.9)
    return frame


def rays(frame, t, center, color, alpha=70, n=18):
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    r = 1600
    for i in range(n):
        a0 = (i / n) * 2 * math.pi + t * 0.25
        a1 = a0 + math.pi / n * 0.55
        d.polygon([center,
                   (center[0] + r * math.cos(a0), center[1] + r * math.sin(a0)),
                   (center[0] + r * math.cos(a1), center[1] + r * math.sin(a1))],
                  fill=color + (alpha,))
    frame.paste(layer, (0, 0), layer)


def speed_lines(frame, t, center, seed):
    r = random.Random(seed + int(t * 12))
    d = ImageDraw.Draw(frame)
    for _ in range(46):
        a = r.uniform(0, 2 * math.pi)
        r0 = r.uniform(430, 560)
        r1 = r0 + r.uniform(120, 360)
        wdt = r.randint(2, 6)
        d.line([(center[0] + r0 * math.cos(a), center[1] + r0 * math.sin(a)),
                (center[0] + r1 * math.cos(a), center[1] + r1 * math.sin(a))], fill=INK, width=wdt)


def halftone_card(color_a, color_b):
    base = Image.new("RGB", (W, H), color_a)
    d = ImageDraw.Draw(base)
    for y in range(0, H, 14):
        for x in range(0, W, 14):
            rr = 1.2 + 3.2 * (1 - abs((x - W / 2) / (W / 2)))
            d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=color_b)
    return base


# --------------------------------------------------------------- shots
def build_shots(kit):
    imgs = {n: Image.open(os.path.join(IMG, f"{n}.jpg")).convert("RGB")
            for n in ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "thumb"]}
    card = halftone_card(INK, (52, 44, 68))

    def title(t):
        f = card.copy()
        rays(f, t, (W // 2, H // 2), HOT, alpha=40)
        pop_text(f, kit, "THE ARMY", 118, (W / 2, 250), t, rot=-3, appear=0.15)
        pop_text(f, kit, "THAT LOST", 118, (W / 2, 370), t, rot=2, appear=0.45, color=GOLD)
        pop_text(f, kit, "TO BIRDS...", 118, (W / 2, 490), t, rot=-2, appear=0.75, color=HOT)
        if t > 1.4:
            fm = kit.font("figtree.ttf", 28)
            d = ImageDraw.Draw(f)
            s = "La Grande Guerre des Émeus  ·  Australie, 1932"
            tw = d.textlength(s, font=fm)
            a = int(255 * ease_out((t - 1.4) / 0.4))
            d.text(((W - tw) / 2, 600), s, font=fm, fill=(255, 255, 255, a))
        return flash(f, t, 0.0, 0.12)

    def s1(t):  # cold open : push-in on the crying soldier
        z = lerp(1.05, 1.45, ease_io(t / 5))
        cx = lerp(0.5, 0.26, ease_io(t / 5))
        sx, sy = shake(1, t, 0.004 if t > 3 else 0.0)
        f = camera(imgs["p1"], cx, 0.5, z, sx, sy)
        subtitle(f, kit, "In 1932, the Australian army went to war. And lost. To birds.", t, 0.4, 4.8)
        return f

    def s2(t):  # context : slow pan across the farm
        f = camera(imgs["p2"], lerp(0.3, 0.72, ease_io(t / 5)), 0.52, 1.35)
        chapter(f, kit, "0:20", "Wheat, Veterans and Bad Economics", t)
        subtitle(f, kit, "These farmers were WW1 veterans. They had survived the Somme.", t, 0.3, 4.8)
        return f

    def s3(t):  # the emus : push toward the screaming farmer, CRUNCH
        z = lerp(1.1, 1.6, ease_out(t / 1.2)) if t < 2.2 else lerp(1.6, 1.75, (t - 2.2) / 2.8)
        sx, sy = shake(3, t, 0.012 if 1.0 < t < 1.8 else 0.002)
        f = camera(imgs["p3"], lerp(0.5, 0.7, ease_io(t / 1.2)), 0.4, z, sx, sy)
        chapter(f, kit, "1:30", "20,000 Hungry Dinosaurs", t)
        pop_text(f, kit, "*CRUNCH*", 96, (380, 250), t, rot=-8, appear=1.0, dur=1.6)
        subtitle(f, kit, "Twenty thousand emus. Zero manners.", t, 2.2, 4.9)
        return flash(f, t, 1.0, 0.1)

    def s4(t):  # the major : punch-in + name card
        z = lerp(1.9, 1.15, back_out(t / 0.5, 1.3))
        f = camera(imgs["p4"], 0.36, 0.42, z, 0, 0, lerp(-4, 0, ease_out(t / 0.5)))
        if t > 0.45:
            k = ease_out((t - 0.45) / 0.3)
            d = ImageDraw.Draw(f)
            x = int(lerp(-560, 40, k))
            d.polygon([(x, 430), (x + 540, 430), (x + 500, 520), (x - 40, 520)], fill=GOLD, outline=INK, width=6)
            d.text((x + 20, 440), "MAJOR MEREDITH", font=kit.font("luckiest.ttf", 58), fill=INK)
            d.rectangle((x + 10, 522, x + 300, 562), fill=INK)
            d.text((x + 22, 526), "very confident guy", font=kit.font("figtree.ttf", 26), fill=(255, 255, 255))
        chapter(f, kit, "2:40", "Major Meredith", t)
        subtitle(f, kit, "He had machine guns. They had... feet.", t, 1.6, 4.4)
        return flash(f, t, 0.0, 0.2, GOLD)

    def s5(t):  # the battle : heavy shake, muzzle flashes, MISS
        firing = (t % 0.9) < 0.45 and t < 4.2
        sx, sy = shake(5, t, 0.012 if firing else 0.003)
        f = camera(imgs["p5"], lerp(0.45, 0.55, t / 5.5), 0.5, 1.22, sx, sy)
        if firing and int(t * FPS) % 3 == 0:
            f = flash(f, 0, 0, 1, (255, 230, 170))
        chapter(f, kit, "4:00", "Operation: Run Away", t)
        pop_text(f, kit, "MISS!", 84, (230, 200), t, rot=-10, appear=0.6, dur=1.0)
        pop_text(f, kit, "MISS!", 84, (1040, 260), t, rot=8, appear=1.5, dur=1.0)
        pop_text(f, kit, "MISS!!", 104, (640, 170), t, rot=-4, appear=2.4, dur=1.4, color=HOT)
        subtitle(f, kit, "The emus used an advanced tactic: running away in different directions.", t, 3.0, 5.4)
        return f

    def s6(t):  # the truck : bouncy camera + BONK
        bounce = abs(math.sin(t * 9)) * 0.018
        sx, _ = shake(6, t, 0.004)
        f = camera(imgs["p6"], lerp(0.42, 0.6, ease_io(t / 5)), 0.5, 1.25, sx, -bounce, math.sin(t * 9) * 1.2)
        chapter(f, kit, "7:00", "The Truck Idea (bad idea)", t)
        for i, a in enumerate([0.4, 1.2, 2.0]):
            pop_text(f, kit, "BONK", 70, (200 + i * 170, 150 + (i % 2) * 40), t, rot=(-1) ** i * 9, appear=a, dur=0.6)
        subtitle(f, kit, "Emus can run at 50 km/h. The truck could not.", t, 2.4, 4.9)
        return f

    def s7(t):  # parliament : slow pull-out, colder
        z = lerp(1.6, 1.05, ease_io(t / 5.5))
        f = camera(imgs["p7"], 0.5, lerp(0.45, 0.5, t / 5.5), z)
        grey = f.convert("L").convert("RGB")
        f = Image.blend(f, grey, 0.25)
        chapter(f, kit, "9:30", "Parliament Laughs", t)
        pop_text(f, kit, "HA HA HA", 80, (640, 130), t, rot=-3, appear=1.2, dur=1.8)
        subtitle(f, kit, "986 kills for 9,860 rounds. That's ten bullets per bird.", t, 2.4, 5.4)
        return f

    def s8(t):  # victory : rays + stamp
        f = camera(imgs["p8"], 0.5, lerp(0.55, 0.38, ease_io(t / 5)), lerp(1.08, 1.35, ease_io(t / 5)))
        rays(f, t, (W // 2, 200), GOLD, alpha=35)
        chapter(f, kit, "11:30", "Did Anyone Win?", t)
        pop_text(f, kit, "EMUS 1 - ARMY 0", 92, (640, 600), t, rot=-3, appear=1.6, color=GOLD)
        subtitle(f, kit, "So did the army win? ... Next question.", t, 0.4, 1.5)
        return flash(f, t, 1.6, 0.15)

    def end(t):  # end card on the thumbnail
        z = lerp(1.2, 1.05, ease_out(t / 1.5))
        f = camera(imgs["thumb"], 0.5, 0.5, z)
        f = Image.blend(f, Image.new("RGB", f.size, INK), 0.35 * ease_out(t / 0.8))
        pop_text(f, kit, "THE ARMY THAT LOST TO BIRDS...", 64, (640, 300), t, rot=-2, appear=0.4)
        if t > 1.2:
            d = ImageDraw.Draw(f)
            fm = kit.font("figtree.ttf", 30)
            s = "Maquette animatique  ·  épisode pilote  ·  13–15 min"
            tw = d.textlength(s, font=fm)
            d.text(((W - tw) / 2, 400), s, font=fm, fill=(255, 255, 255))
        if t > 3.4:
            f = Image.blend(f, Image.new("RGB", f.size, (0, 0, 0)), ease_io((t - 3.4) / 0.6))
        return f

    return [(title, 3.0), (s1, 5.0), (s2, 5.0), (s3, 5.0), (s4, 4.5),
            (s5, 5.5), (s6, 5.0), (s7, 5.5), (s8, 5.0), (end, 4.0)]


# --------------------------------------------------------------- audio
def build_audio(shots):
    total = sum(d for _, d in shots)
    n = int(total * SR) + SR
    out = np.zeros(n, dtype=np.float32)
    rng = np.random.default_rng(7)

    def add(sig, at, gain=1.0):
        i = int(at * SR)
        j = min(n, i + len(sig))
        out[i:j] += sig[: j - i] * gain

    def env(length, attack=0.005, decay=6.0):
        t = np.arange(int(length * SR)) / SR
        return np.minimum(1, t / attack) * np.exp(-t * decay)

    def whoosh(length=0.35):
        noise = rng.standard_normal(int(length * SR)).astype(np.float32)
        t = np.linspace(0, 1, len(noise))
        shape = np.sin(np.pi * t) ** 2
        k = np.ones(24) / 24
        return np.convolve(noise, k, "same") * shape * 0.8

    def thump(freq=70, length=0.4):
        t = np.arange(int(length * SR)) / SR
        f = freq * (1 + 2.5 * np.exp(-t * 30))
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(length, 0.002, 9)

    def shot(length=0.12):
        noise = rng.standard_normal(int(length * SR)).astype(np.float32)
        return noise * env(length, 0.001, 38) * 0.7 + thump(55, length) * 0.6

    def bonk():
        t = np.arange(int(0.25 * SR)) / SR
        f = 420 * np.exp(-t * 4)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(0.25, 0.002, 12)

    def sting(chord, length=1.2):
        t = np.arange(int(length * SR)) / SR
        sig = sum(np.sign(np.sin(2 * np.pi * fr * t)) * 0.18 for fr in chord)
        return sig * env(length, 0.01, 2.8)

    def laugh(length=1.6):
        t = np.arange(int(length * SR)) / SR
        mod = (np.sin(2 * np.pi * 7 * t) > 0).astype(np.float32)
        noise = np.convolve(rng.standard_normal(len(t)), np.ones(8) / 8, "same")
        return noise * mod * env(length, 0.05, 1.5) * 0.5

    starts = np.cumsum([0] + [d for _, d in shots])
    for s in starts[1:-1]:
        add(whoosh(), s - 0.2, 0.5)
    t0 = starts
    add(thump(60, 0.6), t0[0] + 0.15, 0.9)
    add(thump(60, 0.6), t0[0] + 0.45, 0.9)
    add(thump(60, 0.6), t0[0] + 0.75, 0.9)
    add(sting([220, 277, 330]), t0[0] + 0.75, 0.6)
    add(thump(45, 0.8), t0[3] + 1.0, 1.0)                       # CRUNCH
    add(sting([196, 247, 294, 392], 1.4), t0[4], 0.6)           # the major
    for k in range(40):                                        # machine gun
        tt = k * 0.075
        if (tt % 0.9) < 0.45 and tt < 4.2:
            add(shot(), t0[5] + tt, 0.6)
    for a in [0.4, 1.2, 2.0]:
        add(bonk(), t0[6] + a, 0.7)
    add(laugh(), t0[7] + 1.2, 0.8)
    add(sting([262, 330, 392, 523], 1.8), t0[8] + 1.6, 0.7)     # EMUS 1 - ARMY 0
    add(thump(55, 0.7), t0[8] + 1.6, 1.0)
    add(sting([220, 262, 330], 1.5), t0[9] + 0.4, 0.5)

    out /= max(1e-6, np.abs(out).max()) / 0.85
    return out[: int(total * SR)]


def write_wav(path, samples):
    data = (np.clip(samples, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


# --------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", required=True)
    ap.add_argument("--out", default=os.path.join(HERE, "animatique.mp4"))
    ap.add_argument("--stills", default=None, help="dossier où écrire une image par plan")
    args = ap.parse_args()

    kit = Kit(args.fonts)
    shots = build_shots(kit)
    wav = args.out + ".wav"
    write_wav(wav, build_audio(shots))

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.Popen([
        ff, "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", wav,
        "-c:v", "libx264", "-preset", "medium", "-crf", "24", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", args.out,
    ], stdin=subprocess.PIPE)

    for idx, (fn, dur) in enumerate(shots):
        for i in range(int(round(dur * FPS))):
            t = i / FPS
            frame = fn(t)
            proc.stdin.write(frame.tobytes())
            if args.stills and abs(t - dur * 0.6) < 0.5 / FPS:
                frame.save(os.path.join(args.stills, f"shot{idx}.jpg"), quality=80)
    proc.stdin.close()
    proc.wait()
    os.remove(wav)
    print("ok", args.out)


if __name__ == "__main__":
    main()
