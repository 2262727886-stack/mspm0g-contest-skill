@echo off
rem MSPM0G3507 快速编译+烧录 — 跳过验证
rem 用法: fast_flash.bat
setlocal enabledelayedexpansion

set PROJ=C:\Users\Administrator\workspace_ccstheia\test_1
set CC=C:\ti\ccs2020\ccs\tools\compiler\ti-cgt-armllvm_4.0.3.LTS\bin\tiarmclang.exe
set DSLITE=C:\ti\uniflash_9.5.0\deskdb\content\TICloudAgent\win\ccs_base\DebugServer\bin\DSLite.exe
set CCXML=C:\ti\uniflash_9.5.0\deskdb\content\TICloudAgent\win\scripting\examples\debugger\mspm0g3507\mspm0g3507.ccxml
set SDK=C:\ti\mspm0_sdk_2_10_00_04\source

cd /d "%PROJ%\Debug"

rem === 编译改动文件 ===
for %%s in (empty encoder motor pid) do (
    if "..\%%s.c" is newer than "%%s.o" (
        echo CC %%s.c
        "%CC%" -c @"device.opt" -march=thumbv6m -mcpu=cortex-m0plus -mfloat-abi=soft -mlittle-endian -mthumb -O2 -I"%PROJ%" -I"%PROJ%\Debug" -I"%SDK%\third_party\CMSIS\Core\Include" -I"%SDK%" -gdwarf-3 -Wall -o"%%s.o" "..\%%s.c" 2>nul
    )
)

rem === 链接 ===
echo LINK
"%CC%" @"device.opt" -march=thumbv6m -mcpu=cortex-m0plus -mfloat-abi=soft -mlittle-endian -mthumb -O2 -Wl,--rom_model -o "test_1.out" empty.o ti_msp_dl_config.o startup_mspm0g350x_ticlang.o encoder.o motor.o pid.o -Wl,-l"device_linker.cmd" -Wl,-ldevice.cmd.genlibs -Wl,-llibc.a 2>nul

rem === 烧录 ===
echo FLASH
"%DSLITE%" flash -c "%CCXML%" -s "AutoResetOnConnect=true" -s "VerifyAfterProgramLoad=2" "test_1.out" 2>&1 | findstr /C:"Success" /C:"Failed" /C:"error"

echo DONE
