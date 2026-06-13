/**
 * button.h — 按键去抖模块
 *
 * 软件去抖原理:
 *   检测到电平变化后, 等待 BUTTON_DEBOUNCE_MS (30ms) 再确认。
 *   如果 30ms 内电平又变回去, 认为是抖动, 忽略。
 *
 * 使用方式:
 *   主循环每次调用 button_update_pressed_event(), 返回 true 表示
 *   按键刚按下 (上升沿事件, 不是持续按住)。
 */
#ifndef BUTTON_H
#define BUTTON_H

#include <stdbool.h>
#include <stdint.h>

/**
 * 按键去抖状态
 */
typedef struct {
    bool stable_pressed;     /* 去抖后的稳定状态 */
    bool last_raw_pressed;   /* 上次原始电平 */
    uint32_t changed_ms;     /* 上次电平变化时间 */
} Button;

/**
 * 初始化按键状态
 */
void button_init(Button *btn, uint32_t now_ms);

/**
 * 更新按键状态, 返回按下事件
 *
 * @param btn           按键状态指针
 * @param raw_pressed   当前原始电平 (true=按下)
 * @param now_ms        当前毫秒时间戳
 * @return              true = 按键刚按下 (只返回一次)
 */
bool button_update_pressed_event(Button *btn, bool raw_pressed, uint32_t now_ms);

#endif /* BUTTON_H */
