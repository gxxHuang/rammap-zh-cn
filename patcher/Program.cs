// RAMMap 汉化工具 - 图形界面
using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Text;
using System.Windows.Forms;

namespace RamMapZh
{
    internal enum FileState { Missing, Original, Patched, Unknown }

    internal sealed class MainForm : Form
    {
        private readonly TextBox _dirBox = new TextBox();
        private readonly Button _browseBtn = new Button();
        private readonly ListView _list = new ListView();
        private readonly Button _patchBtn = new Button();
        private readonly Button _restoreBtn = new Button();
        private readonly TextBox _log = new TextBox();

        private static readonly string[] Targets = { "RAMMap64.exe", "RAMMap.exe", "RAMMap64a.exe" };

        public MainForm()
        {
            Text = "RAMMap 汉化工具  v1.0";
            ClientSize = new Size(760, 560);
            Font = new Font("Microsoft YaHei UI", 9F);
            StartPosition = FormStartPosition.CenterScreen;
            AllowDrop = true;
            DragEnter += (s, e) => { if (e.Data.GetDataPresent(DataFormats.FileDrop)) e.Effect = DragDropEffects.Copy; };
            DragDrop += (s, e) =>
            {
                var files = (string[])e.Data.GetData(DataFormats.FileDrop);
                if (files != null && files.Length > 0)
                {
                    var p = files[0];
                    if (File.Exists(p)) p = Path.GetDirectoryName(p);
                    _dirBox.Text = p;
                    Scan();
                }
            };

            var lbl1 = new Label { Text = "RAMMap 目录：", Left = 14, Top = 18, Width = 90 };
            _dirBox.SetBounds(105, 14, 540, 26);
            _dirBox.TextChanged += (s, e) => Scan();
            _browseBtn.Text = "浏览...";
            _browseBtn.SetBounds(655, 13, 90, 28);
            _browseBtn.Click += (s, e) =>
            {
                using (var dlg = new FolderBrowserDialog { Description = "选择包含 RAMMap.exe 的目录" })
                {
                    if (dlg.ShowDialog() == DialogResult.OK)
                    {
                        _dirBox.Text = dlg.SelectedPath;
                    }
                }
            };

            _list.SetBounds(14, 52, 731, 130);
            _list.View = View.Details;
            _list.FullRowSelect = true;
            _list.GridLines = true;
            _list.Columns.Add("文件", 180);
            _list.Columns.Add("状态", 260);
            _list.Columns.Add("备份", 130);
            _list.Columns.Add("大小", 130);

            _patchBtn.Text = "汉化  →";
            _patchBtn.SetBounds(14, 192, 160, 36);
            _patchBtn.Click += (s, e) => DoPatch();
            _restoreBtn.Text = "←  还原原版";
            _restoreBtn.SetBounds(190, 192, 160, 36);
            _restoreBtn.Click += (s, e) => DoRestore();

            var lbl2 = new Label { Text = "日志：", Left = 14, Top = 240, Width = 100, Height = 20 };
            _log.SetBounds(14, 262, 731, 282);
            _log.Multiline = true;
            _log.ReadOnly = true;
            _log.ScrollBars = ScrollBars.Vertical;
            _log.BackColor = Color.FromArgb(30, 30, 30);
            _log.ForeColor = Color.Gainsboro;
            _log.Font = new Font("Consolas", 9F);

            Controls.AddRange(new Control[] { lbl1, _dirBox, _browseBtn, _list, _patchBtn, _restoreBtn, lbl2, _log });

            string guess = GuessDir();
            if (guess != null) _dirBox.Text = guess;
            AppendLog("提示：选择 RAMMap 所在目录后点\"汉化\"即可；原始文件会自动备份，随时可还原。");
            AppendLog("说明：汉化只替换界面文字数据，不改动程序代码（.text 段），不影响功能。");
        }

