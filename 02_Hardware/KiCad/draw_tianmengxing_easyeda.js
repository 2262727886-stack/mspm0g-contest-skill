const COLOR = {
  red: '#d32f2f',
  green: '#2e7d32',
  blue: '#1565c0',
  gray: '#666666',
  black: '#222222',
  fill: '#fffef8',
  pale: '#f7fbff',
};

async function safeDelete(api, args = []) {
  try {
    if (!api || !api.getAllPrimitiveId || !api.delete) return 0;
    const ids = await api.getAllPrimitiveId(...args);
    if (ids && ids.length) {
      await api.delete(ids);
      return ids.length;
    }
  } catch (e) {}
  return 0;
}

async function text(x, y, content, size = 80, color = COLOR.black, bold = false) {
  return await eda.sch_PrimitiveText.create(x, y, content, 0, color, null, size, bold, false, false);
}

async function rect(x, y, w, h, color = COLOR.red, fill = null, lineWidth = 2) {
  return await eda.sch_PrimitiveRectangle.create(x, y, w, h, 0, 0, color, fill, lineWidth);
}

async function wire(points, net = '') {
  return await eda.sch_PrimitiveWire.create(points, net || undefined, COLOR.green, 2);
}

async function port(net, x, y, dir = 'BI', rot = 0) {
  try {
    return await eda.sch_PrimitiveComponent.createNetPort(dir, net, x, y, rot, false);
  } catch (e) {
    await text(x, y - 20, net, 52, COLOR.blue);
  }
}

async function netFlag(net, x, y) {
  const id = net === 'GND' || net === 'AGND' ? 'Ground' : 'Power';
  try {
    return await eda.sch_PrimitiveComponent.createNetFlag(id, net, x, y, 0, false);
  } catch (e) {
    await text(x, y - 20, net, 52, COLOR.red);
  }
}

async function moduleBox(opts) {
  const { x, y, w, h, title, subtitle = '', left = [], right = [] } = opts;
  await rect(x, y, w, h, COLOR.red, COLOR.fill, 2);
  await text(x + 80, y + 120, title, 90, COLOR.black, true);
  if (subtitle) await text(x + 80, y + 230, subtitle, 55, COLOR.gray);

  const pinTop = y + 360;
  const pitch = Math.min(120, Math.max(55, Math.floor((h - 470) / Math.max(left.length, right.length, 1))));

  for (let i = 0; i < left.length; i++) {
    const p = left[i];
    const yy = pinTop + i * pitch;
    await wire([x - 260, yy, x, yy], p.net);
    await text(x + 35, yy - 18, `${p.no || ''} ${p.name || p.net}`, 42, COLOR.black);
    await text(x - 255, yy - 18, p.net, 42, COLOR.blue);
  }

  for (let i = 0; i < right.length; i++) {
    const p = right[i];
    const yy = pinTop + i * pitch;
    await wire([x + w, yy, x + w + 260, yy], p.net);
    await text(x + w - 360, yy - 18, `${p.no || ''} ${p.name || p.net}`, 42, COLOR.black);
    await text(x + w + 65, yy - 18, p.net, 42, COLOR.blue);
  }
}

function pins(list) {
  return list.map((net, idx) => ({ no: idx + 1, name: net, net }));
}

function numbered(arr) {
  return arr.map(([no, net]) => ({ no, name: net, net }));
}

let deleted = 0;
deleted += await safeDelete(eda.sch_PrimitiveText);
deleted += await safeDelete(eda.sch_PrimitiveRectangle);
deleted += await safeDelete(eda.sch_PrimitiveWire);
deleted += await safeDelete(eda.sch_PrimitiveComponent);
deleted += await safeDelete(eda.sch_PrimitivePin);
deleted += await safeDelete(eda.sch_PrimitiveBus);
deleted += await safeDelete(eda.sch_PrimitiveCircle);
deleted += await safeDelete(eda.sch_PrimitiveArc);
deleted += await safeDelete(eda.sch_PrimitivePolygon);

await rect(200, 200, 15400, 10800, COLOR.red, null, 3);
await text(550, 500, '小车拓展板天猛星2026 - 原理图复刻连接图', 150, COLOR.black, true);
await text(550, 700, '根据 PDF 反向整理。此图用于在嘉立创 EDA 中核对网络连接；器件库/封装需后续绑定。', 70, COLOR.gray);

await text(550, 1050, '主控与扩展排针', 110, COLOR.black, true);

