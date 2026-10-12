# -*- coding: utf-8 -*-
"""RAMMap 字符串定位器：提取可汉化的宽字符串及其文件偏移、所属节、可用空间。"""
import pefile, re, json, sys, os

# 可用于追溯字符串起点的宽字符（字符串内部的合法字符）
INNER = set(range(0x20, 0x7f)) | {0x09}

def section_of(off, sections):
    for name, va, praw, rawsize, vsize in sections:
        if praw <= off < praw + rawsize:
            return name, va, praw
    return None, None, None

def extract(path):
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories()
    data = pe.__data__
    sections = []
    for s in pe.sections:
        sections.append((s.Name.rstrip(b'\x00').decode('latin1'),
                         s.VirtualAddress, s.PointerToRawData,
                         s.SizeOfRawData, s.Misc_VirtualSize))
    secmap = {n: (va, praw, vs) for n, va, praw, rs, vs in sections}

    # 匹配 >=2 个连续的可打印宽字符（含制表符）
    pat = re.compile(rb'(?:[\x09\x20-\x7e]\x00){2,}')
    strings = []
    for m in pat.finditer(data):
        start = m.start()
        end = m.end()  # 指向最后一个字符之后
        # 向后追溯真实起点：前一码元若仍是字符串内部字符，说明正则从一个更长串的中间开始
        s2 = start
        while s2 >= 2:
            prev_lo = data[s2-2]
            prev_hi = data[s2-1]
            if prev_hi == 0 and prev_lo in INNER:
                s2 -= 2
            else:
                break
        # 校验起点：前一码元若是字符串内部字符，说明匹配从某个更长字符串中间开始
        # （资源模板里的字符串前缀多为二进制结构字段，hi 字节非 0，属合法起点）
        ok_start = True
        if s2 >= 2:
            if data[s2-1] == 0 and data[s2-2] in INNER:
                ok_start = False
        # 校验终点：必须紧跟 0x0000
        ok_end = data[end:end+2] == b'\x00\x00'
        name, va, praw = section_of(s2, sections)
        txt = data[s2:end].decode('utf-16-le')
        rec = dict(file_off=s2, sec=name, rva=(va + s2 - praw) if va is not None else None,
                   en=txt, blen=end - s2, ok_start=ok_start, ok_end=ok_end)
        strings.append(rec)

    # 合并统计重复
    seen = {}
    for r in strings:
        key = r['en']
        if key not in seen:
            seen[key] = dict(en=key, blen=r['blen'], occ=[], secs=set(), bad=False)
        seen[key]['occ'].append(r['file_off'])
        seen[key]['secs'].add(r['sec'])
        if not (r['ok_start'] and r['ok_end']):
            seen[key]['bad'] = True
    out = []
    for k, v in sorted(seen.items()):
        out.append(dict(en=k, blen=v['blen'], count=len(v['occ']),
                        offs=v['occ'], secs=sorted(v['secs'], key=lambda x: (x is None, x)), bad_boundary=v['bad']))
    return out, sections, len(data)

if __name__ == '__main__':
    for exe in sys.argv[1:]:
        lst, sections, size = extract(exe)
        base = os.path.splitext(os.path.basename(exe))[0]
        with open(base + '_strings.json', 'w', encoding='utf-8') as f:
            json.dump(lst, f, ensure_ascii=False, indent=1)
        print(f"{exe}: {size} bytes, sections={[s[0] for s in sections]}, {len(lst)} unique strings")
        # 统计各节数量
        from collections import Counter
        c = Counter()
        for r in lst:
            c[tuple(r['secs'])] += 1
        for k, v in c.most_common():
            print('   secs', k, '->', v)
