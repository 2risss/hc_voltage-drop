# 用途：生成本地 PWA 图标（不联网）
# 输出：web/icons/icon-192.png, web/icons/icon-512.png

from __future__ import annotations

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "icons"
RED = (180, 35, 24, 255)
WHITE = (255, 255, 255, 255)


def png_rgba(width: int, height: int, pixels: bytes) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b""
    stride = width * 4
    for y in range(height):
        raw += b"\x00" + pixels[y * stride : (y + 1) * stride]
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def draw_icon(size: int) -> bytes:
    buf = bytearray(size * size * 4)
    cx = cy = size / 2
    outer = size * 0.42
    inner = size * 0.28
    bar_w = size * 0.08
    bar_h = size * 0.36

    def set_px(x: int, y: int, color: tuple[int, int, int, int]) -> None:
        i = (y * size + x) * 4
        buf[i : i + 4] = bytes(color)

    for y in range(size):
        for x in range(size):
            dx = x + 0.5 - cx
            dy = y + 0.5 - cy
            r2 = dx * dx + dy * dy
            if r2 <= outer * outer:
                set_px(x, y, RED)
            else:
                set_px(x, y, (17, 17, 17, 255))
            if inner * inner <= r2 <= (inner + size * 0.05) ** 2:
                set_px(x, y, WHITE)
            if abs(dx) <= bar_w / 2 and abs(dy) <= bar_h / 2:
                set_px(x, y, WHITE)
    return png_rgba(size, size, bytes(buf))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "icon-192.png").write_bytes(draw_icon(192))
    (OUT / "icon-512.png").write_bytes(draw_icon(512))
    print("wrote icons")


if __name__ == "__main__":
    main()
