# -*- coding: utf-8 -*-
"""动态实测：用去掉提权要求的测试副本启动 RAMMap，枚举窗口/菜单/控件验证中文。"""
import ctypes, ctypes.wintypes as wt, subprocess, time, sys, os, shutil

u32 = ctypes.WinDLL('user32', use_last_error=True)
k32 = ctypes.WinDLL('kernel32', use_last_error=True)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = ROOT
TESTDIR = os.path.join(BASE, 'out', 'test')

def make_test_copy():
    os.makedirs(TESTDIR, exist_ok=True)
    src = os.path.join(BASE, 'out', '汉化版', 'RAMMap64.exe')
    dst = os.path.join(TESTDIR, 'RAMMap64_test.exe')
    data = bytearray(open(src, 'rb').read())
    old = b'level="requireAdministrator"'
    new = b'           level="asInvoker"'   # 用空格填充保持字节长度（属性间空白合法）
    assert len(old) == len(new), (len(old), len(new))
    n = data.count(old)
    print(f"manifest level 字段出现 {n} 次")
    data = data.replace(old, new)
    # 校验修改后 manifest 仍是合法 XML
    import xml.etree.ElementTree as ET
    import pefile
    open(dst, 'wb').write(bytes(data))
    pe = pefile.PE(dst, fast_load=True); pe.parse_data_directories()
    for r in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        tn = r.name.string.decode() if r.name else pefile.RESOURCE_TYPE.get(r.struct.Id, str(r.struct.Id))
        if tn != 'RT_MANIFEST': continue
        for l in r.directory.entries:
            for d in l.directory.entries:
                off = pe.get_offset_from_rva(d.data.struct.OffsetToData)
                blob = pe.__data__[off:off+d.data.struct.Size]
                ET.fromstring(blob.decode('utf-8'))
                print("manifest XML 校验通过, asInvoker:", b'asInvoker' in blob)
    print("测试副本:", dst)
    return dst

def get_windows(pid):
    res = []
    EnumProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    u32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
    def cb(hwnd, lp):
        p = wt.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid:
            cls = ctypes.create_unicode_buffer(256); u32.GetClassNameW(hwnd, cls, 256)
            txt = ctypes.create_unicode_buffer(512); u32.GetWindowTextW(hwnd, txt, 512)
            res.append((hwnd, cls.value, txt.value))
        return True
    u32.EnumWindows(EnumProc(cb), 0)
    return res

def get_children(hwnd):
    res = []
    EnumProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(h, lp):
        cls = ctypes.create_unicode_buffer(256); u32.GetClassNameW(h, cls, 256)
        txt = ctypes.create_unicode_buffer(512); u32.GetWindowTextW(h, txt, 512)
        cid = u32.GetDlgCtrlID(h)
        res.append((h, cls.value, txt.value, cid))
        return True
    u32.EnumChildWindows(hwnd, EnumProc(cb), 0)
    return res

def dump_menu(hwnd):
    u32.GetMenu.restype = wt.HMENU
    hm = u32.GetMenu(hwnd)
    if not hm: return None
    out = []
    def walk(m, d=0):
        n = u32.GetMenuItemCount(m)
        for i in range(n):
            b = ctypes.create_unicode_buffer(256)
            u32.GetMenuStringW(m, i, b, 256, 0x400)
            sub = u32.GetSubMenu(m, i)
            out.append('  '*d + (repr(b.value) if b.value else '<sep>'))
            if sub: walk(sub, d+1)
    walk(hm)
    return out

def dump_tabs(hwnd):
    """找 SysTabControl32 并读取所有标签"""
    TCM_GETITEMCOUNT = 0x1304
    TCM_GETITEMW = 0x133C
    found = []
    for h, cls, txt, cid in get_children(hwnd):
        if cls != 'SysTabControl32':
            continue
        cnt = u32.SendMessageW(h, TCM_GETITEMCOUNT, 0, 0)
        items = []
        for i in range(cnt):
            class TCITEM(ctypes.Structure):
                _fields_ = [('mask', wt.UINT), ('dwState', wt.DWORD), ('dwStateMask', wt.DWORD),
                            ('pszText', ctypes.c_void_p), ('cchTextMax', ctypes.c_int),
                            ('iImage', ctypes.c_int), ('lParam', ctypes.c_void_p)]
            buf = ctypes.create_unicode_buffer(256)
            item = TCITEM()
            item.mask = 0x0001 | 0x0004 | 0x0008  # TCIF_TEXT|TCIF_IMAGE|TCIF_PARAM
            item.pszText = ctypes.cast(buf, ctypes.c_void_p)
            item.cchTextMax = 256
            res = u32.SendMessageW(h, TCM_GETITEMW, i, ctypes.byref(item))
            items.append(buf.value)
        found.append(items)
    return found

def main():
    exe = make_test_copy()
    print("启动测试副本...")
    p = subprocess.Popen([exe, '-accepteula'], cwd=TESTDIR)
    print("pid:", p.pid)
    seen = {}
    deadline = time.time() + 12
    while time.time() < deadline:
        wins = get_windows(p.pid)
        for h, cls, txt in wins:
            if (h, cls) in seen: continue
            seen[(h, cls)] = True
            print(f"\n>>> 窗口 hwnd={h} class={cls!r} title={txt!r}")
            menu = dump_menu(h)
            if menu:
                print("    菜单:")
                for line in menu: print("      ", line)
            tabs = dump_tabs(h)
            for items in tabs:
                print("    Tab 标签:", items)
            kids = get_children(h)
            if kids:
                print("    子控件:")
                for hh, c, t, cid in kids[:25]:
                    if t:
                        print(f"      [{c} id={cid}] {t!r}")
        if p.poll() is not None and not wins:
            break
        time.sleep(1.0)
    alive = p.poll() is None
    print("\n进程是否仍在运行:", alive, "| exit code:", p.poll())
    if alive:
        p.terminate()
        try: p.wait(timeout=3)
        except Exception: p.kill()
        print("已终止测试进程")

if __name__ == '__main__':
    main()
