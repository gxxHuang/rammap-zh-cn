# -*- coding: utf-8 -*-
"""汉化版验证：PE 结构、代码段未改动、菜单/对话框资源可被 Windows API 正确解析。"""
import ctypes, ctypes.wintypes as wt, hashlib, sys, os
import pefile

u32 = ctypes.WinDLL('user32', use_last_error=True)
k32 = ctypes.WinDLL('kernel32', use_last_error=True)
LOAD_LIBRARY_AS_DATAFILE = 0x2


def section_map(pe):
    m = {}
    for s in pe.sections:
        name = s.Name.rstrip(b'\x00').decode('latin1')
        m[name] = (s.PointerToRawData, s.SizeOfRawData)
    return m


def load_menu_text(path, resname):
    k32.LoadLibraryExW.restype = wt.HMODULE
    h = k32.LoadLibraryExW(path, None, LOAD_LIBRARY_AS_DATAFILE)
    if not h:
        return None, f"LoadLibraryEx failed: {k32.GetLastError()}"
    u32.LoadMenuW.restype = wt.HMENU
    hm = u32.LoadMenuW(h, resname)
    if not hm:
        return None, f"LoadMenu failed: {k32.GetLastError()}"
    out = []
    def dump(menu, depth=0):
        n = u32.GetMenuItemCount(menu)
        for i in range(n):
            buf = ctypes.create_unicode_buffer(512)
            u32.GetMenuStringW(menu, i, buf, 512, 0x400)
            mid = u32.GetMenuItemID(menu, i)
            sub = u32.GetSubMenu(menu, i)
            out.append('    ' * depth + f"{(buf.value or '<sep>')!r} id=0x{mid & 0xFFFFFFFF:X}")
            if sub:
                dump(sub, depth + 1)
    dump(hm)
    u32.DestroyMenu(hm)
    k32.FreeLibrary(h)
    return out, None


def dump_dialog_texts(path):
    """用 LoadLibraryEx 加载，解析 DLGTEMPLATEEX 提取所有控件文本。"""
    k32.LoadLibraryExW.restype = wt.HMODULE
    k32.FindResourceW.restype = wt.HANDLE
    k32.FindResourceW.argtypes = [wt.HMODULE, wt.LPCWSTR, wt.LPCWSTR]
    k32.LoadResource.restype = wt.HANDLE
    k32.LoadResource.argtypes = [wt.HMODULE, wt.HANDLE]
    k32.LockResource.restype = ctypes.c_void_p
    k32.LockResource.argtypes = [wt.HANDLE]
    k32.SizeofResource.restype = wt.DWORD
    k32.SizeofResource.argtypes = [wt.HMODULE, wt.HANDLE]
    h = k32.LoadLibraryExW(path, None, LOAD_LIBRARY_AS_DATAFILE)
    results = {}
    names = ['ABOUT', 'ADD_DIALOG', 'LISTVIEWFILTER_TAB', 'LISTVIEWGRAPH_TAB', 'LISTVIEW_TAB',
             'MAIN_WINDOW', 'PROGRESS', 'SUMMARY_TAB', 'TREELIST_TAB', 'USAGE']
    for nm in names:
        try:
            hr = k32.FindResourceW(h, nm, ctypes.c_wchar_p(5))
            if not hr:
                results[nm] = ['<FindResource failed>']
                continue
            hl = k32.LoadResource(h, hr)
            size = k32.SizeofResource(h, hr)
            ptr = k32.LockResource(hl)
            b = ctypes.string_at(ptr, size)
            results[nm] = parse_dlg_texts(b)
        except Exception as e:
            results[nm] = [f'<parse error {e}>']
    k32.FreeLibrary(h)
    return results


def parse_dlg_texts(b):
    import struct
    out = []
    dlgver, sig = struct.unpack('<HH', b[0:4])
    if sig == 0xFFFF:
        style = struct.unpack('<I', b[12:16])[0]
        cdit = struct.unpack('<H', b[16:18])[0]
        pos = 26
    else:
        style = struct.unpack('<I', b[0:4])[0]
        cdit = struct.unpack('<H', b[8:10])[0]
        pos = 18
    def rd_str(p):
        e = p
        while b[e:e+2] != b'\x00\x00':
            e += 2
        return b[p:e].decode('utf-16-le'), e + 2
    def rd_name(p):
        w = struct.unpack('<H', b[p:p+2])[0]
        if w == 0: return '(none)', p + 2
        if w == 0xFFFF: return f'#{struct.unpack("<H", b[p+2:p+4])[0]}', p + 4
        return rd_str(p)
    menu, pos = rd_name(pos)
    cls, pos = rd_name(pos)
    title, pos = rd_str(pos)
    out.append(f'<title> {title!r}')
    if style & 0x40:
        pts = struct.unpack('<H', b[pos:pos+2])[0]; pos += 2
        if dlgver == 1: pos += 4
        fname, pos = rd_str(pos)
    for _ in range(cdit):
        while pos % 4: pos += 1
        exstyle, style2 = struct.unpack('<II', b[pos+4:pos+12]); pos += 12
        pos += 8
        cid = struct.unpack('<I' if dlgver == 1 else '<H', b[pos:pos+(4 if dlgver == 1 else 2)])[0]
        pos += 4 if dlgver == 1 else 2
        cls2, pos = rd_name(pos)
        t2, pos = rd_str(pos)
        extra = struct.unpack('<H', b[pos:pos+2])[0]; pos += 2 + extra
        if t2:
            out.append(f'<{cls2} id={cid}> {t2!r}')
    return out


if __name__ == '__main__':
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'rammap_src')
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'out', '汉化版')
    for name in ['RAMMap64.exe', 'RAMMap.exe', 'RAMMap64a.exe']:
        p_src = os.path.join(src_dir, name)
        p_out = os.path.join(out_dir, name)
        print(f"\n{'='*70}\n### {name}\n{'='*70}")
        # --- 1. PE 结构 ---
        try:
            pe = pefile.PE(p_out)
            print("PE ok:", pe.FILE_HEADER.Machine == pefile.PE(p_src).FILE_HEADER.Machine,
                  "| sections:", [s.Name.rstrip(b'\x00').decode() for s in pe.sections])
        except Exception as e:
            print("!! PE 解析失败:", e)
            continue
        # --- 2. 代码段未改 ---
        a = open(p_src, 'rb').read()
        b = open(p_out, 'rb').read()
        sm = section_map(pefile.PE(p_src, fast_load=True))
        for sec in ['.text', '.pdata', '.reloc']:
            if sec in sm:
                off, size = sm[sec]
                same = hashlib.sha256(a[off:off+size]).hexdigest() == hashlib.sha256(b[off:off+size]).hexdigest()
                print(f"  {sec} 未改动: {same}")
        # 差异统计
        diff = sum(1 for x, y in zip(a, b) if x != y)
        print(f"  文件大小 {len(a)} -> {len(b)} (差异字节数: {diff})")
        # --- 3. 菜单 ---
        texts, err = load_menu_text(p_out, "MAIN_MENU")
        if err:
            print("  !! 菜单加载失败:", err)
        else:
            print("  --- 载入后的菜单 ---")
            for t in texts:
                print("   ", t)
        # --- 4. 对话框 ---
        dlgs = dump_dialog_texts(p_out)
        for nm, lines in dlgs.items():
            if any(ch for line in lines for ch in line if '\u4e00' <= ch <= '\u9fff'):
                print(f"  --- 对话框 {nm} ---")
                for line in lines:
                    print("   ", line)
