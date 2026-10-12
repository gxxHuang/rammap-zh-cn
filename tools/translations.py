# -*- coding: utf-8 -*-
"""RAMMap 汉化翻译表。

规则：
- menu: 菜单文本（重新序列化整个菜单模板，可自由加长，保留 & 加速键）
- strings: 其它界面字符串（原地等长替换，译文不得超过原文长度）
    - 位于对话框资源内 → 尾部补空格
    - 位于代码数据段   → 尾部补 NUL
- 绝不包含：内部标识符（XML 列名/注册表键/类名/资源名）、命令行开关、字体名、
  语言代码、月份/星期名、权限名、DLL 名。
"""

MENU_TABLE = {
    # ---- File ----
    "&File":                                      "文件(&F)",
    "Open...":                                    "打开(&O)...",
    "Save...":                                    "保存(&S)...",
    "&Find\tCtrl+F":                              "查找(&F)\tCtrl+F",
    "Refresh\tF5":                                "刷新(&R)\tF5",
    "E&xit":                                      "退出(&X)",
    # ---- Empty ----
    "&Empty":                                     "清空(&E)",
    "Empty &Working Sets":                        "清空工作集(&W)",
    "Empty &System Working Set":                  "清空系统工作集(&S)",
    "Empty &Modified Page List":                  "清空已修改页面列表(&M)",
    "Empty S&tandby List":                        "清空备用列表(&T)",
    "Empty Priority 0 Standby &List":             "清空优先级0备用列表(&L)",
    # ---- Settings ----
    "&Settings":                                  "设置(&S)",
    "&Colors":                                    "颜色(&C)",
    # ---- Help ----
    "&Help":                                      "帮助(&H)",
    "&Usage":                                     "用法(&U)",
    "&About":                                     "关于(&A)",
}

