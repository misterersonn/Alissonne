"""Plan 3 en animation image par image (flipbook), sans interpolation.

Chaque personnage a une petite bibliothèque de dessins fixes (poses clés).
Une feuille d'exposition dit quel dessin montrer à quel moment : les dessins
changent 8 fois par seconde (chacun tenu 3 ou 4 images de la vidéo), comme en
animation limitée. Pour les cris, deux dessins alternent et le même dessin est
reposé à des positions un peu différentes, ce qui donne la secousse.
Le décor est une seule image fixe.
"""
import argparse
import os
import random
import subprocess

import imageio_ffmpeg
import numpy as np
from PIL import Image

import render as R
import shot3_test
from chars import emu, farmer
from puppet import action_marks, layer_for, puffs
from toon import layer_rgba, new_layer, stickerize

HERE = os.path.dirname(os.path.abspath(__file__))
PW, PH = 1600, 893
STEP = 1 / 8  # 8 dessins par seconde

# ------------------------------------------------------------ dessins du fermier
F = {
    "idle": dict(lean=0, head_rot=0, head_sy=1.0, mouth=0.18, arm_l=-160, fore_l=30, arm_r=160, fore_r=-30,
                 spread=0.7, vein=0.0),
    "hold": dict(lean=-3, head_rot=1, head_sy=0.93, mouth=0, face="tight", arm_l=175, fore_l=-128,
                 arm_r=-175, fore_r=128, hand_l="fist", hand_r="fist", arms_front=True, spread=1, vein=0.8),
    "scream_a": dict(lean=1, head_rot=-4, head_sy=1.04, mouth=1.0, arm_l=-24, fore_l=-26, arm_r=24, fore_r=26,
                     spread=1.1, vein=1.1),
    "scream_b": dict(lean=-1, head_rot=5, head_sy=1.0, mouth=0.82, arm_l=-8, fore_l=-12, arm_r=10, fore_r=8,
                     spread=1.25, vein=1.35),
    "point_a": dict(lean=-7, head_rot=-8, head_sy=1.02, mouth=0.92, arm_l=-78, fore_l=-8, hand_l="point",
                    arm_r=18, fore_r=-12, hand_r="fist", spread=1, vein=1.2),
    "point_b": dict(lean=-6, head_rot=-5, head_sy=1.0, mouth=0.7, arm_l=-74, fore_l=-12, hand_l="point",
                    arm_r=34, fore_r=-34, hand_r="fist", spread=1, vein=1.35),
}

# ------------------------------------------------------------ dessins de l'émeu
E_BASE = dict(body_sy=1.0, neck=0, head_rot=-4, jaw=3, look=-0.2, blink=0.0, stalk=0.0)
E = {
    "chew_closed": dict(E_BASE),
    "chew_open": dict(E_BASE, jaw=16, stalk=1.0, body_sy=1.01),
    "bored_closed": dict(E_BASE, blink=0.55),
    "bored_open": dict(E_BASE, blink=0.55, jaw=14, stalk=1.0),
    "look_closed": dict(E_BASE, look=0.9, head_rot=4, neck=12, jaw=4),
    "look_open": dict(E_BASE, look=0.9, head_rot=4, neck=12, jaw=13, stalk=1.0),
    "look_blink": dict(E_BASE, look=0.9, head_rot=4, neck=12, jaw=4, blink=1.0),
}

# ------------------------------------------------------------ feuilles d'exposition
# (début, [dessins en boucle], secousse en px)
FARMER_X = [
    (0.00, ["idle"], 0),
    (0.30, ["hold"], 2.5),
    (0.62, ["scream_a", "scream_b"], 7),
    (2.40, ["point_a", "point_b"], 5),
    (4.10, ["scream_a", "scream_b"], 7),
]
EMU_X = [
    (0.00, ["chew_closed", "chew_closed", "chew_open", "chew_open"], 0),
    (1.50, ["bored_closed", "bored_closed", "bored_open", "bored_open"], 0),
    (2.50, ["look_closed", "look_closed", "look_open", "look_open"], 0),
    (3.50, ["look_blink"], 0),
    (3.625, ["look_closed", "look_closed", "look_open", "look_open"], 0),
]


def expose(sheet, t, seed):
    cur = sheet[0]
    for e in sheet:
        if t >= e[0] - 1e-9:
            cur = e
    start, seq, amp = cur
    k = int((t - start) / STEP + 1e-6)
    tick = int(t / STEP + 1e-6)
    r = random.Random(seed * 1000 + tick)
    off = (r.uniform(-amp, amp), r.uniform(-amp, amp) * 0.6) if amp else (0.0, 0.0)
    return seq[k % len(seq)], off


def render_drawing(fn, x, y, pose):
    s, c = new_layer(PW, PH)
    fn(c, x, y, pose)
    return stickerize(layer_rgba(s))


def paste(base, layer, dx, dy):
    if dx or dy:
        layer = np.roll(np.roll(layer, int(round(dy)), axis=0), int(round(dx)), axis=1)
    al = layer[..., 3:4].astype(np.float32) / 255
    return (layer[..., :3] * al + base * (1 - al)).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", required=True)
    ap.add_argument("--out", default=os.path.join(HERE, "plan3_flipbook.mp4"))
    ap.add_argument("--stills", default=None)
    a = ap.parse_args()
    kit = R.Kit(a.fonts)
    plate = np.asarray(Image.open(os.path.join(HERE, "..", "img", "plates", "p3.jpg")).convert("RGB"))

    # chaque dessin est rendu une seule fois, puis réutilisé (comme un cellulo)
    farmer_cels = {k: render_drawing(farmer, 1180, 905, v) for k, v in F.items()}
    emu_cels = {k: render_drawing(emu, 420, 860, v) for k, v in E.items()}
    if a.stills:
        for k, cel in farmer_cels.items():
            Image.fromarray(paste(plate, cel, 0, 0)).resize((800, 446)).save(os.path.join(a.stills, f"cel_{k}.jpg"))

    total = 5.5
    wav = a.out + ".wav"
    R.write_wav(wav, shot3_test.audio(total))
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{R.W}x{R.H}", "-r", str(R.FPS), "-i", "-", "-i", wav,
                             "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac",
                             "-shortest", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    for i in range(int(total * R.FPS)):
        t = i / R.FPS
        en, eo = expose(EMU_X, t, 1)
        fname, fo = expose(FARMER_X, t, 2)
        img = paste(plate, emu_cels[en], *eo)
        img = paste(img, farmer_cels[fname], *fo)
        pil = Image.fromarray(img)
        lay, d = layer_for(pil)
        tq = int(t / STEP) * STEP
        if fname.startswith("scream"):
            action_marks(d, tq, 800, 250, seed=6, size=70, angle=-2.5)
            action_marks(d, tq, 1560, 250, seed=7, size=60, angle=-0.6)
        puffs(d, tq, 860, 700, seed=8, count=4, spread=120, size=40)
        pil.paste(lay, (0, 0), lay)
        f = R.camera(pil, 0.53, 0.46, 1.06)
        R.chapter(f, kit, "1:30", "20,000 Hungry Dinosaurs", t)
        R.pop_text(f, kit, "*CRUNCH*", 84, (330, 170), t, rot=-8, appear=0.1, dur=0.9)
        R.subtitle(f, kit, "Twenty thousand emus. Zero manners.", t, 2.2, 5.3)
        f = R.flash(f, t, 0.62, 0.1)
        proc.stdin.write(f.tobytes())
    proc.stdin.close()
    proc.wait()
    os.remove(wav)
    print("ok", a.out)


if __name__ == "__main__":
    main()