const u6Left = numbered([
  [1, 'GND'], [3, 'A00'], [5, 'A01'], [7, 'A08'], [9, 'A09'], [11, 'B15'], [13, 'B16'], [15, 'B02'],
  [17, 'B03'], [19, 'DIO'], [21, 'GND'], [23, 'B06'], [25, 'B08'], [27, 'A12'], [29, 'B23'], [31, 'B27'],
  [33, 'AGND'], [35, 'CHIP'], [37, 'A29'], [39, 'GND'],
]);
const u6Right = numbered([
  [2, 'GND'], [4, 'A28'], [6, 'A31'], [8, 'B04'], [10, 'B05'], [12, 'A10'], [14, 'A11'], [16, 'B12'],
  [18, 'B13'], [20, 'CLK'], [22, 'B07'], [24, '5V'], [26, 'B26'], [28, 'B09'], [30, 'A13'], [32, 'GND'],
  [34, '3V3'], [36, '5V'], [38, '3V3'], [40, '5V'],
]);
await moduleBox({ x: 700, y: 1250, w: 1750, h: 1850, title: 'U6 主控左半', subtitle: 'LCKFB-TMX-MSPM0G3507', left: u6Left, right: u6Right });

const u6bLeft = numbered([
  [41, '5V'], [43, 'GND'], [45, 'GND'], [47, 'GND'], [49, 'B11'], [51, 'RST'], [53, 'B00'], [55, 'B10'],
  [57, 'A27'], [59, 'A30'], [61, 'GND'], [63, 'B21'], [65, 'B17'], [67, 'A02'], [69, 'A14'], [71, 'B20'],
  [73, 'A25'], [75, 'B25'], [77, 'A27'], [79, 'GND'],
]);
const u6bRight = numbered([
  [42, 'A18'], [44, 'B14'], [46, 'B01'], [48, 'A07'], [50, 'B22'], [52, 'GND'], [54, '3V3'], [56, 'B18'],
  [58, 'A23'], [60, 'A21'], [62, 'A15'], [64, '3V3'], [66, 'A17'], [68, 'A22'], [70, 'B24'], [72, 'A26'],
  [74, 'A24'], [76, 'GND'], [78, '5V'], [80, 'GND'],
]);
await moduleBox({ x: 3150, y: 1250, w: 1750, h: 1850, title: 'U6 主控右半', subtitle: 'MSPM0G3507 引出', left: u6bLeft, right: u6bRight });

await moduleBox({ x: 5500, y: 1250, w: 1450, h: 1700, title: 'U7 左扩展排针', left: pins(['A28', 'A31', 'B04', 'B05', 'A10', 'A11', 'B12', 'B13', 'VCC', '+5V', 'B07', 'B09', 'A13', 'B26', 'A29', 'CHIP', '3V3', '+5V', 'GND', 'GND']), right: pins(['A00', 'A01', 'A08', 'A09', 'B15', 'B16', 'B02', 'B03', 'DIO', 'GND', 'B06', 'B08', 'A12', 'B23', 'B27', 'AGND', 'GND', 'GND', 'GND', 'GND']) });
await moduleBox({ x: 7550, y: 1250, w: 1450, h: 1700, title: 'U8 右扩展排针', left: pins(['A26', 'A24', 'B24', 'A22', 'A15', 'A17', 'B18', 'A21', 'A23', 'VCC', '+5V', 'B22', 'B01', 'A07', 'B14', 'A18', '3V3', '+5V', 'GND', 'GND']), right: pins(['A27', 'A25', 'B25', 'B20', 'A14', 'A16', 'B17', 'B19', 'A02', 'B21', 'A30', 'B00', 'B10', 'B11', 'RST', 'GND', 'GND', 'GND', 'GND', 'GND']) });

await text(9800, 1050, '12V供电', 110, COLOR.black, true);
await moduleBox({ x: 9700, y: 1250, w: 1200, h: 520, title: 'P1 12V输入', subtitle: 'WJ500V-5.08-2P', left: pins(['VM_RAW', 'GND']), right: [] });
await moduleBox({ x: 11400, y: 1250, w: 1150, h: 620, title: 'SW1 开关', subtitle: 'SS-12D11G5R', left: pins(['GND', 'VM_RAW']), right: pins(['VM', 'GND']) });
await moduleBox({ x: 13200, y: 1250, w: 1350, h: 900, title: 'U5 电源模块', left: pins(['VM', 'VM', 'VM', 'GND', 'GND', 'GND']), right: pins(['+5V', '+5V', '3V3', '3V3', 'VCC', 'GND']) });

await text(9800, 2600, '蜂鸣器 / LED / 按键', 105, COLOR.black, true);
await moduleBox({ x: 9700, y: 2800, w: 1000, h: 620, title: '蜂鸣器', subtitle: 'BUZZER1 + Q1 SI2302', left: pins(['B17', '+5V']), right: pins(['GND']) });
await moduleBox({ x: 11100, y: 2800, w: 950, h: 620, title: 'LED1', subtitle: 'R2 510', left: pins(['B27']), right: pins(['3V3']) });
await moduleBox({ x: 12400, y: 2800, w: 950, h: 620, title: 'K2 按键', left: pins(['A25']), right: pins(['GND']) });
await moduleBox({ x: 13700, y: 2800, w: 950, h: 620, title: 'K1 按键', left: pins(['A26']), right: pins(['GND']) });

