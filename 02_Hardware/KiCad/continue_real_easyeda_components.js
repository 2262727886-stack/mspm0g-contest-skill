const SYS = '0819f05c4eef4c71ace90d822a990e87';
const D = {
  R10K: 'b948db94476e4027ac8953235755ec96',
  R510: '33a3102241ba4ff69c357d325e1097f2',
  LED0805G: '9934e6f2be03427c81d2f7ee362750fc',
  KEY_B3F1000: '57ead04127214881a1f924a69521d213',
  TB6612FNG: '0e6600f45b16489e9666016017267cfb',
  XH6: '2e1a3afe1f8d4582b43bc876b03a4b57',
  C01U: 'ac7072e4a0764739a31216c96ed3c9cc',
  H4: 'c01f42e30f074377b46c9392cd868ea0',
  H3: 'a7415bb46c204efe91e1b40370ea127c',
  H10: '7e8dace7f54d4469b7eb9239696e241c',
  H40: 'f8845160e3bd4a779e3e5806498b6040',
  H12_2x6: '4f9d1ab374564afbac1f7f4e4a363894',
};

async function text(x, y, s, size = 55, color = '#222222', bold = false) {
  return await eda.sch_PrimitiveText.create(x, y, s, 0, color, null, size, bold, false, false);
}

async function wire(x1, y1, x2, y2, net = '') {
  return await eda.sch_PrimitiveWire.create([x1, y1, x2, y2], net || undefined, '#2e7d32', 2);
}

async function portOrFlag(net, x, y) {
  try {
    if (['+5V', '5V', '3V3', 'VCC', 'VM', 'GND', 'AGND'].includes(net)) {
      return await eda.sch_PrimitiveComponent.createNetFlag((net === 'GND' || net === 'AGND') ? 'Ground' : 'Power', net, x, y, 0, false);
    }
    return await eda.sch_PrimitiveComponent.createNetPort('BI', net, x, y, 0, false);
  } catch (e) {
    return await text(x + 30, y - 16, net, 42, '#1565c0');
  }
}

async function deleteByDesignator(refs) {
  const ids = await eda.sch_PrimitiveComponent.getAllPrimitiveId();
  const del = [];
  for (const id of ids) {
    const c = await eda.sch_PrimitiveComponent.get(id);
    if (!c) continue;
    let d = '';
    try { d = c.getState_Designator?.() || ''; } catch (e) {}
    if (refs.includes(d)) del.push(id);
  }
  if (del.length) await eda.sch_PrimitiveComponent.delete(del);
  return del.length;
}

async function place(ref, uuid, x, y, pinNets, value = ref, options = {}) {
  const comp = await eda.sch_PrimitiveComponent.create({ libraryUuid: SYS, uuid }, x, y, undefined, options.rotation || 0, !!options.mirror, true, true);
  if (!comp) throw new Error(`failed to place ${ref}`);
  const id = comp.getState_PrimitiveId();
  try { await eda.sch_PrimitiveComponent.modify(id, { designator: ref, name: value }); } catch (e) {}
  await text(x - 120, y - 245, `${ref}  ${value}`, 50, '#111111', true);
  const pins = await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(id) || [];
  for (const p of pins) {
    const no = p.getState_PinNumber();
    const name = p.getState_PinName();
    const net = pinNets[no] || pinNets[name];
    if (!net || net === 'NC') continue;
    const px = p.getState_X();
    const py = p.getState_Y();
    const rot = p.getState_Rotation();
    let dx = 150, dy = 0;
    if (rot === 180) dx = -150;
    else if (rot === 90) { dx = 0; dy = -150; }
    else if (rot === 270) { dx = 0; dy = 150; }
    await wire(px, py, px + dx, py + dy, net);
    await portOrFlag(net, px + dx, py + dy);
  }
  return { ref, id, pinCount: pins.length };
}

let removed = await deleteByDesignator(['R1', 'R2', 'LED1', 'K1', 'K2']);
const placed = [];

placed.push(await place('R1', D.R10K, 11800, 1000, { '1':'B17', '2':'GND' }, '10K 0603'));
placed.push(await place('R2', D.R510, 11800, 1650, { '1':'B27', '2':'LED_A' }, '510R 0603'));
placed.push(await place('LED1', D.LED0805G, 13200, 1650, { '1':'LED_A', '2':'3V3', 'A':'LED_A', 'K':'3V3' }, 'LED 0805 green'));
placed.push(await place('K1', D.KEY_B3F1000, 9000, 2600, { '1':'A26','2':'A26','3':'GND','4':'GND' }, 'B3F-1000 按键A26'));
placed.push(await place('K2', D.KEY_B3F1000, 10400, 2600, { '1':'A25','2':'A25','3':'GND','4':'GND' }, 'B3F-1000 按键A25'));