        private static string GuessDir()
        {
            foreach (var baseDir in new[]
            {
                AppDomain.CurrentDomain.BaseDirectory,
                Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads"),
            })
            {
                try
                {
                    foreach (var t in Targets)
                        if (File.Exists(Path.Combine(baseDir, t))) return baseDir;
                }
                catch { }
            }
            return null;
        }

        private void AppendLog(string s)
        {
            _log.AppendText($"[{DateTime.Now:HH:mm:ss}] {s}\r\n");
        }

        private static bool IsRamMap(string path, out bool patched)
        {
            patched = false;
            try
            {
                var data = File.ReadAllBytes(path);
                var pe = PeImage.Parse(data);
                if (!pe.Valid) return false;
                foreach (var m in pe.Resources)
                {
                    if (m.TypeId != 4 || m.Name != "MAIN_MENU" || m.Size < 8) continue;
                    var blob = new byte[m.Size];
                    Array.Copy(data, m.Offset, blob, 0, m.Size);
                    var items = MenuCodec.Parse(blob);
                    if (items.Count == 0) continue;
                    // RAMMap 主菜单第一项应为 &File / 文件(&F)
                    var first = items[0].Text;
                    if (first == "&File") { patched = false; return true; }
                    if (first == "文件(&F)") { patched = true; return true; }
                }
            }
            catch { }
            return false;
        }

        private void Scan()
        {
            _list.BeginUpdate();
            _list.Items.Clear();
            string dir = _dirBox.Text.Trim();
            if (dir.Length == 0 || !Directory.Exists(dir))
            {
                _list.EndUpdate();
                return;
            }
            foreach (var name in Targets)
            {
                var p = Path.Combine(dir, name);
                var li = _list.Items.Add(name);
                if (!File.Exists(p))
                {
                    li.SubItems.Add("未找到");
                    li.SubItems.Add("-");
                    li.SubItems.Add("-");
                    li.ForeColor = Color.Gray;
                    continue;
                }
                long size = new FileInfo(p).Length;
                li.SubItems.Add("正在识别...");
                li.SubItems.Add(File.Exists(p + ".zhbak") ? "有 (.zhbak)" : "无");
                li.SubItems.Add($"{size / 1024} KB");
                li.Tag = p;
            }
            _list.EndUpdate();

            // 识别状态（放到后台不阻塞也行，这里直接做，文件很小）
            for (int i = 0; i < _list.Items.Count; i++)
            {
                var li = _list.Items[i];
                var p = li.Tag as string;
                if (p == null) continue;
                if (IsRamMap(p, out bool patched))
                {
                    li.SubItems[1].Text = patched ? "已汉化" : "原版（可汉化）";
                    li.ForeColor = patched ? Color.SeaGreen : Color.FromArgb(0, 90, 170);
                }
                else
                {
                    li.SubItems[1].Text = "无法识别（非 RAMMap？）";
                    li.ForeColor = Color.Firebrick;
                }
            }
        }

        private void DoPatch()
        {
            string dir = _dirBox.Text.Trim();
            if (!Directory.Exists(dir)) { AppendLog("目录不存在"); return; }
            int ok = 0, skip = 0, fail = 0;
            foreach (var name in Targets)
            {
                var p = Path.Combine(dir, name);
                if (!File.Exists(p)) continue;
                if (!IsRamMap(p, out bool patched))
                {
                    AppendLog($"跳过 {name}：不是可识别的 RAMMap");
                    skip++;
                    continue;
                }
                if (patched)
                {
                    AppendLog($"跳过 {name}：已经是汉化版");
                    skip++;
                    continue;
                }
                try
                {
                    var original = File.ReadAllBytes(p);
                    var report = new PatchResult();
                    if (!Patcher.Apply(original, out var patchedData, report))
                    {
                        AppendLog($"失败 {name}：{string.Join("; ", report.Errors)}");
                        fail++;
                        continue;
                    }
                    // 备份（仅在无备份时创建，避免覆盖原始备份）
                    string bak = p + ".zhbak";
                    if (!File.Exists(bak))
                    {
                        File.Copy(p, bak, false);
                        AppendLog($"已备份原件 -> {Path.GetFileName(bak)}");
                    }
                    else AppendLog("已存在备份，保留原有备份未覆盖");
                    File.WriteAllBytes(p, patchedData);
                    AppendLog($"✔ {name} 汉化完成：菜单 {report.MenuHits} 项，界面字符串 {report.StrHits} 处");
                    if (report.Warnings.Count > 0)
                        foreach (var w in report.Warnings) AppendLog("   " + w);
                    if (report.Missed.Count > 0)
                        AppendLog($"   注意：{report.Missed.Count} 条字符串未匹配（版本差异），已保留原文");
                    ok++;
                }
                catch (UnauthorizedAccessException)
                {
                    AppendLog($"失败 {name}：无写入权限，请右键\"以管理员身份运行\"本工具后重试");
                    fail++;
                }
                catch (Exception ex)
                {
                    AppendLog($"失败 {name}：{ex.Message}");
                    fail++;
                }
            }
            AppendLog($"—— 汉化完成：成功 {ok}，跳过 {skip}，失败 {fail} ——");
            Scan();
        }

