"""Plan 3 en animation « poses clés » (image par image).

Plusieurs dessins du même plan, où seuls les personnages changent de pose,
sont enchaînés à cadence dessin animé (8 dessins/s, chaque dessin tenu 3 à 4
images de la vidéo). Le décor vient d'une seule image vide et ne bouge jamais :
de chaque dessin on ne garde que les personnages (zone qui diffère du décor
vide), recalés sur le premier dessin.
"""
import argparse
import os
import random
import subprocess

import cv2
import imageio_ffmpeg
import numpy as np
from PIL import Image

import render as R
import shot3_test

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "..", "img")
PW, PH = 1600, 893
DRAW_FPS = 8


def load(path):
    return np.asarray(Image.open(path).convert("RGB").resize((PW, PH), Image.LANCZOS))


def align(src, ref):
    """Recale `src` sur `ref` (translation / rotation / échelle) avec ORB + RANSAC."""
    orb = cv2.ORB_create(4000)
    g1 = cv2.cvtColor(src, cv2.COLOR_RGB2GRAY)
    g2 = cv2.cvtColor(ref, cv2.COLOR_RGB2GRAY)
    k1, d1 = orb.detectAndCompute(g1, None)
    k2, d2 = orb.detectAndCompute(g2, None)
    if d1 is None or d2 is None:
        return src
    m = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(d1, d2)
    m = sorted(m, key=lambda x: x.distance)[:600]
    if len(m) < 12:
        return src
    p1 = np.float32([k1[x.queryIdx].pt for x in m])
    p2 = np.float32([k2[x.trainIdx].pt for x in m])
    M, _ = cv2.estimateAffinePartial2D(p1, p2, method=cv2.RANSAC, ransacReprojThreshold=3)
    if M is None:
        return src
    return cv2.warpAffine(src, M, (PW, PH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def character_layer(drawing, plate, boxes):
    """Masque des personnages : ce qui diffère nettement du décor vide, dans les boîtes données."""
    a = cv2.GaussianBlur(drawing, (0, 0), 3).astype(np.int16)
    b = cv2.GaussianBlur(plate, (0, 0), 3).astype(np.int16)
    diff = np.abs(a - b).max(axis=2).astype(np.uint8)
    m = (diff > 38).astype(np.uint8)
    roi = np.zeros_like(m)
    for x0, y0, x1, y1 in boxes:
        roi[y0:y1, x0:x1] = 1
    m &= roi
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))
    # boucher les trous
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    keep = np.zeros_like(m)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] > 6000:
            keep[lab == i] = 1
    inv = (1 - keep).astype(np.uint8)
    n2, lab2 = cv2.connectedComponents(inv, connectivity=4)
    border = set(np.unique(np.concatenate([lab2[0], lab2[-1], lab2[:, 0], lab2[:, -1]])).tolist())
    holes = ~np.isin(lab2, list(border)) & (inv == 1)
    keep[holes] = 1
    keep = cv2.dilate(keep, np.ones((7, 7), np.uint8))
    alpha = cv2.GaussianBlur(keep.astype(np.float32) * 255, (0, 0), 2.0)
    return np.dstack([drawing, alpha.astype(np.uint8)])


def paste(base, layer, dx=0, dy=0, rot=0.0, pivot=(1200, 880)):
    if dx or dy or rot:
        M = cv2.getRotationMatrix2D(pivot, rot, 1.0)
        M[0, 2] += dx
        M[1, 2] += dy
        layer = cv2.warpAffine(layer, M, (PW, PH), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
    al = layer[..., 3:4].astype(np.float32) / 255
    return (layer[..., :3] * al + base * (1 - al)).astype(np.uint8)


# Feuille d'exposition : (début en s, dessins en alternance, secousse en px)
EXPOSURE = [
    (0.00, ["k1"], 1.5),           # anticipation : il se retient, ça tremble
    (0.62, ["k0", "k2"], 7.0),     # le cri : deux dessins en alternance + secousse
    (2.40, ["k3"], 4.0),           # il pointe l'émeu du doigt
    (2.65, ["k3", "k3"], 3.0),
    (4.10, ["k2", "k0"], 6.0),     # il repart de plus belle
]


def drawing_at(t):
    idx = int(t * DRAW_FPS)
    cur = EXPOSURE[0]
    for e in EXPOSURE:
        if t >= e[0]:
            cur = e
    start, seq, amp = cur
    k = int((t - start) * DRAW_FPS)
    r = random.Random(idx * 7919)
    return seq[k % len(seq)], (r.uniform(-amp, amp), r.uniform(-amp, amp) * 0.6, r.uniform(-amp, amp) * 0.12)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", required=True)
    ap.add_argument("--out", default=os.path.join(HERE, "plan3_poses.mp4"))
    ap.add_argument("--stills", default=None)
    a = ap.parse_args()
    kit = R.Kit(a.fonts)

    k0 = load(os.path.join(IMG, "p3.jpg"))
    plate = align(load(os.path.join(IMG, "plates", "p3.jpg")), k0)
    boxes = [(880, 100, 1600, 893), (150, 120, 900, 893)]
    layers = {"k0": character_layer(k0, plate, boxes)}
    for k in ("k1", "k2", "k3"):
        d = align(load(os.path.join(IMG, "poses", f"p3_{k}.jpg")), k0)
        layers[k] = character_layer(d, plate, boxes)
    if a.stills:
        for k, lay in layers.items():
            Image.fromarray(paste(plate, lay)).save(os.path.join(a.stills, f"pose_{k}.jpg"), quality=80)

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
        name, (dx, dy, rot) = drawing_at(t)
        img = Image.fromarray(paste(plate, layers[name], dx, dy, rot))
        z = shot3_test.lerp(1.04, 1.14, R.ease_io(t / total))
        sx, sy = R.shake(3, t, 0.01 if 0.62 < t < 1.2 else 0.0)
        f = R.camera(img, 0.53, 0.46, z, sx, sy)
        R.chapter(f, kit, "1:30", "20,000 Hungry Dinosaurs", t)
        R.pop_text(f, kit, "*CRUNCH*", 84, (330, 170), t, rot=-8, appear=0.1, dur=0.9)
        R.subtitle(f, kit, "Twenty thousand emus. Zero manners.", t, 2.2, 5.3)
        f = R.flash(f, t, 0.62, 0.1)
        proc.stdin.write(f.tobytes())
        if a.stills and i % 5 == 0:
            f.save(os.path.join(a.stills, f"kp_{i:03d}.jpg"), quality=80)
    proc.stdin.close()
    proc.wait()
    os.remove(wav)
    print("ok", a.out)


if __name__ == "__main__":
    main()
