################################################################################
# Automatically-generated file. Do not edit!
################################################################################

SHELL = cmd.exe

# Each subdirectory must supply rules for building sources it contributes
%.o: ../%.c $(GEN_OPTS) | $(GEN_FILES) $(GEN_MISC_FILES)
	@echo 'Building file: "$<"'
	@echo 'Invoking: Arm Compiler'
	"F:/Ti/CCS/ccs/tools/compiler/ti-cgt-armllvm_4.0.0.LTS/bin/tiarmclang.exe" -c @"device.opt"  -march=thumbv6m -mcpu=cortex-m0plus -mfloat-abi=soft -mlittle-endian -mthumb -O2 -I"C:/Users/Administrator/Desktop/TMX_MSPM0G3507_ProjectTemplate" -I"C:/Users/Administrator/Desktop/TMX_MSPM0G3507_ProjectTemplate/Board" -I"C:/Users/Administrator/Desktop/TMX_MSPM0G3507_ProjectTemplate/BSP" -I"C:/Users/Administrator/Desktop/TMX_MSPM0G3507_ProjectTemplate/BSP/inc" -I"C:/Users/Administrator/Desktop/TMX_MSPM0G3507_ProjectTemplate/Debug" -I"C:/ti/mspm0_sdk_2_02_00_05/source/third_party/CMSIS/Core/Include" -I"C:/ti/mspm0_sdk_2_02_00_05/source" -gdwarf-3 -MMD -MP -MF"$(basename $(<F)).d_raw" -MT"$(@)"  $(GEN_OPTS__FLAG) -o"$@" "$<"
	@echo 'Finished building: "$<"'
	@echo ' '

build-306660031: ../empty.syscfg
	@echo 'Building file: "$<"'
	@echo 'Invoking: SysConfig'
	"C:/ti/sysconfig_1.21.0/sysconfig_cli.bat" --script "C:/Users/Administrator/Desktop/TMX_MSPM0G3507_ProjectTemplate/empty.syscfg" -o "." -s "C:/ti/mspm0_sdk_2_02_00_05/.metadata/product.json" --compiler ticlang
	@echo 'Finished building: "$<"'
	@echo ' '

device_linker.cmd: build-306660031 ../empty.syscfg
device.opt: build-306660031
device.cmd.genlibs: build-306660031
ti_msp_dl_config.c: build-306660031
ti_msp_dl_config.h: build-306660031
Event.dot: build-306660031

%.o: ./%.c $(GEN_OPTS) | $(GEN_FILES) $(GEN_MISC_FILES)
	@echo 'Building file: "$<"'
	@echo 'Invoking: Arm Compiler'
	"F:/Ti/CCS/ccs/tools/compiler/ti-cgt-armllvm_4.0.0.LTS/bin/tiarmclang.exe" -c @"device.opt"  -march=thumbv6m -mcpu=cortex-m0plus -mfloat-abi=soft -mlittle-endian -mthumb -O2 -I"C:/Users/Administrator/Desktop/TMX_MSPM0G3507_ProjectTemplate" -I"C:/Users/Administrator/Desktop/TMX_MSPM0G3507_ProjectTemplate/Board" -I"C:/Users/Administrator/Desktop/TMX_MSPM0G3507_ProjectTemplate/BSP" -I"C:/Users/Administrator/Desktop/TMX_MSPM0G3507_ProjectTemplate/BSP/inc" -I"C:/Users/Administrator/Desktop/TMX_MSPM0G3507_ProjectTemplate/Debug" -I"C:/ti/mspm0_sdk_2_02_00_05/source/third_party/CMSIS/Core/Include" -I"C:/ti/mspm0_sdk_2_02_00_05/source" -gdwarf-3 -MMD -MP -MF"$(basename $(<F)).d_raw" -MT"$(@)"  $(GEN_OPTS__FLAG) -o"$@" "$<"
	@echo 'Finished building: "$<"'
	@echo ' '

startup_mspm0g350x_ticlang.o: C:/ti/mspm0_sdk_2_02_00_05/source/ti/devices/msp/m0p/startup_system_files/ticlang/startup_mspm0g350x_ticlang.c $(GEN_OPTS) | $(GEN_FILES) $(GEN_MISC_FILES)
	@echo 'Building file: "$<"'
	@echo 'Invoking: Arm Compiler'
	"F:/Ti/CCS/ccs/tools/compiler/ti-cgt-armllvm_4.0.0.LTS/bin/tiarmclang.exe" -c @"device.opt"  -march=thumbv6m -mcpu=cortex-m0plus -mfloat-abi=soft -mlittle-endian -mthumb -O2 -I"C:/Users/Administrator/Desktop/TMX_MSPM0G3507_ProjectTemplate" -I"C:/Users/Administrator/Desktop/TMX_MSPM0G3507_ProjectTemplate/Board" -I"C:/Users/Administrator/Desktop/TMX_MSPM0G3507_ProjectTemplate/BSP" -I"C:/Users/Administrator/Desktop/TMX_MSPM0G3507_ProjectTemplate/BSP/inc" -I"C:/Users/Administrator/Desktop/TMX_MSPM0G3507_ProjectTemplate/Debug" -I"C:/ti/mspm0_sdk_2_02_00_05/source/third_party/CMSIS/Core/Include" -I"C:/ti/mspm0_sdk_2_02_00_05/source" -gdwarf-3 -MMD -MP -MF"$(basename $(<F)).d_raw" -MT"$(@)"  $(GEN_OPTS__FLAG) -o"$@" "$<"
	@echo 'Finished building: "$<"'
	@echo ' '


