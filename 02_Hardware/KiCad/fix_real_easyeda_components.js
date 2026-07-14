const SYS = '0819f05c4eef4c71ace90d822a990e87';
const D = {
  TB6612FNG: '0e6600f45b16489e9666016017267cfb',
  C01U: 'ac7072e4a0764739a31216c96ed3c9cc',
  H3: 'a7415bb46c204efe91e1b40370ea127c',
  H10: '7e8dace7f54d4469b7eb9239696e241c',
  H12_2x6: '4f9d1ab374564afbac1f7f4e4a363894',
};

async function text(x, y, s, size = 50, color = '#222222', bold = false) {
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

async function place(ref, uuid, x, y, pinNets, value = ref) {
  const dev = await eda.lib_Device.get(uuid, SYS);
  if (!dev) throw new Error(`device get failed ${ref}`);
  const comp = await eda.sch_PrimitiveComponent.create(dev, x, y, undefined, 0, false, true, true);
  if (!comp) throw new Error(`place failed ${ref}`);
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
  let fp = '';
  try { fp = comp.getState_Footprint?.()?.name || ''; } catch (e) {}
  return { ref, fp, pinCount: pins.length };
}

const removed = await deleteByDesignator(['C1', 'C2', 'SERVO1', 'SERVO2', 'J_TRACK1', 'U_TB1', 'J_PWR1']);
const placed = [];

const tb = {
  'PWMA':'B15','AIN2':'A12','AIN1':'A13','STBY':'VCC','BIN1':'B00','BIN2':'B01','PWMB':'B16',
  'VM':'VM','VCC':'+5V','GND':'GND','AO1':'AO1','AO2':'AO2','BO2':'BO2','BO1':'BO1',
};
placed.push(await place('U_TB1', D.TB6612FNG, 5200, 4500, tb, 'TB6612FNG 芯片'));
placed.push(await place('C1', D.C01U, 9400, 4100, { '1':'+5V','2':'GND' }, '0.1uF 0603'));
placed.push(await place('C2', D.C01U, 9400, 5200, { '1':'+5V','2':'GND' }, '0.1uF 0603'));
placed.push(await place('SERVO1', D.H3, 11200, 4700, { '1':'B09','2':'+5V','3':'GND' }, '舵机1 1x3'));
placed.push(await place('SERVO2', D.H3, 13200, 4700, { '1':'B08','2':'+5V','3':'GND' }, '舵机2 1x3'));
placed.push(await place('J_TRACK1', D.H10, 11200, 6200, { '1':'+5V','2':'GND','3':'B25','4':'B24','5':'B20','6':'A14','7':'B18','8':'B19','9':'B10','10':'A07' }, '循迹 1x10'));
placed.push(await place('J_PWR1', D.H12_2x6, 13200, 6200, { '1':'+5V','2':'+5V','3':'GND','4':'GND','5':'GND','6':'GND','7':'VCC','8':'VCC','9':'GND','10':'GND','11':'VCC','12':'VCC' }, '供电桩 2x6'));

await text(500, 9350, '注意：TB6612 已使用真实 TB6612FNG 芯片封装；若你买的是 16Pin TB6612 模块，请后续替换为模块封装。U5/U9 精确料号仍需确认。', 58, '#666666');
try { await eda.sys_ToastMessage.showMessage('封装异常项已修正'); } catch(e) {}
return { ok: true, removed, placed };
