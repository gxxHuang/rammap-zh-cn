# -*- coding: utf-8 -*-
"""从 translations.py 生成 C# 数据文件（UTF-8 BOM）。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from translations import MENU_TABLE, STR_TABLE

def cs_str(s):
    out = []
    for ch in s:
        if ch == '\\': out.append('\\\\')
        elif ch == '"': out.append('\\"')
        elif ch == '\r': out.append('\\r')
        elif ch == '\n': out.append('\\n')
        elif ch == '\t': out.append('\\t')
        elif ord(ch) < 0x20: out.append(f'\\u{ord(ch):04x}')
        else: out.append(ch)
    return '"' + ''.join(out) + '"'

lines = []
lines.append('// 本文件由 tools/gen_csharp_data.py 自动生成，请勿手工修改。')
lines.append('using System.Collections.Generic;')
lines.append('')
lines.append('namespace RamMapZh')
lines.append('{')
lines.append('    internal static class PatchData')
lines.append('    {')
lines.append('        /// <summary>菜单文本（整表重排，可加长，保留 Alt 加速键）</summary>')
lines.append('        public static readonly Dictionary<string, string> MenuTable = new Dictionary<string, string>')
lines.append('        {')
for k, v in MENU_TABLE.items():
    lines.append(f'            {{ {cs_str(k)}, {cs_str(v)} }},')
lines.append('        };')
lines.append('')
lines.append('        /// <summary>其它界面字符串（原地等长替换）</summary>')
lines.append('        public static readonly Dictionary<string, string> StrTable = new Dictionary<string, string>')
lines.append('        {')
for k, v in STR_TABLE.items():
    lines.append(f'            {{ {cs_str(k)}, {cs_str(v)} }},')
lines.append('        };')
lines.append('    }')
lines.append('}')
lines.append('')

out = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'patcher', 'PatchData.cs'))
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, 'w', encoding='utf-8-sig', newline='\r\n') as f:
    f.write('\n'.join(lines))
print("written:", out)
print("menu entries:", len(MENU_TABLE), "| str entries:", len(STR_TABLE))
