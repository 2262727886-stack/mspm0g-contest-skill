async function allIds(api, ...args) {
  try { return await api.getAllPrimitiveId(...args) || []; } catch (e) { return []; }
}

async function clearSheet() {
  const apis = [
    eda.sch_PrimitiveText, eda.sch_PrimitiveRectangle, eda.sch_PrimitiveWire,
    eda.sch_PrimitiveComponent, eda.sch_PrimitivePin, eda.sch_PrimitiveBus,
    eda.sch_PrimitiveCircle, eda.sch_PrimitiveArc, eda.sch_PrimitivePolygon,
  ];
  let deleted = 0;
  for (const api of apis) {
    try {
      const ids = await allIds(api);
      if (ids.length) {
        await api.delete(ids);
        deleted += ids.length;
      }
    } catch (e) {}
  }
  return deleted;
}

async function text(x, y, s, size = 65, color = '#222222', bold = false) {
  return await eda.sch_PrimitiveText.create(x, y, s, 0, color, null, size, bold, false, false);
}

async function line(x1, y1, x2, y2, net = '') {
  return await eda.sch_PrimitiveWire.create([x1, y1, x2, y2], net || undefined, '#2e7d32', 2);
}

async function port(net, x, y, direction = 'BI') {
  try {
    return await eda.sch_PrimitiveComponent.createNetPort(direction, net, x, y, 0, false);
  } catch (e) {
    return await text(x + 40, y - 16, net, 44, '#1565c0');
  }
}

async function flag(net, x, y) {
  const kind = net === 'GND' || net === 'AGND' ? 'Ground' : 'Power';
  try {
    return await eda.sch_PrimitiveComponent.createNetFlag(kind, net, x, y, 0, false);
  } catch (e) {
    return await text(x + 40, y - 16, net, 44, '#d32f2f');
  }
}

async function device(query, pick = 0) {
  const sys = await eda.lib_LibrariesList.getSystemLibraryUuid();
  const r = await eda.lib_Device.search(query, sys, undefined, undefined, 12, 1);
  if (!r || !r[pick]) throw new Error(`Device not found: ${query}`);
  return r[pick];
}

async function place(ref, query, x, y, pinNets, options = {}) {
  const dev = await device(query, options.pick || 0);
  const comp = await eda.sch_PrimitiveComponent.create(dev, x, y, options.subPartName, options.rotation || 0, !!options.mirror, true, true);
  if (!comp) throw new Error(`Place failed: ${ref}/${query}`);
  const id = comp.getState_PrimitiveId();
  try {
    await eda.sch_PrimitiveComponent.modify(id, { designator: ref, name: options.value || dev.name });
  } catch (e) {}
  await text(x - 120, y - 260, `${ref}  ${options.value || dev.name}`, 55, '#222222', true);
  await text(x - 120, y - 180, `封装: ${dev.footprintName || ''}  LCSC: ${dev.lcscId || ''}`, 38, '#666666');

  const pins = await eda.sch_PrimitiveComponent.getAllPinsByPrimitiveId(id) || [];
  for (const p of pins) {
    const no = p.getState_PinNumber();
    const pinName = p.getState_PinName();
    const net = pinNets[no] || pinNets[pinName];
    if (!net || net === 'NC') continue;
    const px = p.getState_X();
    const py = p.getState_Y();
    const rot = p.getState_Rotation();
    let dx = 160, dy = 0;
    if (rot === 0) { dx = 160; dy = 0; }
    else if (rot === 180) { dx = -160; dy = 0; }
    else if (rot === 90) { dx = 0; dy = -160; }
    else if (rot === 270) { dx = 0; dy = 160; }
    await line(px, py, px + dx, py + dy, net);
    if (['+5V', '5V', '3V3', 'VCC', 'VM', 'GND', 'AGND'].includes(net)) await flag(net, px + dx, py + dy);
    else await port(net, px + dx, py + dy, 'BI');
  }
  return { ref, query, name: dev.name, lcscId: dev.lcscId, footprint: dev.footprintName, primitiveId: id, pinCount: pins.length };
}

const deleted = await clearSheet();