const u7 = {
  '1':'A28','2':'A31','3':'B04','4':'B05','5':'A10','6':'A11','7':'B12','8':'B13','9':'VCC','10':'+5V',
  '11':'B07','12':'B09','13':'A13','14':'B26','15':'A29','16':'CHIP','17':'3V3','18':'+5V','19':'GND','20':'GND',
  '21':'A00','22':'A01','23':'A08','24':'A09','25':'B15','26':'B16','27':'B02','28':'B03','29':'DIO','30':'GND',
  '31':'B06','32':'B08','33':'A12','34':'B23','35':'B27','36':'AGND','37':'GND','38':'GND','39':'GND','40':'GND',
};
const u8 = {
  '1':'A26','2':'A24','3':'B24','4':'A22','5':'A15','6':'A17','7':'B18','8':'A21','9':'A23','10':'VCC',
  '11':'+5V','12':'B22','13':'B01','14':'A07','15':'B14','16':'A18','17':'3V3','18':'+5V','19':'GND','20':'GND',
  '21':'A27','22':'A25','23':'B25','24':'B20','25':'A14','26':'A16','27':'B17','28':'B19','29':'A02','30':'B21',
  '31':'A30','32':'B00','33':'B10','34':'B11','35':'RST','36':'GND','37':'GND','38':'GND','39':'GND','40':'GND',
};
placed.push(await place('U7', D.H40, 3600, 6900, u7, '2x20 2.54 左扩展排针'));
placed.push(await place('U8', D.H40, 6500, 6900, u8, '2x20 2.54 右扩展排针'));

const tb = {
  'PWMA':'B15','AIN2':'A12','AIN1':'A13','STBY':'VCC','BIN1':'B00','BIN2':'B01','PWMB':'B16',
  'VM':'VM','VCC':'+5V','GND':'GND','AO1':'AO1','AO2':'AO2','BO2':'BO2','BO1':'BO1',
  '1':'B15','2':'A12','3':'A13','4':'VCC','5':'B00','6':'B01','7':'B16','8':'GND',
};
placed.push(await place('U_TB1', D.TB6612FNG, 5200, 4500, tb, 'TB6612FNG 芯片'));
placed.push(await place('J_MA', D.XH6, 7600, 4100, { '1':'AO1','2':'GND','3':'A15','4':'A16','5':'AO2','6':'+5V' }, 'Motor-A XH2.54-6P'));
placed.push(await place('J_MB', D.XH6, 7600, 5200, { '1':'BO2','2':'GND','3':'A17','4':'A24','5':'BO1','6':'+5V' }, 'Motor-B XH2.54-6P'));
placed.push(await place('C1', D.C01U, 9400, 4100, { '1':'+5V','2':'GND' }, '0.1uF 0603'));
placed.push(await place('C2', D.C01U, 9400, 5200, { '1':'+5V','2':'GND' }, '0.1uF 0603'));

placed.push(await place('J_BT1', D.H4, 11200, 3600, { '1':'B06','2':'B07','3':'GND','4':'+5V' }, '蓝牙接口 1x4'));
placed.push(await place('J_CAM1', D.H4, 13200, 3600, { '1':'B03','2':'B02','3':'GND','4':'+5V' }, '摄像头串口 1x4'));
placed.push(await place('SERVO1', D.H3, 11200, 4700, { '1':'B09','2':'+5V','3':'GND' }, '舵机1 1x3'));
placed.push(await place('SERVO2', D.H3, 13200, 4700, { '1':'B08','2':'+5V','3':'GND' }, '舵机2 1x3'));
placed.push(await place('J_TRACK1', D.H10, 11200, 6200, { '1':'+5V','2':'GND','3':'B25','4':'B24','5':'B20','6':'A14','7':'B18','8':'B19','9':'B10','10':'A07' }, '循迹 1x10'));
placed.push(await place('J_PWR1', D.H12_2x6, 13200, 6200, { '1':'+5V','2':'+5V','3':'GND','4':'GND','5':'GND','6':'GND','7':'VCC','8':'VCC','9':'GND','10':'GND','11':'VCC','12':'VCC' }, '供电桩 2x6'));

await text(500, 9200, '未完全确认：U5 电源模块、U9 陀螺仪模块的精确料号/封装 PDF 未给出；当前保留为需人工指定项。TB6612 使用真实 TB6612FNG 芯片，若实际是 16Pin 模块需换为模块器件。', 58, '#666666');
try { await eda.sys_ToastMessage.showMessage('剩余真实器件已补齐，错误器件已替换'); } catch(e) {}
return { ok: true, removed, placed };
