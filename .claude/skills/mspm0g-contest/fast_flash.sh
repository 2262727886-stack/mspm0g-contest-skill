#!/bin/bash
# MSPM0G3507 快速编译+烧录 — 跳过验证，只编译改动文件
# 用法: ./fast_flash.sh
set -e

PROJ="C:/Users/Administrator/workspace_ccstheia/test_1"
CC="C:/ti/ccs2020/ccs/tools/compiler/ti-cgt-armllvm_4.0.3.LTS/bin/tiarmclang.exe"
DSLSITE="C:/ti/uniflash_9.5.0/deskdb/content/TICloudAgent/win/ccs_base/DebugServer/bin/DSLite.exe"
CCXML="C:/ti/uniflash_9.5.0/deskdb/content/TICloudAgent/win/scripting/examples/debugger/mspm0g3507/mspm0g3507.ccxml"
SDK="C:/ti/mspm0_sdk_2_10_00_04/source"

cd "$PROJ/Debug"

# 编译改动的 .c 文件
for src in ../empty.c ../encoder.c ../motor.c ../pid.c; do
    obj="./$(basename "${src%.c}.o")"
    if [ "$src" -nt "$obj" ]; then
        echo "CC $(basename $src)"
        "$CC" -c -D__MSPM0G3507__ -D__USE_SYSCONFIG__ \
            -march=thumbv6m -mcpu=cortex-m0plus -mfloat-abi=soft -mlittle-endian -mthumb -O2 \
            -I"$PROJ" -I"$PROJ/Debug" -I"$SDK/third_party/CMSIS/Core/Include" -I"$SDK" \
            -gdwarf-3 -Wall -o"$obj" "$src" 2>&1 | grep -E "error|Error" || true
    fi
done

# 链接
echo "LINK"
"$CC" -D__MSPM0G3507__ -D__USE_SYSCONFIG__ \
    -march=thumbv6m -mcpu=cortex-m0plus -mfloat-abi=soft -mlittle-endian -mthumb -O2 \
    -Wl,-i"$SDK" -Wl,-i"$PROJ" -Wl,-i"$PROJ/Debug/syscfg" \
    -Wl,-i"C:/ti/ccs2020/ccs/tools/compiler/ti-cgt-armllvm_4.0.3.LTS/lib" \
    -Wl,--rom_model -o "test_1.out" \
    ./empty.o ./ti_msp_dl_config.o ./startup_mspm0g350x_ticlang.o ./encoder.o ./motor.o ./pid.o \
    -Wl,-l"./device_linker.cmd" -Wl,-ldevice.cmd.genlibs -Wl,-llibc.a 2>&1 | grep -E "error|Error" || true

# 烧录
echo "FLASH"
"$DSLSITE" flash -c "$CCXML" -s "AutoResetOnConnect=true" -s "VerifyAfterProgramLoad=2" "./test_1.out" 2>&1 | grep -E "Success|Failed|error"
