# 天猛星原理图复刻工程

这是根据 `天猛星原理图.pdf` 反向生成的 KiCad 中转工程，目标是导入嘉立创 EDA 专业版后继续编辑。

## 使用方法

1. 打开嘉立创 EDA 专业版。
2. 选择 `文件 -> 导入 -> KiCad`。
3. 选择本目录下的 `TianMengXing_Schematic_KiCad.zip`。
4. 导入后先检查 ERC，再为每个元件绑定嘉立创器件/封装。

## 重要说明

- PDF 不是原生工程源文件，无法保留嘉立创专业版元件 UUID、封装绑定、器件商城编号和精确图元样式。
- 本工程主要复刻网络连接关系，并用通用自定义符号表达模块和接口。
- 请重点核对：U7/U8 扩展排针、电源桩 J_PWR1、SW1 开关脚位、U9 陀螺仪模块的冗余 I2C/电源脚位。
- 电机、TB6612、OLED、超声波、蓝牙、摄像头、按键、蜂鸣器、LED 等网络已按 PDF 可见信息整理。

## 文件

- `TianMengXing.sch`: KiCad 5 风格原理图
- `TianMengXing.lib`: 自定义符号库
- `TianMengXing.pro`: KiCad 工程文件
- `sym-lib-table`: 工程符号库表
