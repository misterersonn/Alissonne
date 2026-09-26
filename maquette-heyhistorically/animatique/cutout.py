"""Détoure les personnages grâce à leur liseré blanc, et reconstruit le décor.

Pour chaque boîte donnée, le liseré blanc (dilaté pour boucher les trous) sert
de mur : le fond est rempli depuis les bords de la boîte, tout ce qui n'est pas
atteint est le personnage. Les bords de boîte collés au bord de l'image ne
servent pas de départ, pour les personnages coupés par le cadre.
Le décor sans personnage est ensuite reconstruit par inpainting.
"""
import cv2
import numpy as np


def white_barrier(img, close=7):
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    white = ((hsv[:, :, 1] < 55) & (hsv[:, :, 2] > 215)).astype(np.uint8)
    return cv2.dilate(white, np.ones((close, close), np.uint8))


def cut_box(img, box, close=7, min_area=3000):
    h, w = img.shape[:2]
    x0, y0, x1, y1 = box
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(w, x1), min(h, y1)
    bar = white_barrier(img[y0:y1, x0:x1], close)
    free = (bar == 0).astype(np.uint8)
    n, lab = cv2.connectedComponents(free, connectivity=4)
    bw, bh = x1 - x0, y1 - y0
    edge = np.zeros_like(free, dtype=bool)
    if y0 > 0:
        edge[0, :] = True
    if y1 < h:
        edge[-1, :] = True
    if x0 > 0:
        edge[:, 0] = True
    if x1 < w:
        edge[:, -1] = True
    bg_labels = set(np.unique(lab[edge & (free == 1)]).tolist())
    bg = np.isin(lab, list(bg_labels)) & (free == 1)
    fg = (~bg).astype(np.uint8)
    # ne garder que les grosses pièces, boucher les trous
    n2, lab2, stats, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)
    keep = np.zeros_like(fg)
    for i in range(1, n2):
        if stats[i, cv2.CC_STAT_AREA] >= min_area:
            keep[lab2 == i] = 1
    keep = cv2.morphologyEx(keep, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    out = np.zeros((h, w), np.uint8)
    out[y0:y1, x0:x1] = keep * 255
    return out


def cutout(image, boxes):
    """Renvoie (décor RGB, liste de calques RGBA, masque global)."""
    img = np.asarray(image.convert("RGB"))
    masks = [cut_box(img, b) for b in boxes]
    union = np.zeros(img.shape[:2], np.uint8)
    for m in masks:
        union = np.maximum(union, m)
    hole = cv2.dilate(union, np.ones((9, 9), np.uint8))
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    small = cv2.resize(bgr, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    hs = cv2.resize(hole, (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST)
    filled = cv2.inpaint(small, hs, 9, cv2.INPAINT_TELEA)
    filled = cv2.resize(filled, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_CUBIC)
    filled = cv2.GaussianBlur(filled, (0, 0), 2)
    plate = np.where(hole[..., None] > 0, cv2.cvtColor(filled, cv2.COLOR_BGR2RGB), img)
    layers = []
    for m in masks:
        a = cv2.GaussianBlur(m, (0, 0), 0.8)
        layers.append(np.dstack([img, a]))
    return plate, layers, union