await text(500, 420, '小车拓展板天猛星2026 - 真实器件/封装版', 120, '#111111', true);
await text(500, 610, '已从嘉立创系统库放置器件并绑定封装；网络按 PDF 复刻。请导出 PCB 前人工核对引脚序号和模块方向。', 62, '#666666');

const placed = [];

placed.push(await place('U6', 'LCKFB-TMX-MSPM0G3507', 1700, 2300, {
  '1':'GND','2':'GND','3':'A00','4':'A28','5':'A01','6':'A31','7':'A08','8':'B04','9':'A09','10':'B05',
  '11':'B15','12':'A10','13':'B16','14':'A11','15':'B02','16':'B12','17':'B03','18':'B13','19':'DIO','20':'CLK',
  '21':'GND','22':'B07','23':'B06','24':'5V','25':'B08','26':'B26','27':'A12','28':'B09','29':'B23','30':'A13',
  '31':'B27','32':'GND','33':'AGND','34':'3V3','35':'CHIP','36':'5V','37':'A29','38':'3V3','39':'GND','40':'5V',
  '41':'5V','42':'A18','43':'GND','44':'B14','45':'GND','46':'B01','47':'GND','48':'A07','49':'B11','50':'B22',
  '51':'RST','52':'GND','53':'B00','54':'3V3','55':'B10','56':'B18','57':'A27','58':'A23','59':'A30','60':'A21',
  '61':'GND','62':'A15','63':'B21','64':'3V3','65':'B17','66':'A17','67':'A02','68':'A22','69':'A14','70':'B24',
  '71':'B20','72':'A26','73':'A25','74':'A24','75':'B25','76':'GND','77':'A27','78':'5V','79':'GND','80':'GND',
}, { value: 'LCKFB-TMX-MSPM0G3507' }));

placed.push(await place('P1', 'WJ500V-5.08-2P', 5200, 1150, { '1':'VM_RAW', '2':'GND' }, { value: '12V输入' }));
placed.push(await place('SW1', 'SS-12D11G5R', 6800, 1150, { '1':'GND', '2':'VM', '3':'VM_RAW', '4':'GND', '5':'NC' }, { value: '电源开关' }));

// Use the exact module if available; otherwise these nets document the regulator module pads.
placed.push(await place('OLED1', 'HS96L03W2C03', 5200, 2500, { '1':'GND', '2':'VCC', '3':'A31', '4':'A28' }, { value: 'OLED' }));
placed.push(await place('J_US1', 'HC-SR04', 6800, 2500, { '1':'+5V', '2':'A08', '3':'A09', '4':'GND' }, { value: '超声波模块' }));

placed.push(await place('Q1', 'SI2302', 9000, 1150, { '1':'B17', '2':'GND', '3':'BUZZER_SW' }, { value: 'SI2302' }));
placed.push(await place('BUZZER1', '3kHz 蜂鸣器', 10400, 1150, { '1':'+5V', '2':'BUZZER_SW' }, { value: '3kHz蜂鸣器' }).catch(async e => {
  return await place('BUZZER1', '蜂鸣器', 10400, 1150, { '1':'+5V', '2':'BUZZER_SW' }, { value: '蜂鸣器' });
}));
placed.push(await place('R1', '0603 10K', 11800, 1000, { '1':'B17', '2':'GND' }, { value: '10K', pick: 0 }).catch(async e => place('R1', '10K R0603', 11800, 1000, { '1':'B17','2':'GND' }, { value: '10K' })));
placed.push(await place('R2', '0603 510R', 11800, 1650, { '1':'B27', '2':'LED_A' }, { value: '510R' }).catch(async e => place('R2', '510R', 11800, 1650, { '1':'B27','2':'LED_A' }, { value: '510R' })));
placed.push(await place('LED1', 'LED 0805', 13200, 1650, { '1':'LED_A', '2':'3V3' }, { value: 'LED' }));

