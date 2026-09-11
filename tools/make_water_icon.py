#!/usr/bin/env python3
"""Generate the Water Log app icons (192 and 512 px) with the standard library only.

No PIL. Writes RGBA PNGs of a blue water droplet-ish circle on the app's dark
background, matching the page tokens: background #0f1117, accent #4fa3ff.

Usage:
    python tools/make_water_icon.py            # writes into the repo root
    python tools/make_water_icon.py --out-dir .
"""

import argparse
import os
import struct
import zlib

BG = (0x0F, 0x11, 0x17, 255)
ACCENT = (0x4F, 0xA3, 0xFF, 255)
ACCENT_DEEP = (0x1E, 0x6F, 0xC8, 255)


def _blend(bottom, top, alpha):
    """alpha in 0..1, both RGBA tuples with opaque A."""
    return tuple(
        int(round(bottom[i] * (1 - alpha) + top[i] * alpha)) for i in range(3)
    ) + (255,)


def _coverage(dx, dy, radius):
    """Antialiased coverage of a pixel centre against a circle of `radius`."""
    dist = (dx * dx + dy * dy) ** 0.5
    edge = dist - radius
    if edge <= -0.5:
        return 1.0
    if edge >= 0.5:
        return 0.0
    return 0.5 - edge


def render(size):
    """Return raw RGBA rows for one icon of `size` x `size` pixels."""
    cx = cy = (size - 1) / 2.0
    outer = size * 0.40          # the blue disc
    inner = size * 0.30          # lighter core, gives it a little depth
    rows = []
    for y in range(size):
        row = bytearray()
        dy = y - cy
        for x in range(size):
            dx = x - cx
            px = BG
            cov_outer = _coverage(dx, dy, outer)
            if cov_outer > 0:
                px = _blend(px, ACCENT_DEEP, cov_outer)
            cov_inner = _coverage(dx, dy, inner)
            if cov_inner > 0:
                px = _blend(px, ACCENT, cov_inner)
            row += bytes(px)
        rows.append(bytes(row))
    return rows


def write_png(path, size):
    rows = render(size)
    raw = b"".join(b"\x00" + r for r in rows)   # filter type 0 per scanline

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # 8-bit RGBA
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    with open(path, "wb") as fh:
        fh.write(png)
    return len(png)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    args = ap.parse_args()
    for size in (192, 512):
        path = os.path.join(args.out_dir, "water-icon-%d.png" % size)
        n = write_png(path, size)
        print("wrote %s (%d bytes)" % (path, n))


if __name__ == "__main__":
    main()
