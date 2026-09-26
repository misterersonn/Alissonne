"""Plan 3 en vrai cut-out : décor fixe + personnages vectoriels animés."""
import argparse
import math
import os
import subprocess

import imageio_ffmpeg
import numpy as np
from PIL import Image

import render as R
from chars import emu, farmer
from puppet import action_marks, layer_for, on_twos, puffs
from toon import composite, layer_rgba, new_layer, stickerize

HERE = os.path.dirname(os.path.abspath(__file__))
PW, PH = 1600, 893


def lerp(a, b, u):
    return a + (b - a) * u


def farmer_pose(t):
    # anticipation (on se tasse), puis explosion avec dépassement, puis boucle de rage
    pre = dict(lean=-4, head_rot=2, head_sy=0.93, mouth=0.12, arm_l=-150, fore_l=40,
               arm_r=150, fore_r=-40, spread=0.7, vein=0.0)
    rage = dict(lean=2 * math.sin(2 * math.pi * 1.5 * t),
                head_rot=3.5 * math.sin(2 * math.pi * 6 * t),
                head_sy=1 + 0.04 * abs(math.sin(2 * math.pi * 3 * t)),
                mouth=0.8 + 0.2 * abs(math.sin(2 * math.pi * 2 * t)),
                arm_l=-22 + 12 * math.sin(2 * math.pi * 4 * t),
                fore_l=-25 + 15 * math.sin(2 * math.pi * 4 * t + 0.8),
                arm_r=22 - 12 * math.sin(2 * math.pi * 4 * t + 1.1),
                fore_r=25 - 15 * math.sin(2 * math.pi * 4 * t + 1.9),
                spread=1.05 + 0.12 * math.sin(2 * math.pi * 5 * t),
                vein=1 + 0.25 * abs(math.sin(2 * math.pi * 3 * t)))
    if t < 0.55:
        k = R.ease_io(t / 0.55)
        p = dict(pre)
        p["head_sy"] = lerp(1.0, 0.93, k)
        p["lean"] = lerp(0, -4, k)
        return p
    k = R.back_out((t - 0.55) / 0.22, 2.6)
    p = {key: lerp(pre[key], rage[key], k) for key in pre}
    p["vein"] = rage["vein"] if t > 0.8 else 0.0
    return p


def emu_pose(t):
    chew = max(0.0, math.sin(2 * math.pi * 2.4 * t))
    look = 0.0 if t < 1.6 else R.ease_io((t - 1.6) / 0.35)
    blink = 0.0
    for bt in (1.2, 2.7, 4.3):
        if bt <= t < bt + 0.17:
            blink = 1 - abs((t - bt) / 0.085 - 1)
    return dict(body_sy=1 + 0.015 * math.sin(2 * math.pi * 0.7 * t),
                neck=6 * math.sin(2 * math.pi * 0.6 * t) + (10 * look),
                head_rot=-4 + 3 * math.sin(2 * math.pi * 0.6 * t) + 6 * look,
                jaw=3 + 12 * chew, look=-0.2 + 1.0 * look, blink=blink,
                stalk=math.sin(2 * math.pi * 2.4 * t + 0.5))


def frame(bg, kit, t):
    tq = on_twos(t)  # poses tenues deux images, comme en dessin animé
    s1, c1 = new_layer(PW, PH)
    emu(c1, 420, 860, emu_pose(tq))
    s2, c2 = new_layer(PW, PH)
    farmer(c2, 1180, 905, farmer_pose(tq))
    img = composite(composite(bg, stickerize(layer_rgba(s1))), stickerize(layer_rgba(s2)))
    pil = Image.fromarray(img)
    lay, d = layer_for(pil)
    if t > 0.75:
        action_marks(d, t, 760, 250, seed=6, size=70, angle=-2.5)
        action_marks(d, t, 1560, 260, seed=7, size=60, angle=-0.6)
    puffs(d, t, 860, 700, seed=8, count=4, spread=120, size=40)
    pil.paste(lay, (0, 0), lay)
    # caméra : léger push, secousse au moment du cri
    z = lerp(1.04, 1.16, R.ease_io(t / 5.5))
    sx, sy = R.shake(3, t, 0.012 if 0.55 < t < 1.3 else 0.0)
    f = R.camera(pil, 0.53, 0.46, z, sx, sy)
    R.chapter(f, kit, "1:30", "20,000 Hungry Dinosaurs", t)
    R.pop_text(f, kit, "*CRUNCH*", 84, (330, 170), t, rot=-8, appear=0.15, dur=0.9)
    R.subtitle(f, kit, "Twenty thousand emus. Zero manners.", t, 2.2, 5.3)
    return R.flash(f, t, 0.55, 0.1)


def audio(total):
    n = int(total * R.SR)
    out = np.zeros(n, np.float32)
    rng = np.random.default_rng(3)
    ts = np.arange(n) / R.SR

    def add(sig, at, g=1.0):
        i = int(at * R.SR)
        j = min(n, i + len(sig))
        out[i:j] += sig[:j - i] * g

    def env(L, a=0.005, dcy=6.0):
        tt = np.arange(int(L * R.SR)) / R.SR
        return np.minimum(1, tt / a) * np.exp(-tt * dcy)

    # crunch : craquements
    for k in range(3):
        L = 0.08
        add(rng.standard_normal(int(L * R.SR)) * env(L, 0.001, 40), 0.15 + k * 0.07, 0.5)
    # cri : dent de scie modulée + bruit
    L = total - 0.6
    tt = np.arange(int(L * R.SR)) / R.SR
    f0 = 330 + 40 * np.sin(2 * np.pi * 6 * tt)
    saw = 2 * ((np.cumsum(f0) / R.SR) % 1) - 1
    scream = (saw * 0.35 + np.convolve(rng.standard_normal(len(tt)), np.ones(6) / 6, "same") * 0.25)
    scream *= np.minimum(1, tt / 0.05) * np.minimum(1, (L - tt) / 0.3)
    add(scream, 0.6, 0.45)
    # coup sourd à l'explosion
    tt = np.arange(int(0.5 * R.SR)) / R.SR
    add(np.sin(2 * np.pi * np.cumsum(60 * (1 + 2 * np.exp(-tt * 30))) / R.SR) * env(0.5, 0.002, 8), 0.55, 1.0)
    # mâchouillement de l'émeu
    for k in range(int(total * 2.4)):
        L = 0.05
        add(rng.standard_normal(int(L * R.SR)) * env(L, 0.001, 60), k / 2.4 + 0.1, 0.18)
    out /= max(1e-6, np.abs(out).max()) / 0.85
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", required=True)
    ap.add_argument("--out", default=os.path.join(HERE, "plan3_cutout.mp4"))
    ap.add_argument("--stills", default=None)
    a = ap.parse_args()
    kit = R.Kit(a.fonts)
    bg = np.asarray(Image.open(os.path.join(HERE, "..", "img", "plates", "p3.jpg")).convert("RGB"))
    total = 5.5
    wav = a.out + ".wav"
    R.write_wav(wav, audio(total))
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{R.W}x{R.H}", "-r", str(R.FPS), "-i", "-", "-i", wav,
                             "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac",
                             "-shortest", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    cache = {}
    for i in range(int(total * R.FPS)):
        t = i / R.FPS
        f = frame(bg, kit, t)
        proc.stdin.write(f.tobytes())
        if a.stills and i % 6 == 0:
            f.save(os.path.join(a.stills, f"s3_{i:03d}.jpg"), quality=80)
    proc.stdin.close()
    proc.wait()
    os.remove(wav)
    print("ok", a.out)


if __name__ == "__main__":
    main()
