# 04_Software

软件代码：K230 视觉端 MicroPython 脚本、PC 上位机工具。

## 目录结构

### K230 — 视觉识别脚本

K230 庐山派 MicroPython 脚本，用于摄像头采集、色块/形状检测、双芯通信。

**开发环境**
- 固件: CanMV `canmv_k230`
- 摄像头: GC2093 (CSI 2, Sensor id=2)
- 通信: UART 9600 8N1, FF FE Wheeltec 协议
