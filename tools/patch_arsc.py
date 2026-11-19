#!/usr/bin/env python3
"""Copy an APK with some strings replaced, per language.

usage: patch_arsc.py in.apk translations.json out.apk

translations.json = {"pt": {"string_name": "texto", ...},
                     "en": {"string_name": "text", ...}}

Each language only touches its own slots (values-pt, values-pt-rBR, ...). When the app
has no slot for a name in that language, one is added. The default slot (the
fallback) is never touched. Only resources.arsc changes; every other file in
the APK is copied as is.

Drive Assist does the same on the car with a Java port
(modehelper/src/com/geely/modehelper/ArscPatch.java). Keep the two in step:
for the same input they must give the same resources.arsc bytes.
"""
import json, struct, sys, zipfile

def u16(b, o): return struct.unpack_from('<H', b, o)[0]
def u32(b, o): return struct.unpack_from('<I', b, o)[0]
NO_ENTRY = 0xffffffff

class Pool:
    def __init__(self, b, off):
        self.off = off
        (self.type, self.hsize, self.size, self.count, self.scount,
         self.flags, self.sstart, self.ystart) = struct.unpack_from('<HHIIIIII', b, off)
        self.utf8 = bool(self.flags & 0x100)
        h = off + self.hsize
        self.offs = list(struct.unpack_from('<%dI' % self.count, b, h))
        self.soffs = list(struct.unpack_from('<%dI' % self.scount, b, h + 4 * self.count))
        send = (off + self.ystart) if self.scount else (off + self.size)
        self.sdata = bytes(b[off + self.sstart:send])
        self.ydata = bytes(b[off + self.ystart:off + self.size]) if self.scount else b''

    def get(self, i):
        d, o = self.sdata, self.offs[i]
        if self.utf8:
            o += 2 if d[o] & 0x80 else 1                 # char count
            n = d[o]
            if n & 0x80: n = ((n & 0x7f) << 8) | d[o + 1]; o += 2
            else: o += 1
            return d[o:o + n].decode('utf-8')
        n = u16(d, o); o += 2
        if n & 0x8000: n = ((n & 0x7fff) << 16) | u16(d, o); o += 2
        return d[o:o + 2 * n].decode('utf-16-le')

    def add(self, s):
        if self.utf8:
            e = s.encode('utf-8'); c = len(s.encode('utf-16-le')) // 2
            def ln(n): return bytes([n]) if n < 0x80 else bytes([0x80 | (n >> 8), n & 0xff])
            raw = ln(c) + ln(len(e)) + e + b'\0'
        else:
            e = s.encode('utf-16-le'); n = len(e) // 2
            raw = (struct.pack('<H', n) if n < 0x8000 else
                   struct.pack('<HH', 0x8000 | (n >> 16), n & 0xffff)) + e + b'\0\0'
        self.offs.append(len(self.sdata)); self.sdata += raw; self.count += 1
        self.flags &= ~1                                 # an added string is not sorted
        return self.count - 1

    def build(self):
        sd = self.sdata + b'\0' * (-len(self.sdata) % 4)
        sstart = self.hsize + 4 * self.count + 4 * self.scount
        ystart = sstart + len(sd) if self.scount else 0
        size = sstart + len(sd) + len(self.ydata)
        return (struct.pack('<HHIIIIII', self.type, self.hsize, size, self.count,
                            self.scount, self.flags, sstart, ystart)
                + struct.pack('<%dI' % self.count, *self.offs)
                + struct.pack('<%dI' % self.scount, *self.soffs) + sd + self.ydata)

