# MSPM0G 电赛开发助手

MSPM0G3507 + K230 双芯架构 25E 电赛完整参考。

## 项目结构

```
├── k230_cam_test.py          # K230 视觉端 (GC2093 + OLED + A4检测 + UART)
├── k230_sensor_diag.py       # K230 摄像头诊断脚本
├── m0g_25e_receiver.c        # MSPM0G 拓展板接收框架
├── .claude/
│   ├── CLAUDE.md             # 开发规范 (82行核心规则)
│   └── skills/mspm0g-contest/
│       └── SKILL.md          # 完整参考资料 (引脚/API/算法/真题)
└── README.md
```

## 验证状态

| 模块 | 状态 |
|------|------|
| K230 GC2093 采集 QVGA 60fps | ✅ 实机通过 |
| K230 A4黑框检测 + OLED显示 | ✅ 实机通过 |
| K230 自动阈值校准 + Otsu | ✅ 实机通过 |
| K230 UART2→M0G 帧协议 | ✅ 代码就绪 |
| M0G 拓展板引脚全表 | ✅ SysConfig 验证 |
| M0G SDK API 黑名单 (16条) | ✅ 头文件+例程双重确认 |
| M0G TB6612/编码器/舵机 | 🟡 待实机 |
| 双芯联调 | 🟡 待仿真器 |

## SDK API 验证

基于 TI MSPM0 SDK 2.10.00.04，已检查 **11 个 G3507 裸机 driverlib 例程**，确认 16 条不存在的 API（详见 SKILL.md 黑名单）。

## 快速开始

### K230 视觉端
1. 将 `k230_cam_test.py` 保存为 `/sdcard/main.py`
2. 上电自动运行 → OLED 显示启动画面 → 自动校准 → 检测

### M0G 控制端
1. CCS 新建工程 → SysConfig 按 `m0g_25e_receiver.c` 头部注释配置
2. 合并代码 → 编译 → XDS110 烧录

## Release

当前版本: **v2.0** — 完整 SDK 验证 + K230 视觉稳定 + 拓展板引脚就绪
