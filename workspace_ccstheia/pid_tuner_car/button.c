/**
 * button.c — 按键去抖实现
 *
 * 去抖算法:
 *   1. 检测电平变化 → 记录变化时间
 *   2. 等待 30ms (BUTTON_DEBOUNCE_MS)
 *   3. 30ms 后如果电平仍与变化时一致 → 确认为真实按键
 *   4. 只在状态从 "未按下" 变为 "按下" 时返回 true (边沿触发)
 */
#include "button.h"

/* 去抖时间 (ms), 按键机械抖动通常 <20ms */
#define BUTTON_DEBOUNCE_MS  30U

/**
 * 初始化按键状态 (全部清零)
 */
void button_init(Button *btn, uint32_t now_ms)
{
    btn->stable_pressed = false;
    btn->last_raw_pressed = false;
    btn->changed_ms = now_ms;
}

/**
 * 更新按键状态, 返回按下事件
 *
 * 返回 true 的条件 (全部满足):
 *   - 原始电平从 false 变为 true (边沿)
 *   - 变化后稳定了 30ms (去抖)
 *   - 上次返回 true 后已经松开过 (避免重复触发)
 */
bool button_update_pressed_event(Button *btn, bool raw_pressed, uint32_t now_ms)
{
    /* 检测电平变化, 记录时间 */
    if (raw_pressed != btn->last_raw_pressed) {
        btn->last_raw_pressed = raw_pressed;
        btn->changed_ms = now_ms;
    }

    /* 去抖: 变化后不满 30ms, 不确认 */
    if ((now_ms - btn->changed_ms) < BUTTON_DEBOUNCE_MS) {
        return false;
    }

    /* 确认稳定后, 检测 "未按下→按下" 的边沿 */
    if (raw_pressed != btn->stable_pressed) {
        btn->stable_pressed = raw_pressed;
        return raw_pressed;  /* 只在按下时返回 true */
    }

    return false;
}