        private void DoRestore()
        {
            string dir = _dirBox.Text.Trim();
            if (!Directory.Exists(dir)) { AppendLog("目录不存在"); return; }
            int ok = 0;
            foreach (var name in Targets)
            {
                var p = Path.Combine(dir, name);
                var bak = p + ".zhbak";
                if (!File.Exists(bak)) continue;
                try
                {
                    File.Copy(bak, p, true);
                    AppendLog($"✔ {name} 已从备份还原为原版");
                    ok++;
                }
                catch (UnauthorizedAccessException)
                {
                    AppendLog($"失败 {name}：无写入权限，请以管理员身份运行本工具");
                }
                catch (Exception ex)
                {
                    AppendLog($"失败 {name}：{ex.Message}");
                }
            }
            if (ok == 0) AppendLog("没有找到可还原的备份（.zhbak 文件）");
            AppendLog($"—— 还原完成：{ok} 个文件 ——");
            Scan();
        }
    }

    internal static class Program
    {
        [STAThread]
        private static void Main(string[] args)
        {
            // 命令行模式（供脚本调用）：--patch <目录> / --restore <目录>
            if (args.Length >= 2 && (args[0] == "--patch" || args[0] == "--restore"))
            {
                RunCli(args[0] == "--patch", args[1]);
                return;
            }
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new MainForm());
        }

        private static void RunCli(bool patch, string dir)
        {
            Console.OutputEncoding = Encoding.UTF8;
            if (!Directory.Exists(dir)) { Console.WriteLine("目录不存在: " + dir); Environment.Exit(2); }
            int rc = 0;
            foreach (var name in new[] { "RAMMap64.exe", "RAMMap.exe", "RAMMap64a.exe" })
            {
                var p = Path.Combine(dir, name);
                if (!File.Exists(p)) continue;
                try
                {
                    if (patch)
                    {
                        var data = File.ReadAllBytes(p);
                        var rep = new PatchResult();
                        if (!Patcher.Apply(data, out var outData, rep))
                        {
                            Console.WriteLine($"{name}: 失败 - {string.Join("; ", rep.Errors)}"); rc = 1; continue;
                        }
                        var bak = p + ".zhbak";
                        if (!File.Exists(bak)) File.Copy(p, bak, false);
                        File.WriteAllBytes(p, outData);
                        Console.WriteLine($"{name}: 汉化完成 (菜单 {rep.MenuHits} 项, 字符串 {rep.StrHits} 处)");
                    }
                    else
                    {
                        var bak = p + ".zhbak";
                        if (!File.Exists(bak)) { Console.WriteLine($"{name}: 无备份，跳过"); continue; }
                        File.Copy(bak, p, true);
                        Console.WriteLine($"{name}: 已还原");
                    }
                }
                catch (Exception ex) { Console.WriteLine($"{name}: 失败 - {ex.Message}"); rc = 1; }
            }
            Environment.Exit(rc);
        }
    }
}
