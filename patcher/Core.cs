// RAMMap 汉化工具 - 核心逻辑（PE 解析 / 菜单编解码 / 字符串补丁）
// 只替换界面字符串数据，不触碰 .text 代码段，不修改程序逻辑。
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace RamMapZh
{
    internal sealed class SectionInfo
    {
        public string Name = "";
        public uint VirtualAddress;
        public uint VirtualSize;
        public int PointerToRawData;
        public int SizeOfRawData;
    }

    internal sealed class ResEntry
    {
        public uint TypeId;
        public string Name = "";
        public int Offset;
        public int Size;
    }

    /// <summary>最小 PE 解析器：节表 / 资源目录 / RVA 转换。</summary>
    internal sealed class PeImage
    {
        public byte[] Data = Array.Empty<byte>();
        public readonly List<SectionInfo> Sections = new List<SectionInfo>();
        public readonly List<ResEntry> Resources = new List<ResEntry>();
        public bool Valid;
        private int resBase;

        public static PeImage Parse(byte[] data)
        {
            var pe = new PeImage { Data = data };
            try { pe.ParseInternal(); pe.Valid = true; }
            catch { pe.Valid = false; }
            return pe;
        }

        private void ParseInternal()
        {
            if (Data.Length < 0x40 || Data[0] != 'M' || Data[1] != 'Z')
                throw new InvalidDataException("not MZ");
            int lfanew = BitConverter.ToInt32(Data, 0x3C);
            if (lfanew <= 0 || lfanew + 24 > Data.Length ||
                Data[lfanew] != 'P' || Data[lfanew + 1] != 'E')
                throw new InvalidDataException("not PE");
            int coff = lfanew + 4;
            int numSections = BitConverter.ToUInt16(Data, coff + 2);
            int optSize = BitConverter.ToUInt16(Data, coff + 16);
            int opt = coff + 20;
            ushort magic = BitConverter.ToUInt16(Data, opt);
            bool pe32plus = magic == 0x20B;

            int secTable = opt + optSize;
            for (int i = 0; i < numSections; i++)
            {
                int s = secTable + i * 40;
                if (s + 40 > Data.Length) break;
                Sections.Add(new SectionInfo
                {
                    Name = Encoding.ASCII.GetString(Data, s, 8).TrimEnd('\0'),
                    VirtualSize = BitConverter.ToUInt32(Data, s + 8),
                    VirtualAddress = BitConverter.ToUInt32(Data, s + 12),
                    SizeOfRawData = BitConverter.ToInt32(Data, s + 16),
                    PointerToRawData = BitConverter.ToInt32(Data, s + 20),
                });
            }

            int dd = opt + (pe32plus ? 0x70 : 0x60);
            uint resRva = BitConverter.ToUInt32(Data, dd + 16);
            if (resRva != 0)
            {
                resBase = RvaToOff(resRva);
                if (resBase >= 0) WalkRes(resBase, 0, 0, "");
            }
        }

        public int RvaToOff(uint rva)
        {
            foreach (var s in Sections)
            {
                uint size = Math.Max(s.VirtualSize, (uint)s.SizeOfRawData);
                if (rva >= s.VirtualAddress && rva < s.VirtualAddress + size)
                    return s.PointerToRawData + (int)(rva - s.VirtualAddress);
            }
            return -1;
        }

        public string SectionOf(int fileOff)
        {
            foreach (var s in Sections)
                if (fileOff >= s.PointerToRawData && fileOff < s.PointerToRawData + s.SizeOfRawData)
                    return s.Name;
            return "";
        }

        private void WalkRes(int dirOff, int level, uint typeId, string itemName)
        {
            if (dirOff < 0 || dirOff + 16 > Data.Length) return;
            int named = BitConverter.ToUInt16(Data, dirOff + 12);
            int ids = BitConverter.ToUInt16(Data, dirOff + 14);
            int total = named + ids;
            for (int i = 0; i < total; i++)
            {
                int e = dirOff + 16 + i * 8;
                if (e + 8 > Data.Length) return;
                uint nameField = BitConverter.ToUInt32(Data, e);
                uint offField = BitConverter.ToUInt32(Data, e + 4);

                string entryName;
                if ((nameField & 0x80000000) != 0)
                {
                    int strOff = resBase + (int)(nameField & 0x7FFFFFFF);
                    if (strOff + 2 > Data.Length) return;
                    int len = BitConverter.ToUInt16(Data, strOff);
                    entryName = (len > 0 && strOff + 2 + len * 2 <= Data.Length)
                        ? Encoding.Unicode.GetString(Data, strOff + 2, len * 2) : "";
                }
                else entryName = nameField.ToString();

                if ((offField & 0x80000000) != 0)
                {
                    int sub = resBase + (int)(offField & 0x7FFFFFFF);
                    if (level == 0) WalkRes(sub, 1, nameField, "");
                    else if (level == 1) WalkRes(sub, 2, typeId, entryName);
                }
                else if (level == 2)
                {
                    int de = resBase + (int)offField;
                    if (de + 16 > Data.Length) return;
                    uint dataRva = BitConverter.ToUInt32(Data, de);
                    int size = BitConverter.ToInt32(Data, de + 4);
                    int off = RvaToOff(dataRva);
                    if (off >= 0 && size > 0 && off + size <= Data.Length)
                        Resources.Add(new ResEntry { TypeId = typeId, Name = itemName, Offset = off, Size = size });
                }
            }
        }
    }

    internal sealed class MenuItem
    {
        public ushort Flags;
        public ushort Id;
        public string Text = "";
        public List<MenuItem> Sub;   // 非 null 表示 popup
    }

    /// <summary>RAMMap 菜单模板编解码（格式经实测确认：header 4B；popup 项无 ID 字段）。</summary>
    internal static class MenuCodec
    {
        private const ushort MF_POPUP = 0x0010;
        private const ushort MF_END = 0x0080;

        public static List<MenuItem> Parse(byte[] b)
        {
            if (b.Length < 4) throw new InvalidDataException("menu too small");
            int pos = 4;
            return ParseLevel(b, ref pos);
        }

        private static List<MenuItem> ParseLevel(byte[] b, ref int pos)
        {
            var items = new List<MenuItem>();
            while (true)
            {
                if (pos + 2 > b.Length) throw new InvalidDataException("menu truncated");
                ushort flags = BitConverter.ToUInt16(b, pos); pos += 2;
                var it = new MenuItem { Flags = flags };
                if ((flags & MF_POPUP) != 0)
                {
                    it.Text = ReadStr(b, ref pos);
                    it.Sub = ParseLevel(b, ref pos);
                }
                else
                {
                    if (pos + 2 > b.Length) throw new InvalidDataException("menu truncated");
                    it.Id = BitConverter.ToUInt16(b, pos); pos += 2;
                    it.Text = ReadStr(b, ref pos);
                }
                items.Add(it);
                if ((flags & MF_END) != 0) break;
            }
            return items;
        }

        private static string ReadStr(byte[] b, ref int pos)
        {
            int s = pos;
            while (pos + 1 < b.Length && !(b[pos] == 0 && b[pos + 1] == 0)) pos += 2;
            string r = Encoding.Unicode.GetString(b, s, pos - s);
            pos += 2;
            return r;
        }

        public static byte[] Generate(List<MenuItem> items)
        {
            using (var ms = new MemoryStream())
            {
                ms.WriteByte(0); ms.WriteByte(0); ms.WriteByte(0); ms.WriteByte(0);
                GenLevel(items, ms);
                return ms.ToArray();
            }
        }

        private static void GenLevel(List<MenuItem> items, MemoryStream ms)
        {
            for (int i = 0; i < items.Count; i++)
            {
                var it = items[i];
                ushort flags = it.Flags;
                if (i == items.Count - 1) flags |= MF_END;
                else flags = (ushort)(flags & ~MF_END);
                WriteU16(ms, flags);
                if ((flags & MF_POPUP) != 0)
                {
                    WriteStr(ms, it.Text);
                    GenLevel(it.Sub, ms);
                }
                else
                {
                    WriteU16(ms, it.Id);
                    WriteStr(ms, it.Text);
                }
            }
        }

        private static void WriteU16(MemoryStream ms, ushort v)
        {
            ms.WriteByte((byte)(v & 0xFF));
            ms.WriteByte((byte)(v >> 8));
        }

        private static void WriteStr(MemoryStream ms, string s)
        {
            var b = Encoding.Unicode.GetBytes(s);
            ms.Write(b, 0, b.Length);
            ms.WriteByte(0); ms.WriteByte(0);
        }

        public static void Translate(List<MenuItem> items, Dictionary<string, string> table,
                                     ref int hits, List<string> missed)
        {
            foreach (var it in items)
            {
                if (table.TryGetValue(it.Text, out var zh))
                {
                    it.Text = zh;
                    hits++;
                }
                else if (!string.IsNullOrEmpty(it.Text))
                {
                    missed.Add(it.Text);
                }
                if (it.Sub != null) Translate(it.Sub, table, ref hits, missed);
            }
        }
    }

    internal sealed class PatchResult
    {
        public bool Success;
        public int MenuHits;
        public int StrHits;
        public readonly List<string> Log = new List<string>();
        public readonly List<string> Errors = new List<string>();
        public readonly List<string> Warnings = new List<string>();
        public readonly List<string> Missed = new List<string>();
    }

    internal static class Patcher
    {
        private static bool IsInnerAscii(byte hi, byte lo) => hi == 0 && lo >= 0x01 && lo <= 0x7F;

        private static bool BoundaryOk(byte[] data, int pos, int blen)
        {
            if (pos >= 2 && IsInnerAscii(data[pos - 1], data[pos - 2])) return false;
            if (pos + blen + 2 > data.Length) return false;
            return data[pos + blen] == 0 && data[pos + blen + 1] == 0;
        }

        private static int IndexOf(byte[] hay, byte[] needle, int start)
        {
            if (start >= hay.Length) return -1;
            int p = hay.AsSpan(start).IndexOf(needle);
            return p < 0 ? -1 : start + p;
        }

        /// <summary>对原始字节应用汉化补丁。成功时 patched 返回新数组；失败返回 false。</summary>
        public static bool Apply(byte[] original, out byte[] patched, PatchResult r)
        {
            patched = null;
            var data = (byte[])original.Clone();
            var pe = PeImage.Parse(original);
            if (!pe.Valid) { r.Errors.Add("不是有效的 PE 文件"); return false; }

            // ---------- 1. 菜单资源 ----------
            const uint RT_MENU = 4;
            int menuBlocks = 0;
            foreach (var m in pe.Resources)
            {
                if (m.TypeId != RT_MENU) continue;
                var blob = new byte[m.Size];
                Array.Copy(original, m.Offset, blob, 0, m.Size);
                List<MenuItem> items;
                try { items = MenuCodec.Parse(blob); }
                catch (Exception ex) { r.Errors.Add($"菜单解析失败 {m.Name}: {ex.Message}"); continue; }
                int hits = 0;
                MenuCodec.Translate(items, PatchData.MenuTable, ref hits, r.Missed);
                r.MenuHits += hits;
                var nb = MenuCodec.Generate(items);
                if (nb.Length > m.Size)
                {
                    r.Errors.Add($"菜单重建后过大: {nb.Length} > {m.Size}");
                    continue;
                }
                Array.Copy(nb, 0, data, m.Offset, nb.Length);
                for (int i = m.Offset + nb.Length; i < m.Offset + m.Size; i++) data[i] = 0;
                menuBlocks++;
                r.Log.Add($"菜单资源 {m.Name}: {m.Size} -> {nb.Length} 字节，翻译 {hits} 项");
            }
            if (menuBlocks == 0) r.Warnings.Add("未找到菜单资源（可能不是 RAMMap 主程序）");

            // ---------- 2. 对话框范围 ----------
            const uint RT_DIALOG = 5;
            var dlgRanges = new List<(int Off, int Size)>();
            foreach (var d in pe.Resources)
                if (d.TypeId == RT_DIALOG) dlgRanges.Add((d.Offset, d.Size));

            bool InDialog(int pos)
            {
                foreach (var (o, s) in dlgRanges)
                    if (pos >= o && pos < o + s) return true;
                return false;
            }

            // ---------- 3. 字符串替换 ----------
            foreach (var kv in PatchData.StrTable)
            {
                string en = kv.Key, zh = kv.Value;
                var pat = Encoding.Unicode.GetBytes(en);
                var zhb = Encoding.Unicode.GetBytes(zh);
                if (zhb.Length > pat.Length)
                {
                    r.Errors.Add($"译文过长被跳过: {en} -> {zh}");
                    continue;
                }
                int hits = 0, idx = 0;
                while (true)
                {
                    int pos = IndexOf(original, pat, idx);
                    if (pos < 0) break;
                    idx = pos + 2;
                    if (!BoundaryOk(original, pos, pat.Length)) continue;
                    string sec = pe.SectionOf(pos);
                    if (sec == ".text")
                    {
                        r.Warnings.Add($"代码段命中已跳过: {en}");
                        continue;
                    }
                    bool inDlg = InDialog(pos);
                    for (int i = 0; i < pat.Length; i++) data[pos + i] = 0;
                    Array.Copy(zhb, 0, data, pos, zhb.Length);
                    if (inDlg)
                    {
                        int pad = (pat.Length - zhb.Length) / 2;
                        for (int i = 0; i < pad; i++)
                        {
                            data[pos + zhb.Length + i * 2] = 0x20;
                            data[pos + zhb.Length + i * 2 + 1] = 0x00;
                        }
                    }
                    hits++;
                }
                if (hits == 0) r.Missed.Add(en);
                else r.StrHits += hits;
            }

            r.Missed.Sort();
            patched = data;
            r.Success = r.Errors.Count == 0;
            return r.Success;
        }
    }
}
