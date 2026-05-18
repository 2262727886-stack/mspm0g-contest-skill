################################################################################
# Automatically-generated file. Do not edit!
################################################################################

SHELL = cmd.exe

# Each subdirectory must supply rules for building sources it contributes
BSP/src/%.o: ../BSP/src/%.c $(GEN_OPTS) | $(GEN_FILES) $(GEN_MISC_FILES)
	@echo 'Building file: "$<"'
	@echo 'Invoking: Arm Compiler'
	"F:/Ti/CCS/ccs/tools/compiler/ti-cgt-armllvm_4.0.0.LTS/bin/tiarmclang.exe" -c @"device.opt"  -march=thumbv6m -mcpu=cortex-m0plus -mfloat-abi=soft -mlittle-endian -mthumb -O2 -I"C:/Users/Administrator/Desktop/TMX_MSPM0G3507_ProjectTemplate" -I"C:/Users/Administrator/Desktop/TMX_MSPM0G3507_ProjectTemplate/Board" -I"C:/Users/Administrator/Desktop/TMX_MSPM0G3507_ProjectTemplate/BSP" -I"C:/Users/Administrator/Desktop/TMX_MSPM0G3507_ProjectTemplate/BSP/inc" -I"C:/Users/Administrator/Desktop/TMX_MSPM0G3507_ProjectTemplate/Debug" -I"C:/ti/mspm0_sdk_2_02_00_05/source/third_party/CMSIS/Core/Include" -I"C:/ti/mspm0_sdk_2_02_00_05/source" -gdwarf-3 -MMD -MP -MF"BSP/src/$(basename $(<F)).d_raw" -MT"$(@)"  $(GEN_OPTS__FLAG) -o"$@" "$<"
	@echo 'Finished building: "$<"'
	@echo ' '


