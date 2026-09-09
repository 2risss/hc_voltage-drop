# 用途：从本地 xlsm 中提取 VBA 宏源码（不上传、不联网）
# 输入：data/压降计算公式.xlsm
# 输出：temp/*_vba.txt

from __future__ import annotations

import struct
from pathlib import Path

import olefile

ROOT = Path(__file__).resolve().parents[1]
BIN_PATH = ROOT / "temp" / "vba_extract" / "xl" / "vbaProject.bin"
OUT_DIR = ROOT / "temp"


def decompress(data: bytes, max_out: int = 2_000_000) -> bytes:
    if not data or data[0] != 0x01:
        raise ValueError(f"bad signature {data[:8]!r}")
    out = bytearray()
    cur = 1
    end = len(data)
    steps = 0
    while cur + 2 <= end:
        steps += 1
        if steps > 50_000 or len(out) > max_out:
            raise ValueError("decompress runaway")
        chunk_start = cur
        header = struct.unpack_from("<H", data, cur)[0]
        cur += 2
        compressed_size = (header & 0x0FFF) + 3
        chunk_sig = (header >> 12) & 0x07
        compressed_flag = header >> 15
        if chunk_sig != 0x03:
            raise ValueError(f"bad chunk sig {chunk_sig} header={header:#06x} at {chunk_start}")
        chunk_end = chunk_start + compressed_size
        if chunk_end > end:
            raise ValueError("chunk past end")
        if compressed_flag == 0:
            take = compressed_size - 2
            out += data[cur : cur + take]
            cur = chunk_end
            continue
        decomp_chunk_start = len(out)
        while cur < chunk_end:
            flag_byte = data[cur]
            cur += 1
            for bit in range(8):
                if cur >= chunk_end:
                    break
                if (flag_byte & (1 << bit)) == 0:
                    out.append(data[cur])
                    cur += 1
                else:
                    token = struct.unpack_from("<H", data, cur)[0]
                    cur += 2
                    bitcount = 4
                    dcur = len(out)
                    while (1 << bitcount) < (dcur - decomp_chunk_start) and bitcount < 12:
                        bitcount += 1
                    length_mask = 0xFFFF >> bitcount
                    offset_shift = 16 - bitcount
                    copy_len = (token & length_mask) + 3
                    offset = (token >> offset_shift) + 1
                    src = len(out) - offset
                    if src < 0:
                        raise ValueError("bad offset")
                    for _ in range(copy_len):
                        out.append(out[src])
                        src += 1
        cur = chunk_end
    return bytes(out)


def parse_module_offsets(dir_bytes: bytes) -> dict[str, int]:
    offsets: dict[str, int] = {}
    i = 0
    current_name = None
    n = len(dir_bytes)
    while i + 6 <= n:
        rec_id = struct.unpack_from("<H", dir_bytes, i)[0]
        rec_size = struct.unpack_from("<I", dir_bytes, i + 2)[0]
        if rec_size > n - i:
            break
        payload = dir_bytes[i + 6 : i + 6 + rec_size]
        i += 6 + rec_size
        if rec_id == 0x0019:
            current_name = payload.split(b"\x00", 1)[0].decode("latin1", errors="replace")
        elif rec_id == 0x0031 and rec_size >= 4 and current_name:
            offsets[current_name] = struct.unpack_from("<I", payload, 0)[0]
        elif rec_id == 0x0010:
            break
    return offsets


def main() -> None:
    ole = olefile.OleFileIO(BIN_PATH)
    dir_raw = ole.openstream(["VBA", "dir"]).read()
    dir_dec = decompress(dir_raw)
    OUT_DIR.joinpath("VBA_dir_decomp.bin").write_bytes(dir_dec)
    offsets = parse_module_offsets(dir_dec)
    print("offsets", offsets)

    for name, off in offsets.items():
        raw = ole.openstream(["VBA", name]).read()
        print(f"{name}: stream={len(raw)} offset={off}")
        if off >= len(raw):
            print("  offset past end")
            continue
        payload = raw[off:]
        print(f"  payload head={payload[:16].hex()} len={len(payload)}")
        try:
            text_bytes = decompress(payload)
            text = text_bytes.decode("latin1", errors="replace")
            outp = OUT_DIR / f"{name}_vba.txt"
            outp.write_text(text, encoding="utf-8", errors="replace")
            print(f"  wrote {outp.name} chars={len(text)}")
            print(text[:500])
            print("-----")
        except Exception as e:
            print(f"  decompress failed: {e}")
            # dump nearby 0x01 positions after offset
            ones = [i for i, b in enumerate(payload[:200]) if b == 0x01]
            print("  0x01 in first 200 of payload:", ones)


if __name__ == "__main__":
    main()
