# -*- coding: utf-8 -*-
"""RAMMap 汉化补丁生成器。

流程：
  1. 定位并重排菜单资源（RT_MENU/MAIN_MENU）→ 中文菜单模板
  2. 精确替换对话框资源与代码数据段中的界面字符串（等长，NUL/空格填充）
  3. 输出汉化版 exe + 补丁报告

安全约束：
  - 绝不触碰 .text 代码段
  - 每个替换都做"完整字符串"边界校验（前缀/后缀不算）
  - 译文长度不得超过原文
"""
import sys, os, json, struct
import pefile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from menu_tool import parse_menu, gen_menu
from translations import MENU_TABLE, STR_TABLE

INNER = set(range(0x01, 0x80))   # 所有 ASCII（含控制字符）都视为"可能是字符串内容"
CODE_SECS = {'.text'}


def load_pe(path):
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories()
    sections = []
    for s in pe.sections:
        sections.append((s.Name.rstrip(b'\x00').decode('latin1'),
                         s.VirtualAddress, s.PointerToRawData, s.SizeOfRawData))
    resblocks = {}
    for r in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        tn = r.name.string.decode() if r.name else pefile.RESOURCE_TYPE.get(r.struct.Id, str(r.struct.Id))
        lst = []
        for l in r.directory.entries:
            key = l.name.string.decode() if l.name else l.id
            for d in l.directory.entries:
                off = pe.get_offset_from_rva(d.data.struct.OffsetToData)
                lst.append((key, off, d.data.struct.Size))
        resblocks[tn] = lst
    return pe, sections, resblocks


def section_of(off, sections):
    for name, va, praw, rawsize in sections:
        if praw <= off < praw + rawsize:
            return name
    return None


def translate_menu(items, table, report):
    for it in items:
        txt = it['text']
        if txt in table:
            it['text'] = table[txt]
            report['menu_hits'].append((txt, table[txt]))
        elif txt and not (it['flags'] & 0x10) and txt.strip() == '':
            pass  # 分隔符
        elif txt:
            report['menu_miss'].append(txt)
        if 'sub' in it:
            translate_menu(it['sub'], table, report)


def boundary_ok(data, pos, blen):
    """校验 pos 处是完整字符串：
       - 前一个码元若是 ASCII 字符（含控制字符），说明命中处是某长串的后缀 → 拒绝
       - 命中处之后必须紧跟 NUL（字符串结尾）
       - 命中处之前是 NUL 或非 ASCII 数据（资源结构字段）→ 视为字符串开头
    """
    if pos >= 2:
        hi, lo = data[pos - 1], data[pos - 2]
        if hi == 0 and lo in INNER:
            return False
    if data[pos + blen:pos + blen + 2] != b'\x00\x00':
        return False
    return True


def build(src, dst):
    pe, sections, resblocks = load_pe(src)
    orig = bytes(pe.__data__)
    data = bytearray(orig)
    report = {'src': src, 'dst': dst, 'menu_hits': [], 'menu_miss': [],
              'str_hits': [], 'str_miss': [], 'errors': [], 'warnings': [], 'skipped': []}

    # ---------- 1. 菜单 ----------
    menu_blocks = resblocks.get('RT_MENU', [])
    for key, off, size in menu_blocks:
        blob = orig[off:off + size]
        try:
            items, consumed = parse_menu(blob)
        except Exception as e:
            report['errors'].append(f'menu parse fail {key}: {e}')
            continue
        translate_menu(items, MENU_TABLE, report)
        newblob = gen_menu(items)
        if len(newblob) > size:
            report['errors'].append(f'menu too big: {key} {len(newblob)} > {size}')
            continue
        data[off:off + len(newblob)] = newblob
        data[off + len(newblob):off + size] = b'\x00' * (size - len(newblob))
        report.setdefault('menu_blocks', []).append(
            {'key': str(key), 'off': off, 'old_size': size, 'new_size': len(newblob)})

    # ---------- 2. 对话框资源范围 ----------
    dialog_ranges = [(off, size) for _, off, size in resblocks.get('RT_DIALOG', [])]

    def in_dialog(pos):
        for o, s in dialog_ranges:
            if o <= pos < o + s:
                return True
        return False

    # ---------- 3. 字符串替换 ----------
    for en, zh in STR_TABLE.items():
        pat = en.encode('utf-16-le')
        zhb = zh.encode('utf-16-le')
        if len(zhb) > len(pat):
            report['errors'].append(f'译文过长: {en!r} -> {zh!r} ({len(zhb)}B > {len(pat)}B)')
            continue
        hits = 0
        start = 0
        while True:
            pos = orig.find(pat, start)
            if pos < 0:
                break
            start = pos + 2
            if not boundary_ok(orig, pos, len(pat)):
                continue
            sec = section_of(pos, sections)
            if sec in CODE_SECS:
                report['warnings'].append(f'跳过代码段命中: {en!r} @0x{pos:X}')
                continue
            if in_dialog(pos):
                pad = (len(pat) - len(zhb)) // 2
                newb = zhb + b'\x20\x00' * pad          # 尾部空格填充（保持字符数）
            else:
                newb = zhb + b'\x00' * (len(pat) - len(zhb))  # NUL 填充
            assert len(newb) == len(pat)
            data[pos:pos + len(pat)] = newb
            hits += 1
            report['str_hits'].append({'en': en, 'zh': zh, 'off': f'0x{pos:X}',
                                       'sec': sec, 'size': len(pat), 'fill': 'space' if in_dialog(pos) else 'nul'})
        if hits == 0:
            report['str_miss'].append(en)

    with open(dst, 'wb') as f:
        f.write(bytes(data))
    return report


if __name__ == '__main__':
    # 用法: python build_patch.py [原始exe目录] [输出目录]
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'rammap_src')
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'out', '汉化版')
    os.makedirs(out_dir, exist_ok=True)
    all_reports = []
    for name in ['RAMMap64.exe', 'RAMMap.exe', 'RAMMap64a.exe']:
        src = os.path.join(src_dir, name)
        if not os.path.exists(src):
            print(f"跳过 {name}（不存在）")
            continue
        rep = build(src, os.path.join(out_dir, name))
        all_reports.append(rep)
        print(f"\n########## {name} ##########")
        print(f"  菜单块: {rep.get('menu_blocks')}")
        print(f"  菜单命中 {len(rep['menu_hits'])} 条, 未译: {rep['menu_miss']}")
        print(f"  字符串命中: {len(rep['str_hits'])} 处")
        if rep['str_miss']:
            print(f"  未找到({len(rep['str_miss'])}): {rep['str_miss']}")
        if rep['errors']:
            print(f"  !! 错误({len(rep['errors'])}): {rep['errors']}")
        if rep['warnings']:
            print(f"  ?? 警告({len(rep['warnings'])}): {rep['warnings']}")
    report_path = os.path.join(os.path.dirname(out_dir), 'patch_report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(all_reports, f, ensure_ascii=False, indent=1)
    print(f"\n报告已保存: {report_path}")
