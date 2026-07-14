# 06_Tools

开发工具与辅助脚本。

## 目录结构

| 目录 | 说明 |
|------|------|
| `PID_Tuner/` | Python PID 调试上位机（GUI + 串口 + 自动调参） |

## PID 调试助手

基于 Python 的跨平台 PID 调参工具，支持：
- 实时速度 / 位置曲线显示
- 串口通信（FF FE Wheeltec 兼容协议）
- LLM 辅助参数推荐
- 仿真模式（无需硬件）
- Windows exe 打包
