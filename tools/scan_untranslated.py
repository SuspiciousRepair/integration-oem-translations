#!/usr/bin/env python3
"""List strings whose pt/es/th slot is the same text as the English one.
usage: scan_untranslated.py app.apk"""
import re, struct, sys, zipfile, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from patch_arsc import Pool, TypeChunk, u16, u32
SKIP = ('abc_', 'mtrl_', 'material_', 'm3_', 'sensors_analytics', 'accessibility_')
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
for name, d in sorted(vals.items()):
    if name.startswith(SKIP): continue
    en = d.get('en')
    if not en or len(re.findall('[A-Za-z]', en)) < 4 or en.startswith(('{', 'http')): continue
    same = [l for l in ('pt', 'es', 'th') if d.get(l, d.get('')) == en]
    if same: print('%-10s %-45s %r' % (','.join(same), name, en))
