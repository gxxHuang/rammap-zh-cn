# -*- coding: utf-8 -*-
"""GUI 端到端测试：启动汉化工具 → 点「汉化」→ 校验哈希 → 点「还原原版」→ 校验哈希。"""
import ctypes, ctypes.wintypes as wt, subprocess, time, os, hashlib, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, 'out', 'gui_test')
TOOL = os.path.join(BASE, 'RAMMap汉化工具.exe')
TARGETS = ['RAMMap64.exe', 'RAMMap.exe', 'RAMMap64a.exe']
ZH_DIR = os.path.join(ROOT, 'out', '汉化版')

u32 = ctypes.WinDLL('user32', use_last_error=True)
u32.SendMessageW.argtypes = [wt.HWND, wt.UINT, ctypes.c_size_t, ctypes.c_ssize_t]
u32.SendMessageW.restype = ctypes.c_ssize_t
u32.EnumChildWindows.argtypes = [wt.HWND, ctypes.c_void_p, wt.LPARAM]
u32.EnumWindows.argtypes = [ctypes.c_void_p, wt.LPARAM]

BM_CLICK = 0x00F5
WM_CLOSE = 0x0010


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def enum_children(hwnd):
    out = []
    EnumProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def cb(h, lp):
        cls = ctypes.create_unicode_buffer(256); u32.GetClassNameW(h, cls, 256)
        txt = ctypes.create_unicode_buffer(1024); u32.GetWindowTextW(h, txt, 1024)
        out.append((h, cls.value, txt.value))
        return True
    u32.EnumChildWindows(hwnd, EnumProc(cb), 0)
    return out


def find_main(timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        found = []
        EnumProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

        def cb(h, lp):
            txt = ctypes.create_unicode_buffer(512); u32.GetWindowTextW(h, txt, 512)
            if 'RAMMap 汉化工具' in txt.value:
                found.append(h)
            return True
        u32.EnumWindows(EnumProc(cb), 0)
        if found:
            return found[0]
        time.sleep(0.5)
    return None


def find_btn(hwnd, keyword):
    for h, cls, txt in enum_children(hwnd):
        if cls == 'WindowsForms10.BUTTON' or 'BUTTON' in cls.upper() or cls == 'Button':
            if keyword in txt:
                return h, txt
    # 兜底：任何控件含关键词
    for h, cls, txt in enum_children(hwnd):
        if keyword in txt and '汉化工具' not in txt:
            return h, txt
    return None, None


def main():
    orig = {t: sha(os.path.join(BASE, t)) for t in TARGETS}
    zh = {t: sha(os.path.join(ZH_DIR, t)) for t in TARGETS}
    print("原始哈希已记录，汉化版参考哈希已记录")

    print("启动工具 GUI ...")
    p = subprocess.Popen([TOOL], cwd=BASE)
    hwnd = find_main()
    if not hwnd:
        print("!! 未找到工具窗口"); p.terminate(); return
    print("工具窗口 hwnd =", hwnd)
    time.sleep(1.5)  # 等待自动扫描完成

    kids = enum_children(hwnd)
    print(f"子控件 {len(kids)} 个：")
    for h, c, t in kids:
        if t:
            print(f"   [{c.split('.')[-1]:10s}] {t!r}")

    # 找状态列（验证扫描结果）——通过读取 ListView 行
    # 1) 点击「汉化」
    btn, label = find_btn(hwnd, '汉化')
    print(f"\n找到汉化按钮: hwnd={btn} 文本={label!r}")
    if not btn:
        p.terminate(); return
    u32.SendMessageW(hwnd, 0x0006, 1, 0)  # WM_ACTIVATE
    u32.PostMessageW(btn, BM_CLICK, 0, 0)
    time.sleep(3)

    ok = True
    print("\n--- 汉化后哈希校验 ---")
    for t in TARGETS:
        cur = sha(os.path.join(BASE, t))
        state = "✓ 与汉化版一致" if cur == zh[t] else ("= 未变化(原版)" if cur == orig[t] else "? 未知")
        if cur != zh[t]:
            ok = False
        print(f"  {t}: {state}")
    print("备份文件:", [f for f in os.listdir(BASE) if f.endswith('.zhbak')])

    # 2) 点击「还原原版」
    btn2, label2 = find_btn(hwnd, '还原')
    print(f"\n找到还原按钮: hwnd={btn2} 文本={label2!r}")
    if btn2:
        u32.PostMessageW(btn2, BM_CLICK, 0, 0)
        time.sleep(3)
        print("--- 还原后哈希校验 ---")
        for t in TARGETS:
            cur = sha(os.path.join(BASE, t))
            state = "✓ 与原版一致" if cur == orig[t] else "✗ 不一致"
            if cur != orig[t]:
                ok = False
            print(f"  {t}: {state}")

    # 3) 关闭
    u32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
    time.sleep(1)
    if p.poll() is None:
        p.terminate()
    print("\n=== 测试结果:", "全部通过 ✓" if ok else "存在失败 ✗", "===")


if __name__ == '__main__':
    main()
