# -*- coding: utf-8 -*-
"""校验翻译表：每一项必须匹配文件中的完整字符串（不被截断）。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from translations import MENU_TABLE, STR_TABLE

# 字符串内部字符：所有 0x01-0x7F（含控制字符 \t \r \n），以及 >0x7F 的非零码元（拉丁扩展/中文等）
def is_inner(hi, lo):
    return not (hi == 0 and lo == 0)

def full_string_at(data, pos):
    s = pos
    while s >= 2:
        hi, lo = data[s-1], data[s-2]
        if hi == 0 and lo == 0:
            break
        if hi == 0 and lo in (0x00,):
            break
        # 前一个码元非 NUL → 可能是字符串内容，继续前移
        s -= 2
    e = pos
    while data[e:e+2] != b'\x00\x00':
        e += 2
    return s, data[s:e]

def check(path, table, name):
    data = open(path, 'rb').read()
    print(f"===== {name} @ {os.path.basename(path)} =====")
    for en in table:
        pat = en.encode('utf-16-le')
        idx = 0
        found = 0
        mismatch = []
        while True:
            pos = data.find(pat, idx)
            if pos < 0: break
            idx = pos + 2
            s, full = full_string_at(data, pos)
            if s == pos and full == pat:
                found += 1
            else:
                try:
                    ftxt = full.decode('utf-16-le')
                except Exception:
                    ftxt = repr(full)
                mismatch.append((pos, s, ftxt))
        if found == 0:
            print(f"  [MISS] {en!r}")
            for pos, s, ftxt in mismatch[:2]:
                print(f"         部分匹配@{pos:#x} 完整串({s:#x}): {ftxt!r}")
        elif mismatch:
            print(f"  [PART] {en!r} 命中{found}处，另有{len(mismatch)}处是部分匹配")

if __name__ == '__main__':
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'rammap_src')
    check(os.path.join(src, 'RAMMap64.exe'), STR_TABLE, 'STR_TABLE')