# 界面字符串（.rdata / 对话框资源）
STR_TABLE = {
    # ===== 主窗口 / 关于 / 标题 =====
    "RamMap - Sysinternals: www.sysinternals.com": "RAMMap - 物理内存分析器",
    "About RamMap":                               "关于 RAMMap",
    "RamMap - physical memory analyzer":          "RAMMap - 物理内存分析器",
    "Portions based on code by Alex Ionescu":     "部分代码基于 Alex Ionescu 的工作",
    "RAMMap Usage":                               "RAMMap 用法",

    # ===== 标签页名 =====
    "Use Counts":                                 "使用计数",
    "Processes":                                  "进程",
    "Priority Summary":                           "优先级摘要",
    "Physical Pages":                             "物理页面",
    "Physical Ranges":                            "物理范围",
    "File Summary":                               "文件摘要",
    "File Details":                               "文件详细信息",

    # ===== 内存类型 / 页面状态 =====
    "Active":                                     "活动",
    "Standby":                                    "备用",
    "Modified":                                   "已修改",
    "Modified No-Write":                          "已修改(不写)",
    "Modified no write":                          "已修改(不写)",
    "Modified nowrite":                           "已修改(不写)",
    "Transition":                                 "转换中",
    "Zeroed":                                     "已清零",
    "Free":                                       "空闲",
    "Zero":                                       "零",
    "Repurposed":                                 "改为他用",
    "Unused":                                     "未使用",
    "Driver Locked":                              "驱动程序锁定",
    "Kernel Stack":                               "内核堆栈",
    "Paged Pool":                                 "分页池",
    "Nonpaged Pool":                              "非分页池",
    "Page Table":                                 "页表",
    "System PTE":                                 "系统 PTE",
    "Large Page":                                 "大页",
    "Mapped File":                                "映射文件",
    "Metafile":                                   "图元文件",
    "Session Private":                            "会话专用",
    "Process Private":                            "进程专用",
    "Shareable":                                  "可共享",
    "Not Image":                                  "非映像",
    "Image":                                      "映像",
    "Total":                                      "总计",
    "PFNs":                                       "页帧数",

    # ===== 列头 =====
    "Name":                                       "名称",
    "Type":                                       "类型",
    "Size":                                       "大小",
    "Path":                                       "路径",
    "Offset":                                     "偏移",
    "Physical Address":                           "物理地址",
    "Virtual Address":                            "虚拟地址",
    "File Name":                                  "文件名",
    "Pool Tag":                                   "池标记",
    "Process":                                    "进程",
    "Session":                                    "会话",
    "Priority":                                   "优先级",
    "Start":                                      "起始",
    "End":                                        "结束",
    "Key":                                        "键",
    "Version":                                    "版本",
    "Private":                                    "专用",
    "Use":                                        "使用",
    "List":                                       "列表",

    # ===== 进程优先级 =====
    "Idle":                                       "空闲",
    "Very Low":                                   "极低",
    "Low":                                        "低",
    "Normal":                                     "普通",
    "Background":                                 "后台",
    "Application":                                "应用程序",

    # ===== 对话框控件 =====
    "Add Signature":                              "添加签名",
    "File Name:":                                 "文件名:",
    "Description:":                               "描述:",
    "Filter:":                                    "筛选:",
    "Label:":                                     "标签:",
    "Initializing...":                            "正在初始化...",
    "Saving...":                                  "正在保存...",
    "Cancel":                                     "取消",
    "OK":                                         "确定",
    "&OK":                                        "确定",
    "Reset to default":                           "恢复默认值",
    "RamMap Files (*.RMP)":                       "RAMMap 文件 (*.RMP)",

    # ===== 用法对话框 =====
    "Usage: Rammap [[outputfile] | [[-run32] -o <inputfile.rmp>]]":
                                                  "用法: Rammap [[输出文件] | [[-run32] -o <输入文件.rmp>]]",
    "Has RAMMap dump scan output to a file and exit.":
                                                  "让 RAMMap 把扫描结果转储到文件后退出。",
    "Has RAMMap open the specified log file.":    "让 RAMMap 打开指定的日志文件。",
    "Launch the 32-bit RAMMap on 64-bit Windows.":
                                                  "在 64 位 Windows 上启动 32 位 RAMMap。",
    "Command line mode: Rammap -E[wsmt0]":        "命令行模式: Rammap -E[wsmt0]",
    "Empty Working Sets":                         "清空工作集",
    "Empty System Working Sets":                  "清空系统工作集",
    "Empty Modified Page List":                   "清空已修改页面列表",
    "Empty Standby List":                         "清空备用列表",
    "Empty Priority 0 standby List":              "清空优先级 0 备用列表",

    # ===== 状态 / 错误消息 =====
    "No items to search":                         "没有可搜索的项",
    "Processing ":                                "正在处理 ",
    "Reading file":                               "正在读取文件",
    "Error exporting":                            "导出错误",
    "Error importing file:\r\n":                  "导入文件出错:\r\n",
    "Error refreshing database":                  "刷新数据库出错",
    "Missing file name for -o command line option.":
                                                  "命令行选项 -o 缺少文件名。",
    "RamMap requires Windows Vista or higher":    "RAMMap 需要 Windows Vista 或更高版本",
    "You must run the 64-bit version for memory analysis":
                                                  "必须使用 64 位版本进行内存分析",
    "The file is not a RamMap export file":       "该文件不是 RAMMap 导出文件",
    "The file is not a valid XML file":           "该文件不是有效的 XML 文件",
    "The file is not accessible, or is not a valid XML file":
                                                  "该文件无法访问，或不是有效的 XML 文件",
    "The file must be opened using the 32-bit version of RamMap":
                                                  "该文件必须使用 32 位版本的 RAMMap 打开",
    "The file version is not supported by this version of RamMap":
                                                  "此版本 RAMMap 不支持该文件的版本",
    "The file was created by an architecture not supported by this version of RamMap":
                                                  "创建该文件的体系结构不受此版本 RAMMap 支持",
    # —— 多行消息（含换行符，须整条替换）——
    "Failed to get required privileges.\r\nMake sure that you are running with administrative privileges\r\nand that your account has the Profile Process, Debug privileges\r\nIncrease Quota privileges.":
                                                  "获取所需权限失败。\r\n请确保以管理员权限运行，\r\n并且您的账户具有配置文件、进程和调试权限，\r\n以及增加配额权限。",
    "Unable to connect to the FileInfo driver.\nYou must reboot your system in order for the driver to load and RamMap to connect to it.":
                                                  "无法连接到 FileInfo 驱动程序。\n必须重启系统，驱动程序才能加载，RamMap 才能连接到它。",
    "Unable to connect to the FileInfo driver.\nWould you like RamMap to configure it to start at the next boot?":
                                                  "无法连接到 FileInfo 驱动程序。\n是否让 RAMMap 将它配置为在下次启动时自动加载？",
    "If you do this all values will be set to their default values. Click on OK to continue or cancel to keep changes":
                                                  "此操作会将所有值恢复为默认值。点击\"确定\"继续，或点击\"取消\"保留更改",
    "not implemented":                            "尚未实现",
    "Cancelled":                                  "已取消",
    "Cannot find string \"":                      "找不到字符串 \"",
}
