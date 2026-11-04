#!/usr/bin/env python3
"""Custom models inside the Castle Fight .w3x (reference only, never shipped): read the MPQ by file name.

    python3.14 tools/blender/w3x_models.py <map.w3x> <out-dir> [wc3-model-map.json]

The map is a protected MPQ: HM3W pre-header, broken header_size, encrypted tables and a hash table padded
with decoys, so a file is found by its name hash only. Candidates: every mdl path of the model map, as .mdx,
plus (listfile) and war3map.imp when they are there.
"""
import bz2
import json
import pathlib
import struct
import sys
import zlib

TABLE = []


def _table():
    seed = 0x00100001
    for i in range(256):
        idx = i
        for _ in range(5):
            seed = (seed * 125 + 3) % 0x2AAAAB
            hi = (seed & 0xFFFF) << 16
            seed = (seed * 125 + 3) % 0x2AAAAB
            TABLE.append(hi | (seed & 0xFFFF))
            idx += 0x100
    ordered = [0] * 1280
    for i in range(256):
        for j in range(5):
            ordered[i + j * 256] = TABLE[i * 5 + j]
    TABLE[:] = ordered


def hash_str(s, kind):
    seed1, seed2 = 0x7FED7FED, 0xEEEEEEEE
    for c in s.upper().replace("/", "\\").encode("latin1"):
        seed1 = (TABLE[(kind << 8) + c] ^ (seed1 + seed2)) & 0xFFFFFFFF
        seed2 = (c + seed1 + seed2 + (seed2 << 5) + 3) & 0xFFFFFFFF
    return seed1


def decrypt(data, key):
    out = bytearray()
    seed2 = 0xEEEEEEEE
    for i in range(0, len(data) - len(data) % 4, 4):
        seed2 = (seed2 + TABLE[0x400 + (key & 0xFF)]) & 0xFFFFFFFF
        v = struct.unpack_from("<I", data, i)[0]
        v = (v ^ (key + seed2)) & 0xFFFFFFFF
        key = (((~key << 21) + 0x11111111) | (key >> 11)) & 0xFFFFFFFF
        seed2 = (v + seed2 + (seed2 << 5) + 3) & 0xFFFFFFFF
        out += struct.pack("<I", v)
    return bytes(out) + data[len(data) - len(data) % 4:]


class Map:
    def __init__(self, path):
        self.b = pathlib.Path(path).read_bytes()
        self.base = self.b.find(b"MPQ\x1a")
        _, _, self.fmt, sector, hpos, bpos, hsize, bsize = struct.unpack_from("<IIHHIIII", self.b, self.base + 4)
        self.sector = 512 << sector
        h = decrypt(self.b[self.base + hpos:self.base + hpos + hsize * 16], hash_str("(hash table)", 3))
        bl = decrypt(self.b[self.base + bpos:self.base + bpos + bsize * 16], hash_str("(block table)", 3))
        self.hash = {}
        for i in range(hsize):
            a, c, _lc, idx = struct.unpack_from("<IIII", h, i * 16)
            if idx < bsize:
                self.hash.setdefault((a, c), idx)
        self.blocks = [struct.unpack_from("<IIII", bl, i * 16) for i in range(bsize)]

    def read(self, name):
        idx = self.hash.get((hash_str(name, 1), hash_str(name, 2)))
        if idx is None:
            return None
        pos, csize, fsize, flags = self.blocks[idx]
        raw = self.b[self.base + pos:self.base + pos + csize]
        key = 0
        if flags & 0x10000:                       # encrypted: key from the bare file name
            key = hash_str(name.replace("/", "\\").rsplit("\\", 1)[-1], 3)
            if flags & 0x20000:
                key = ((key + pos) ^ fsize) & 0xFFFFFFFF
        if flags & 0x1000000:                     # single unit
            return self._unpack(raw, fsize, flags)
        n = (fsize + self.sector - 1) // self.sector + 1
        table = raw[:n * 4]
        if flags & 0x10000:
            table = decrypt(table, (key - 1) & 0xFFFFFFFF)
        offs = struct.unpack(f"<{n}I", table)
        out = bytearray()
        for i in range(n - 1):
            s = raw[offs[i]:offs[i + 1]]
            if flags & 0x10000:
                s = decrypt(s, (key + i) & 0xFFFFFFFF)
            want = min(self.sector, fsize - len(out))
            out += self._unpack(s, want, flags)
        return bytes(out)

    @staticmethod
    def _unpack(s, size, flags):
        if len(s) >= size or not flags & 0x200:
            return s
        kind, body = s[0], s[1:]
        if kind == 2:
            return zlib.decompress(body)
        if kind == 0x10:
            return bz2.decompress(body)
        raise ValueError(f"compression {kind:#x}")


def candidates(model_map):
    rows = json.loads(pathlib.Path(model_map).read_text())
    names = set()
    for r in rows.values():
        m = r.get("mdl")
        if m:
            stem = m[:-4] if m.lower().endswith(".mdl") else m
            names |= {stem + ".mdx", stem + ".mdl"}
    return sorted(names)


def main():
    _table()
    m = Map(sys.argv[1])
    out = pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    print(f"{len(m.blocks)} blocks")
    for special in ("(listfile)", "war3map.imp", "(attributes)"):
        try:
            d = m.read(special)
        except Exception as e:                    # noqa: BLE001 - report and go on
            d = None
            print(special, "error", e)
        print(special, None if d is None else len(d))
        if d:
            (out / special.strip("()").replace(".", "_")).write_bytes(d)
    found = 0
    if len(sys.argv) > 3:
        for name in candidates(sys.argv[3]):
            try:
                d = m.read(name)
            except Exception as e:                # noqa: BLE001
                print(name, "error", e)
                continue
            if d:
                found += 1
                print("found", name, len(d), d[:4])
                (out / name.replace("\\", "__")).write_bytes(d)
    print("found", found)


if __name__ == "__main__":
    main()