class TypeChunk:
    """One ResTable_type chunk (one config of one type)."""
    def __init__(self, raw):
        self.raw = bytearray(raw)
        self.hs = u16(raw, 2); self.id = raw[8]; self.sparse = raw[9] & 1
        self.n = u32(raw, 12); self.est = u32(raw, 16)
        cfg = 20; csize = u32(raw, cfg)
        self.lang = bytes(raw[cfg + 8:cfg + 10]).rstrip(b'\0').decode('latin1')
        self.country = bytes(raw[cfg + 10:cfg + 12]).rstrip(b'\0').decode('latin1')
        self.plain = not any(raw[cfg + 12:cfg + csize])     # no night/land/dpi/...

    def entries(self):
        """Yield (index, offset of entry in raw)."""
        r = self.raw
        for i in range(self.n):
            if self.sparse:
                idx, o = u16(r, self.hs + 4 * i), u16(r, self.hs + 4 * i + 2) * 4
            else:
                idx, o = i, u32(r, self.hs + 4 * i)
                if o == NO_ENTRY: continue
            yield idx, self.est + o

    def can_append(self, idx):
        return not self.sparse and idx < self.n and u32(self.raw, self.hs + 4 * idx) == NO_ENTRY

    def append(self, idx, key, value_index):
        """Add a plain string entry for a missing index (dense chunks only)."""
        assert self.can_append(idx)
        struct.pack_into('<I', self.raw, self.hs + 4 * idx, len(self.raw) - self.est)
        self.raw += struct.pack('<HHI', 8, 0, key) + struct.pack('<HBBI', 8, 0, 0x03, value_index)
        struct.pack_into('<I', self.raw, 4, len(self.raw))

def patch(arsc, tr):
    b = bytes(arsc)
    assert u16(b, 0) == 2
    g = Pool(b, u16(b, 2))
    off = g.off + g.size
    out_pkgs = b''
    report = []
    while off < len(b):
        ptype, phs, psize = struct.unpack_from('<HHI', b, off)
        assert ptype == 0x200
        types = Pool(b, off + u32(b, off + 268))
        keys = Pool(b, off + u32(b, off + 276))
        chunks, c = [], off + phs
        while c < off + psize:
            cs = u32(b, c + 4)
            raw = b[c:c + cs]
            ok = u16(raw, 0) == 0x201 and types.get(raw[8] - 1) == 'string'
            chunks.append(TypeChunk(raw) if ok else raw)
            c += cs
        strs = [t for t in chunks if isinstance(t, TypeChunk)]
        # name -> (entry index, key index), from every config
        where = {}
        for t in strs:
            for idx, e in t.entries():
                k = u32(t.raw, e + 4)
                where.setdefault(keys.get(k), (idx, k))
        for lang, table in tr.items():
            mine = [t for t in strs if t.lang == lang]          # pt, pt-BR, pt-PT, ...
            home = [t for t in mine if t.plain and not t.country]
            for name, text in table.items():
                if name not in where:
                    report.append(('MISS', lang, name, 'no such string')); continue
                idx, k = where[name]
                new = None; hit = False
                for t in mine:
                    for i, e in t.entries():
                        if i != idx: continue
                        v = e + u16(t.raw, e)
                        if u16(t.raw, e + 2) & 1 or t.raw[v + 3] != 0x03:
                            report.append(('SKIP', lang, name, 'not a plain string')); continue
                        if new is None: new = g.add(text)
                        if not hit:
                            report.append(('OK', lang, name, g.get(u32(t.raw, v + 4))))
                        struct.pack_into('<I', t.raw, v + 4, new); hit = True
                if not hit:
                    if not home or not home[0].can_append(idx):
                        report.append(('MISS', lang, name, 'app has no %s slot for it' % lang)); continue
                    if new is None: new = g.add(text)
                    home[0].append(idx, k, new)
                    report.append(('ADD', lang, name, None))
        body = b''.join(bytes(t.raw) if isinstance(t, TypeChunk) else t for t in chunks)
        hdr = bytearray(b[off:off + phs])
        struct.pack_into('<I', hdr, 4, phs + len(body))
        out_pkgs += bytes(hdr) + body
        off += psize
    pool = g.build()
    head = bytearray(b[:g.off])
    struct.pack_into('<I', head, 4, len(head) + len(pool) + len(out_pkgs))
    return bytes(head) + pool + out_pkgs, report

def main():
    src, trf, dst = sys.argv[1:4]
    tr = json.load(open(trf, encoding='utf-8'))
    zin = zipfile.ZipFile(src)
    arsc, report = patch(zin.read('resources.arsc'), tr)
    for what, lang, name, old in report:
        print('%-4s %s %-42s %s' % (what, lang, name, '' if old is None else repr(old)))
    with zipfile.ZipFile(dst, 'w') as zout:
        for i in zin.infolist():
            data = arsc if i.filename == 'resources.arsc' else zin.read(i.filename)
            zi = zipfile.ZipInfo(i.filename, i.date_time)
            zi.compress_type = i.compress_type; zi.external_attr = i.external_attr
            zout.writestr(zi, data)
    sys.exit(1 if any(r[0] == 'MISS' for r in report) else 0)

if __name__ == '__main__':
    main()