placed.push(await place('K1', '按键 2P', 9000, 2600, { '1':'A26', '2':'GND' }, { value: '按键A26' }).catch(async e => place('K1', '轻触开关 2P', 9000, 2600, { '1':'A26','2':'GND' }, { value: '按键A26' })));
placed.push(await place('K2', '按键 2P', 10400, 2600, { '1':'A25', '2':'GND' }, { value: '按键A25' }).catch(async e => place('K2', '轻触开关 2P', 10400, 2600, { '1':'A25','2':'GND' }, { value: '按键A25' })));

placed.push(await place('U_TB1', 'TB6612FNG', 5200, 4500, {
  '1':'B15','2':'A12','3':'A13','4':'VCC','5':'B00','6':'B01','7':'B16','8':'GND',
  '9':'VM','10':'+5V','11':'GND','12':'AO1','13':'AO2','14':'BO2','15':'BO1','16':'GND',
}, { value: 'TB6612FNG' }));
placed.push(await place('J_MA', 'BX-XH2.54-6PWZ', 7600, 4100, { '1':'AO1', '2':'GND', '3':'A15', '4':'A16', '5':'AO2', '6':'+5V' }, { value: 'Motor-A' }));
placed.push(await place('J_MB', 'BX-XH2.54-6PWZ', 7600, 5200, { '1':'BO2', '2':'GND', '3':'A17', '4':'A24', '5':'BO1', '6':'+5V' }, { value: 'Motor-B' }));
placed.push(await place('C1', '0.1uF 0603', 9400, 4100, { '1':'+5V', '2':'GND' }, { value: '0.1uF' }));
placed.push(await place('C2', '0.1uF 0603', 9400, 5200, { '1':'+5V', '2':'GND' }, { value: '0.1uF' }));

// Generic headers for external modules where the exact module connector symbol is preferred over sensor body.
placed.push(await place('J_BT1', 'HMT-2.54-1*4PM', 11200, 3600, { '1':'B06', '2':'B07', '3':'GND', '4':'+5V' }, { value: '蓝牙接口' }).catch(async e => place('J_BT1', 'HEADER_1*4P_XH2.54', 11200, 3600, { '1':'B06','2':'B07','3':'GND','4':'+5V' }, { value: '蓝牙接口' })));
placed.push(await place('J_CAM1', 'HMT-2.54-1*4PM', 13200, 3600, { '1':'B03', '2':'B02', '3':'GND', '4':'+5V' }, { value: '摄像头串口' }).catch(async e => place('J_CAM1', 'HEADER_1*4P_XH2.54', 13200, 3600, { '1':'B03','2':'B02','3':'GND','4':'+5V' }, { value: '摄像头串口' })));
placed.push(await place('SERVO1', '1x3 2.54', 11200, 4700, { '1':'B09', '2':'+5V', '3':'GND' }, { value: '舵机1' }).catch(async e => place('SERVO1', 'HDR-TH_1X3', 11200, 4700, { '1':'B09','2':'+5V','3':'GND' }, { value: '舵机1' })));
placed.push(await place('SERVO2', '1x3 2.54', 13200, 4700, { '1':'B08', '2':'+5V', '3':'GND' }, { value: '舵机2' }).catch(async e => place('SERVO2', 'HDR-TH_1X3', 13200, 4700, { '1':'B08','2':'+5V','3':'GND' }, { value: '舵机2' })));

placed.push(await place('J_TRACK1', '1x10 2.54', 11200, 6200, { '1':'+5V','2':'GND','3':'B25','4':'B24','5':'B20','6':'A14','7':'B18','8':'B19','9':'B10','10':'A07' }, { value: '循迹10P' }).catch(async e => place('J_TRACK1', 'HDR-TH_1X10', 11200, 6200, { '1':'+5V','2':'GND','3':'B25','4':'B24','5':'B20','6':'A14','7':'B18','8':'B19','9':'B10','10':'A07' }, { value: '循迹10P' })));

await text(500, 7600, '说明：U5 电源模块、U9 陀螺仪模块、供电桩等若要完全还原，需要指定实际模块型号/封装；当前已优先放置 PDF 中可明确匹配的真实库器件。', 62, '#666666');

try { await eda.sys_ToastMessage.showMessage('真实器件/封装版已生成，请核对引脚'); } catch(e) {}
return { ok: true, deleted, placed };
