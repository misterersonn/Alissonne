import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gp_lib import Canvas, soldier, emu, lewis_gun, muzzle
out = sys.argv[sys.argv.index("--") + 1]
cv = Canvas()
cv.new_drawing(1)
soldier(cv, 200, 330, 0.9, eyes="wide", mouth="wobble", sweat=True)
soldier(cv, 530, 330, 0.9, eyes="dot", mouth="smile", hat="cap", mustache=True, hand_r=(640, 180), gl_r="open")
emu(cv, 230, 900, 0.9, None, eyes="wide", look=(1, 0))
emu(cv, 520, 1000, 0.7, 1, eyes="angry", beak_open=True, crown=True)
lewis_gun(cv, 430, 700, 0.8)
muzzle(cv, 650, 690, 0.8, 3)
cv.render(out, 1, 1)
print("OK")