await text(9800, 4050, 'TB6612 与电机', 105, COLOR.black, true);
await moduleBox({ x: 9700, y: 4250, w: 1500, h: 1320, title: 'TB6612-AB', left: pins(['B15/PWMA', 'A12/AIN2', 'A13/AIN1', 'VCC/STBY', 'B00/BIN1', 'B01/BIN2', 'B16/PWMB', 'GND']), right: pins(['VM', '+5V/VCC', 'GND', 'AO1', 'AO2', 'BO2', 'BO1', 'GND']) });
await moduleBox({ x: 12100, y: 4250, w: 1300, h: 850, title: 'Motor-A', subtitle: 'BX-XH2.54-6PWZ', left: pins(['AO1', 'GND', 'A15', 'A16', 'AO2', '+5V']), right: [] });
await moduleBox({ x: 12100, y: 5300, w: 1300, h: 850, title: 'Motor-B', subtitle: 'BX-XH2.54-6PWZ', left: pins(['BO2', 'GND', 'A17', 'A24', 'BO1', '+5V']), right: [] });

await text(550, 3800, '外设接口', 105, COLOR.black, true);
await moduleBox({ x: 700, y: 4050, w: 1200, h: 620, title: '超声波', subtitle: 'HC-SR04', left: pins(['+5V', 'A08', 'A09', 'GND']), right: [] });
await moduleBox({ x: 2400, y: 4050, w: 1200, h: 620, title: '蓝牙串口', subtitle: '2-TX1-RX', left: pins(['B06', 'B07', 'GND', '+5V']), right: [] });
await moduleBox({ x: 4100, y: 4050, w: 1200, h: 620, title: '摄像头串口', subtitle: '1-TX2-RX', left: pins(['B03', 'B02', 'GND', '+5V']), right: [] });
await moduleBox({ x: 5800, y: 4050, w: 1200, h: 620, title: 'OLED', subtitle: 'HS96L03W2C03', left: pins(['GND', 'VCC', 'A31/SCL', 'A28/SDA']), right: [] });
await moduleBox({ x: 7500, y: 4050, w: 1200, h: 620, title: '舵机1/2', left: pins(['B09', '+5V', 'GND', 'B08', '+5V', 'GND']), right: [] });

await moduleBox({ x: 700, y: 5350, w: 1450, h: 900, title: '循迹 10P', left: pins(['+5V', 'GND', 'B25', 'B24', 'B20', 'A14', 'B18', 'B19', 'B10', 'A07']), right: [] });
await moduleBox({ x: 2900, y: 5350, w: 1700, h: 1180, title: 'U9 陀螺仪', subtitle: 'I2C + UART', left: pins(['+5V', 'A01', 'A00', 'GND', '+5V', '3V3', 'GND', 'A11/SCL', 'A10/SDA']), right: pins(['R4 4.7K to VCC', 'R5 4.7K to VCC']) });
await moduleBox({ x: 5350, y: 5350, w: 1500, h: 900, title: '供电桩', subtitle: '2x6', left: pins(['+5V', '+5V', 'GND', 'GND', 'GND', 'GND']), right: pins(['VCC', 'VCC', 'GND', 'GND', 'VCC', 'VCC']) });

await text(8200, 7100, '主要网络索引', 105, COLOR.black, true);
const nets = ['+5V', '3V3', 'VCC', 'VM', 'GND', 'AGND', 'A00', 'A01', 'A08', 'A09', 'A10', 'A11', 'A12', 'A13', 'A15', 'A16', 'A17', 'A24', 'A25', 'A26', 'A28', 'A31', 'B00', 'B01', 'B02', 'B03', 'B06', 'B07', 'B08', 'B09', 'B15', 'B16', 'B17', 'B27'];
for (let i = 0; i < nets.length; i++) {
  const col = i % 4;
  const row = Math.floor(i / 4);
  const x = 8200 + col * 1350;
  const y = 7350 + row * 190;
  await port(nets[i], x, y, 'BI');
  await text(x + 180, y - 25, nets[i], 58, COLOR.blue);
}

await netFlag('+5V', 550, 10200);
await netFlag('3V3', 1250, 10200);
await netFlag('VCC', 1950, 10200);
await netFlag('GND', 2650, 10200);

await text(9500, 10200, '状态：已通过 API 生成清晰复刻图。下一步：绑定真实器件/封装并按模块重画可出 PCB 的正式原理图。', 65, COLOR.gray);

try {
  await eda.sys_ToastMessage.showMessage('天猛星原理图复刻连接图已生成');
} catch (e) {}

return { ok: true, deleted };
