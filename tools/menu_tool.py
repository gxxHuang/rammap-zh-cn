# -*- coding: utf-8 -*-
"""RAMMap 菜单模板解析器/生成器（基于实测确认的格式）。

格式（实测）：
  [4 bytes] MENUHEADER: wVersion=0, wHeaderSize=0
  重复项:
    WORD   flags         (MF_POPUP=0x0010, MF_END=0x0080, MF_SEPARATOR 用空字符串+0x0000)
    if popup:  无 ID 字段
    else:      WORD id       (空文本 = 分隔符)
    WCHAR  text[]        以 NUL 结尾
  无额外对齐要求。
"""
import struct

MF_POPUP = 0x0010
MF_END = 0x0080


def read_wstr(b, pos):
    end = pos
    while b[end:end + 2] != b'\x00\x00':
        end += 2
    return b[pos:end].decode('utf-16-le'), end + 2


def parse_menu(b):
    pos = 4  # skip MENUHEADER
    items, pos = parse_level(b, pos)
    return items, pos


def parse_level(b, pos):
    items = []
    while True:
        flags, = struct.unpack('<H', b[pos:pos + 2]); pos += 2
        if flags & MF_POPUP:
            text, pos = read_wstr(b, pos)
            sub, pos = parse_level(b, pos)
            items.append({'flags': flags, 'text': text, 'sub': sub})
        else:
            mid, = struct.unpack('<H', b[pos:pos + 2]); pos += 2
            text, pos = read_wstr(b, pos)
            items.append({'flags': flags, 'id': mid, 'text': text})
        if flags & MF_END:
            break
    return items, pos


def gen_menu(items):
    out = bytearray(struct.pack('<HH', 0, 0))
    gen_level(items, out)
    return bytes(out)


def gen_level(items, out):
    n = len(items)
    for i, it in enumerate(items):
        flags = it['flags']
        if i == n - 1:
            flags |= MF_END
        out += struct.pack('<H', flags)
        if flags & MF_POPUP:
            out += it['text'].encode('utf-16-le') + b'\x00\x00'
            gen_level(it['sub'], out)
        else:
            out += struct.pack('<H', it.get('id', 0))
            out += it['text'].encode('utf-16-le') + b'\x00\x00'


def dump(items, ind=0):
    for it in items:
        if it['flags'] & MF_POPUP:
            print('  ' * ind + f"POPUP flags=0x{it['flags']:04X} text={it['text']!r}")
            dump(it['sub'], ind + 1)
        else:
            print('  ' * ind + f"ITEM  flags=0x{it['flags']:04X} id=0x{it['id']:04X} text={it['text']!r}")


if __name__ == '__main__':
    import pefile, sys
    for path in sys.argv[1:]:
        pe = pefile.PE(path, fast_load=True); pe.parse_data_directories()
        blob = None
        for r in pe.DIRECTORY_ENTRY_RESOURCE.entries:
            tn = r.name.string.decode() if r.name else pefile.RESOURCE_TYPE.get(r.struct.Id, str(r.struct.Id))
            if tn != 'RT_MENU': continue
            for l in r.directory.entries:
                for d in l.directory.entries:
                    off = pe.get_offset_from_rva(d.data.struct.OffsetToData)
                    blob = bytes(pe.__data__[off:off + d.data.struct.Size])
        print(f"===== {path} ({len(blob)} bytes) =====")
        items, consumed = parse_menu(blob)
        dump(items)
        print(f"consumed={consumed} / total={len(blob)}  (tail {len(blob)-consumed} bytes)")
        # 往返测试
        regen = gen_menu(items)
        same = regen == blob[:len(regen)]
        print(f"round-trip identical: {same}  regen_len={len(regen)}")
        if not same:
            for i in range(min(len(regen), len(blob))):
                if regen[i] != blob[i]:
                    print(f"  first diff at {i}: {regen[i]:02X} vs {blob[i]:02X}"); break
