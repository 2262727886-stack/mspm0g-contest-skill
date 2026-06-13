################################################################################
# Automatically-generated file. Do not edit!
################################################################################

SHELL = cmd.exe

# Add inputs and outputs from these tool invocations to the build variables 
SYSCFG_SRCS += \
../empty.syscfg 

C_SRCS += \
../button.c \
../delay.c \
./ti_msp_dl_config.c \
C:/ti/mspm0_sdk_2_10_00_04/source/ti/devices/msp/m0p/startup_system_files/ticlang/startup_mspm0g350x_ticlang.c \
../encoder.c \
../main.c \
../motor.c \
../pid_tuner.c \
../speed_pid.c 

GEN_CMDS += \
./device_linker.cmd 

GEN_FILES += \
./device_linker.cmd \
./device.opt \
./ti_msp_dl_config.c 

C_DEPS += \
./button.d \
./delay.d \
./ti_msp_dl_config.d \
./startup_mspm0g350x_ticlang.d \
./encoder.d \
./main.d \
./motor.d \
./pid_tuner.d \
./speed_pid.d 

GEN_OPTS += \
./device.opt 

OBJS += \
./button.o \
./delay.o \
./ti_msp_dl_config.o \
./startup_mspm0g350x_ticlang.o \
./encoder.o \
./main.o \
./motor.o \
./pid_tuner.o \
./speed_pid.o 

GEN_MISC_FILES += \
./device.cmd.genlibs \
./ti_msp_dl_config.h \
./Event.dot 

OBJS__QUOTED += \
"button.o" \
"delay.o" \
"ti_msp_dl_config.o" \
"startup_mspm0g350x_ticlang.o" \
"encoder.o" \
"main.o" \
"motor.o" \
"pid_tuner.o" \
"speed_pid.o" 

GEN_MISC_FILES__QUOTED += \
"device.cmd.genlibs" \
"ti_msp_dl_config.h" \
"Event.dot" 

C_DEPS__QUOTED += \
"button.d" \
"delay.d" \
"ti_msp_dl_config.d" \
"startup_mspm0g350x_ticlang.d" \
"encoder.d" \
"main.d" \
"motor.d" \
"pid_tuner.d" \
"speed_pid.d" 

GEN_FILES__QUOTED += \
"device_linker.cmd" \
"device.opt" \
"ti_msp_dl_config.c" 

C_SRCS__QUOTED += \
"../button.c" \
"../delay.c" \
"./ti_msp_dl_config.c" \
"C:/ti/mspm0_sdk_2_10_00_04/source/ti/devices/msp/m0p/startup_system_files/ticlang/startup_mspm0g350x_ticlang.c" \
"../encoder.c" \
"../main.c" \
"../motor.c" \
"../pid_tuner.c" \
"../speed_pid.c" 

SYSCFG_SRCS__QUOTED += \
"../empty.syscfg" 


