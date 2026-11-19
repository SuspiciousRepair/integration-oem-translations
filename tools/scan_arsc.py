#!/usr/bin/env python3
"""Per language, list strings a user would see in Chinese.
usage: scan_arsc.py app.apk lang [lang...]   -> JSON {lang: {name: shown_text}}"""
import json, re, struct, sys, zipfile, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from patch_arsc import Pool, TypeChunk, u16, u32
CJK = re.compile(r'[㐀-鿿]')
SKIP = ('abc_', 'mtrl_', 'material_', 'm3_', 'sensors_analytics')
b = zipfile.ZipFile(sys.argv[1]).read('resources.arsc'); g = Pool(b, u16(b, 2))
off = g.off + g.size; vals = {}
while off < len(b):
    _, phs, psize = struct.unpack_from('<HHI', b, off)
    types = Pool(b, off + u32(b, off + 268)); keys = Pool(b, off + u32(b, off + 276))
    c = off + phs
    while c < off + psize:
        cs = u32(b, c + 4); raw = b[c:c + cs]
        if u16(raw, 0) == 0x201 and types.get(raw[8] - 1) == 'string':
            t = TypeChunk(raw)
            if t.plain and not t.country:
                for i, e in t.entries():
                    if u16(t.raw, e + 2) & 1: continue
                    v = e + u16(t.raw, e)
                    if t.raw[v + 3] == 3:
                        vals.setdefault(keys.get(u32(t.raw, e + 4)), {})[t.lang] = g.get(u32(t.raw, v + 4))
        c += cs
    off += psize
out = {}
for lang in sys.argv[2:]:
    out[lang] = {}
    for name, d in sorted(vals.items()):
        if name.startswith(SKIP): continue
        shown = d.get(lang, d.get('', ''))
        if CJK.search(shown) and not shown.lstrip().startswith('{data:'):
            out[lang][name] = shown
print(json.dumps(out, ensure_ascii=False, indent=1))
