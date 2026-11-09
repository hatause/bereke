"""Local-only extraction. Never place results in frontend or public directories."""
import hashlib
import json
from pathlib import Path
import pymupdf as fitz
from openpyxl import load_workbook
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.local/audit'
OUT.mkdir(parents=True, exist_ok=True)
inventory = []
for path in sorted((ROOT / 'sources/private').iterdir()):
    item = {'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    if path.suffix in ('.pdf', '.pptx'):
        doc = fitz.open(OUT / 'day3.pdf' if path.suffix == '.pptx' else path)
        pages = []
        folder = OUT / path.stem
        folder.mkdir(exist_ok=True)
        for i, page in enumerate(doc, 1):
            pages.append({'page': i, 'text': page.get_text(), 'images': len(page.get_images())})
            pix = page.get_pixmap(matrix=fitz.Matrix(1.3, 1.3))
            pix.save(str(folder / f'{i:03}.png'))
        item['pages'] = pages
        # Contact sheets for navigation; use individual PNG for fine print.
        for start in range(0, len(pages), 6):
            canvas = Image.new('RGB', (1500, 1080), 'white')
            draw = ImageDraw.Draw(canvas)
            for j in range(start, min(start+6, len(pages))):
                im = Image.open(folder / f'{j+1:03}.png')
                im.thumbnail((740, 330))
                x, y = ((j-start)%2)*750, ((j-start)//2)*360
                canvas.paste(im, (x,y+25))
                draw.text((x+10,y+5), f'Page {j+1}', fill='black')
            canvas.save(folder / f'contact-{start+1:03}.jpg')
    elif path.suffix == '.xlsx':
        wb = load_workbook(path, data_only=True)
        item['sheets'] = {ws.title: [[c for c in row] for row in ws.iter_rows(values_only=True)] for ws in wb}
        item['embedded_images'] = sum(len(ws._images) for ws in wb)
    inventory.append(item)
(OUT / 'extracted.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding='utf-8')
for item in inventory:
    print(item['file'], len(item.get('pages', [])), list(item.get('sheets', {})))
