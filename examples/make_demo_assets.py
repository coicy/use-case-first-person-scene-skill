"""Create intentionally synthetic illustration + UI fixture for offline overlay testing.

Run from the repo root: python examples/make_demo_assets.py
This draws no product screenshot and performs no AI generation or API calls.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path('out/demo')
OUT.mkdir(parents=True, exist_ok=True)
font = ImageFont.load_default()

def line(draw, pts, fill, width=2):
    draw.line(pts, fill=fill, width=width, joint='curve')

scene = Image.new('RGB', (960, 540), '#c9d3dc')
d = ImageDraw.Draw(scene)
d.rectangle((0, 0, 960, 230), fill='#e8eef1')
d.polygon([(0, 230), (960, 230), (960, 540), (0, 540)], fill='#a8b3b9')
d.polygon([(380, 230), (580, 230), (860, 540), (100, 540)], fill='#b7c3c8')
# racks and goods suggest a warehouse, deliberately schematic
for x, direction in [(0, 1), (960, -1)]:
    for col in range(5):
        y_top = 130 + col * 22
        y_bot = 510 - col * 48
        end = x + direction * (340-col*48)
        line(d, [(x, y_top), (end, y_top+12)], '#455d72', 8 if col == 0 else 5)
        line(d, [(x, y_bot), (end, y_bot-12)], '#455d72', 9 if col == 0 else 5)
        for j in range(4):
            bx = x + direction*(35+j*53)
            if 0 <= bx <= 960:
                d.rectangle((bx-15, 157+j*7, bx+15, 178+j*7), fill='#bb9472', outline='#926e50')
# lamp reflections and floor perspective
for k in range(5):
    line(d, [(480-(k+1)*33, 230), (480-(k+1)*90, 540)], '#8796a0', 1)
    line(d, [(480+(k+1)*33, 230), (480+(k+1)*90, 540)], '#8796a0', 1)
# hands and scanner device as seen from user eyes
d.ellipse((420, 408, 605, 565), fill='#c49177', outline='#886758', width=5)
d.polygon([(556, 247), (744, 232), (756, 452), (567, 472)], fill='#273a49')
d.polygon([(567, 245), (733, 234), (730, 406), (572, 409)], fill='#1a2631')
d.polygon([(570, 245), (731, 235), (727, 397), (574, 404)], fill='#ced6dc')
d.rounded_rectangle((605, 424, 703, 501), radius=9, fill='#334957', outline='#192530', width=3)
for yy in (435, 451, 467):
    for xx in (620, 648, 676):
        d.rounded_rectangle((xx, yy, xx+16, yy+10), radius=2, fill='#889da5')
d.text((24, 18), 'SYNTHETIC FIRST-PERSON SCENE - NOT A REAL PRODUCT', font=font, fill='#223747')
scene.save(OUT/'scene.png')

ui=Image.new('RGB',(480,470),'#f7fafc')
u=ImageDraw.Draw(ui)
u.rectangle((0,0,480,72),fill='#264f65')
u.text((22,22),'WAREHOUSE / SCAN',font=font,fill='white')
u.text((22,110),'ORDER #147 / AISLE 3',font=font,fill='#273747')
u.line((20,139,457,139),fill='#d6dce4',width=2)
u.text((22,174),'BARCODE VERIFIED',font=font,fill='#204d3f')
u.rounded_rectangle((22,218,458,318),radius=13,fill='#d6eee1')
u.text((45,252),'ITEM MATCHED / QTY 1',font=font,fill='#175135')
u.rounded_rectangle((22,375,458,438),radius=10,fill='#2e627b')
u.text((145,399),'CONFIRM DISPATCH',font=font,fill='white')
ui.save(OUT/'ui.png')
print(f'Demo fixtures: {OUT / "scene.png"} and {OUT / "ui.png"}')
