from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

OUT = Path(__file__).resolve().parent


def pin_lines(count, side="R", pitch=100, box_left=-250, box_right=650, pin_len=300, start=1):
    lines = []
    if side == "R":
        for idx in range(count):
            pin = start + idx
            y = (count - 1) * pitch // 2 - idx * pitch
            lines.append(f"X {pin} {pin} {box_left - pin_len} {y} {pin_len} R 45 45 1 1 P")
    elif side == "L":
        for idx in range(count):
            pin = start + idx
            y = (count - 1) * pitch // 2 - idx * pitch
            lines.append(f"X {pin} {pin} {box_right + pin_len} {y} {pin_len} L 45 45 1 1 P")
    else:
        raise ValueError(side)
    return lines


def make_symbol(name, ref, count, side="R"):
    split = count > 20
    visible_count = (count + 1) // 2 if split else count
    pitch = 80 if visible_count <= 20 else 70
    h = max(220, (visible_count + 1) * pitch // 2)
    box_left = -250
    box_right = 700 if count > 6 else 400
    body = [
        f"DEF {name} {ref} 0 40 Y N 1 F N",
        f'F0 "{ref}" 200 {h + 120} 60 H V C CNN',
        f'F1 "{name}" 200 -{h + 120} 55 H V C CNN',
        "DRAW",
        f"S {box_left} {h} {box_right} -{h} 0 1 10 N",
    ]
    if split:
        left_count = (count + 1) // 2
        right_count = count - left_count
        body += pin_lines(left_count, "R", pitch=pitch, box_left=box_left, box_right=box_right, start=1)
        body += pin_lines(right_count, "L", pitch=pitch, box_left=box_left, box_right=box_right, start=left_count + 1)
    else:
        body += pin_lines(count, side, pitch=pitch, box_left=box_left, box_right=box_right)
    body += ["ENDDRAW", "ENDDEF", "#"]
    return "\n".join(body)


LIB = """EESchema-LIBRARY Version 2.4
#encoding utf-8
#
{symbols}
#End Library
""".format(symbols="\n".join([
    make_symbol("CONN_01X02", "J", 2),
    make_symbol("CONN_01X03", "J", 3),
    make_symbol("CONN_01X04", "J", 4),
    make_symbol("CONN_01X06", "J", 6),
    make_symbol("CONN_01X10", "J", 10),
    make_symbol("CONN_02X06", "J", 12),
    make_symbol("MODULE_14", "U", 14),
    make_symbol("MODULE_17", "U", 17),
    make_symbol("MODULE_40", "U", 40),
    make_symbol("MODULE_80", "U", 80),
    make_symbol("TB6612_AB", "U", 16),
    make_symbol("BUZZER", "BZ", 2),
    make_symbol("SW_SPDT", "SW", 5),
    make_symbol("MOS_N", "Q", 3),
    make_symbol("R", "R", 2),
    make_symbol("C", "C", 2),
    make_symbol("LED", "D", 2),
]))


class Sch:
    def __init__(self):
        self.parts = []
        self.uid = 0x5F000000

    def next_uid(self):
        self.uid += 1
        return f"{self.uid:X}"

    def comp(self, lib, ref, val, x, y, labels, value_y=220):
        uid = self.next_uid()
        self.parts.append(f"""$Comp
L TianMengXing:{lib} {ref}
U 1 1 {uid}
P {x} {y}
F 0 "{ref}" H {x} {y - value_y} 50  0000 C CNN
F 1 "{val}" H {x} {y + value_y} 50  0000 C CNN
F 2 "" H {x} {y} 50  0001 C CNN
F 3 "" H {x} {y} 50  0001 C CNN
\t1    {x} {y}
\t1    0    0    -1
$EndComp
""")
        n = len(labels)
        split = n > 20
        visible_count = (n + 1) // 2 if split else n
        pitch = 80 if visible_count <= 20 else 70
        if split:
            left_count = (n + 1) // 2
            right_count = n - left_count
            top_left = y - (left_count - 1) * pitch // 2
            for i, net in enumerate(labels[:left_count]):
                py = top_left + i * pitch
                if net in (None, "", "NC"):
                    continue
                self.parts.append(f"Wire Wire Line\n\t{x - 850} {py} {x - 550} {py}\n")
                self.parts.append(f"Text Label {x - 850} {py} 0    50   ~ 0\n{net}\n")
            top_right = y - (right_count - 1) * pitch // 2
            for i, net in enumerate(labels[left_count:]):
                py = top_right + i * pitch
                if net in (None, "", "NC"):
                    continue
                self.parts.append(f"Wire Wire Line\n\t{x + 700} {py} {x + 1000} {py}\n")
                self.parts.append(f"Text Label {x + 1000} {py} 2    50   ~ 0\n{net}\n")
        else:
            top = y - (n - 1) * pitch // 2
            for i, net in enumerate(labels):
                py = top + i * pitch
                if net in (None, "", "NC"):
                    continue
                self.parts.append(f"Wire Wire Line\n\t{x - 550} {py} {x - 250} {py}\n")
                self.parts.append(f"Text Label {x - 550} {py} 0    50   ~ 0\n{net}\n")

    def text(self, text, x, y, size=100):
        self.parts.append(f"Text Notes {x} {y} 0    {size}  ~ 0\n{text}\n")

    def render(self):
        return """EESchema Schematic File Version 4
LIBS:TianMengXing-cache
EELAYER 30 0
EELAYER END
$Descr A2 23386 16535
encoding utf-8
Sheet 1 1
Title "小车拓展板天猛星2026"
Date "2026-04-18"
Rev "V1.0"
Comp "PDF reverse-created import scaffold"
$EndDescr
{body}
$EndSCHEMATC
""".format(body="\n".join(self.parts))


u6 = [
    "GND", "GND", "A00", "A28", "A01", "A31", "A08", "B04", "A09", "B05",
    "B15", "A10", "B16", "A11", "B02", "B12", "B03", "B13", "DIO", "CLK",
    "GND", "B07", "B06", "5V", "B08", "B26", "A12", "B09", "B23", "A13",
    "B27", "GND", "AGND", "3V3", "CHIP", "5V", "A29", "3V3", "GND", "5V",
    "5V", "A18", "GND", "B14", "GND", "B01", "GND", "A07", "B11", "B22",
    "RST", "GND", "B00", "3V3", "B10", "B18", "A27", "A23", "A30", "A21",
    "GND", "A15", "B21", "3V3", "B17", "A17", "A02", "A22", "A14", "B24",
    "B20", "A26", "A25", "A24", "B25", "GND", "A27", "5V", "GND", "GND",
]

u7 = [
    "A28", "A31", "B04", "B05", "A10", "A11", "B12", "B13", "VCC", "+5V",
    "B07", "B09", "A13", "B26", "A29", "CHIP", "3V3", "+5V", "GND", "GND",
    "A00", "A01", "A08", "A09", "B15", "B16", "B02", "B03", "DIO", "GND",
    "B06", "B08", "A12", "B23", "B27", "AGND", "GND", "GND", "GND", "GND",
]

u8 = [
    "A26", "A24", "B24", "A22", "A15", "A17", "B18", "A21", "A23", "VCC",
    "+5V", "B22", "B01", "A07", "B14", "A18", "3V3", "+5V", "GND", "GND",
    "A27", "A25", "B25", "B20", "A14", "A16", "B17", "B19", "A02", "B21",
    "A30", "B00", "B10", "B11", "RST", "GND", "GND", "GND", "GND", "GND",
]

sch = Sch()
sch.text("主控与扩展排针", 700, 450)
sch.comp("MODULE_80", "U6", "LCKFB-TMX-MSPM0G3507", 1700, 1450, u6)
sch.comp("MODULE_40", "U7", "主控左侧扩展排针", 4200, 1450, u7)
sch.comp("MODULE_40", "U8", "主控右侧扩展排针", 6400, 1450, u8)

sch.text("12V供电 / 电源模块", 8800, 450)
sch.comp("CONN_01X02", "P1", "WJ500V-5.08-2P 12V输入", 9300, 800, ["VM_RAW", "GND"])
sch.comp("SW_SPDT", "SW1", "SS-12D11G5R 开关", 10800, 800, ["GND", "VM", "NC", "VM_RAW", "GND"])
sch.comp("MODULE_14", "U5", "电源模块 5V/3V3", 12200, 1050, [
    "+5V", "+5V", "GND", "GND", "GND", "GND", "3V3", "3V3", "VM", "VM", "VM", "GND", "GND", "GND",
])

sch.text("蜂鸣器 / LED / 按键", 8800, 2350)
sch.comp("BUZZER", "BUZZER1", "3kHz", 9300, 2800, ["+5V", "BUZZER_SW"])
sch.comp("MOS_N", "Q1", "SI2302", 10500, 2800, ["BUZZER_SW", "B17", "GND"])
sch.comp("R", "R1", "10K", 11500, 2800, ["B17", "GND"])
sch.comp("R", "R2", "510", 9300, 3650, ["B27", "LED_A"])
sch.comp("LED", "LED1", "LED", 10500, 3650, ["LED_A", "3V3"])
sch.comp("CONN_01X02", "K2", "按键 A25", 11600, 3600, ["A25", "GND"])
sch.comp("CONN_01X02", "K1", "按键 A26", 12800, 3600, ["A26", "GND"])

sch.text("TB6612 / 电机", 8800, 4800)
sch.comp("TB6612_AB", "U_TB1", "TB6612-AB", 9400, 5600, [
    "B15", "A12", "A13", "VCC", "B00", "B01", "B16", "GND",
    "VM", "+5V", "GND", "AO1", "AO2", "BO2", "BO1", "GND",
])
sch.comp("CONN_01X06", "J_MA", "Motor-A BX-XH2.54-6PWZ", 11800, 5200, ["AO1", "GND", "A15", "A16", "AO2", "+5V"])
sch.comp("CONN_01X06", "J_MB", "Motor-B BX-XH2.54-6PWZ", 11800, 6300, ["BO2", "GND", "A17", "A24", "BO1", "+5V"])
sch.comp("C", "C1", "0.1uF Motor-B", 13600, 5200, ["+5V", "GND"])
sch.comp("C", "C2", "0.1uF Motor-A", 13600, 6300, ["+5V", "GND"])

sch.text("外设接口", 700, 7200)
sch.comp("CONN_01X04", "J_US1", "HC-SR04 超声波", 1400, 7700, ["+5V", "A08", "A09", "GND"])
sch.comp("CONN_01X04", "J_BT1", "2-TX1-RX 蓝牙", 3000, 7700, ["B06", "B07", "GND", "+5V"])
sch.comp("CONN_01X04", "J_CAM1", "1-TX2-RX 摄像头", 4600, 7700, ["B03", "B02", "GND", "+5V"])
sch.comp("CONN_01X04", "OLED1", "HS96L03W2C03 OLED", 6200, 7700, ["GND", "VCC", "A31", "A28"])
sch.comp("CONN_01X03", "SERVO1", "舵机1", 7800, 7500, ["B09", "+5V", "GND"])
sch.comp("CONN_01X03", "SERVO2", "舵机2", 9200, 7500, ["B08", "+5V", "GND"])
sch.comp("CONN_01X10", "J_TRACK1", "循迹 10P", 11000, 7800, ["+5V", "GND", "B25", "B24", "B20", "A14", "B18", "B19", "B10", "A07"])

sch.text("陀螺仪 / I2C", 700, 9900)
sch.comp("MODULE_17", "U9", "陀螺仪模块", 1600, 10600, [
    "+5V", "A01", "A00", "GND", "+5V", "NC", "NC", "A11", "A11", "A10", "GND", "NC", "3V3", "GND", "A11", "A10", "NC",
])
sch.comp("R", "R4", "4.7K", 3600, 10300, ["VCC", "A11"])
sch.comp("R", "R5", "4.7K", 3600, 11000, ["VCC", "A10"])

sch.text("供电桩 / 固定孔", 7000, 9900)
sch.comp("CONN_02X06", "J_PWR1", "电桩 2x6", 7600, 10600, ["+5V", "+5V", "GND", "GND", "GND", "GND", "VCC", "VCC", "GND", "GND", "VCC", "VCC"])
sch.comp("CONN_01X02", "SCREW1", "固定孔", 9400, 10100, ["NC", "NC"])
sch.comp("CONN_01X02", "SCREW2", "固定孔", 10400, 10100, ["NC", "NC"])
sch.comp("CONN_01X02", "SCREW3", "固定孔", 11400, 10100, ["NC", "NC"])
sch.comp("CONN_01X02", "SCREW4", "固定孔", 12400, 10100, ["NC", "NC"])
sch.comp("CONN_01X02", "SCREW6", "固定孔", 13400, 10100, ["NC", "NC"])

README = """# 天猛星原理图复刻工程

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
"""

(OUT / "TianMengXing.lib").write_text(LIB, encoding="utf-8")
(OUT / "TianMengXing.sch").write_text(sch.render(), encoding="utf-8")
(OUT / "TianMengXing.pro").write_text("update=2026-06-04\nversion=1\nlast_client=kicad\n", encoding="utf-8")
(OUT / "sym-lib-table").write_text('(sym_lib_table\n  (lib (name TianMengXing)(type Legacy)(uri "${KIPRJMOD}/TianMengXing.lib")(options "")(descr ""))\n)\n', encoding="utf-8")
(OUT / "README.md").write_text(README, encoding="utf-8")

zip_path = OUT / "TianMengXing_Schematic_KiCad.zip"
with ZipFile(zip_path, "w", ZIP_DEFLATED) as z:
    for name in ["TianMengXing.sch", "TianMengXing.lib", "TianMengXing.pro", "sym-lib-table", "README.md"]:
        z.write(OUT / name, name)
print(zip_path)
