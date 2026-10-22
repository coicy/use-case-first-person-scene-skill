"""Create a synthetic IN-SOFTWARE editor-like scene and a UI panel for projection testing.

No device, hands, desk, real screen or third-party screenshot is drawn.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path('out/demo')
OUT.mkdir(parents=True, exist_ok=True)
font = ImageFont.load_default()
scene = Image.new('RGB', (960, 540), '#1c2430')
d = ImageDraw.Draw(scene)
d.rectangle((0, 0, 959, 50), fill='#27394f')
d.text((18, 16), 'SYNTHETIC SOFTWARE WORKSPACE - NOT A REAL APP', font=font, fill='#eef2f8')
d.rectangle((0, 52, 165, 539), fill='#243246')
d.text((18, 92), 'SCENE TREE',font=font,fill='#e8f2f7')
for i, label in enumerate(['Main','Inventory','OrderList','BarcodeField','StatusMessage']):
    d.rectangle((12, 132+i*50, 155, 165+i*50), fill='#33445b')
    d.text((22, 143+i*50), label, font=font, fill='#f1f7fb')
d.rectangle((168, 52, 957, 539), fill='#192b39')
d.rectangle((182, 78, 580, 512), fill='#344356')
d.text((200, 92), 'ORDER PREVIEW', font=font, fill='#e9f3ff')
for i in range(7):
    d.rectangle((202, 129+i*47, 554, 154+i*47), fill='#465d74')
    d.text((220, 135+i*47), f'Item #{i+1:02d}', font=font, fill='#e4ebf2')
d.rectangle((580, 78, 770, 512), fill='#ebeff5')
d.text((599, 100), 'UI PANEL SLOT', font=font, fill='#16364a')
d.rectangle((780, 78, 944, 512), fill='#263548')
d.text((798, 105), 'DETAILS', font=font, fill='white')
scene.save(OUT/'scene.png')
ui = Image.new('RGB', (300, 400), '#f7fafc')
u = ImageDraw.Draw(ui)
u.rectangle((0,0,299,56),fill='#2c5270')
u.text((20,18),'ORDER REVIEW',font=font,fill='white')
u.text((18,102),'SKU: 123 / QTY: 1',font=font,fill='#233b49')
u.text((18,150),'BARCODE: PASS',font=font,fill='#1f6b49')
u.rectangle((18,202,282,265),fill='#c7e3d3')
u.text((33,225),'VERIFIED',font=font,fill='#1e513b')
u.rectangle((18,312,282,371),fill='#2e647e')
u.text((36,333),'CONFIRM',font=font,fill='white')
ui.save(OUT/'ui.png')
print(f'Demo synthetic app frames: {OUT / "scene.png"} and {OUT / "ui.png"}')
