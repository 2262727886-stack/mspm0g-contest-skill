#include "button.h"

#define BUTTON_DEBOUNCE_MS  30U

void button_init(Button *btn, uint32_t now_ms)
{
    btn->stable_pressed = false;
    btn->last_raw_pressed = false;
    btn->changed_ms = now_ms;
}

bool button_update_pressed_event(Button *btn, bool raw_pressed, uint32_t now_ms)
{
    if (raw_pressed != btn->last_raw_pressed) {
        btn->last_raw_pressed = raw_pressed;
        btn->changed_ms = now_ms;
    }

    if ((now_ms - btn->changed_ms) < BUTTON_DEBOUNCE_MS) {
        return false;
    }

    if (raw_pressed != btn->stable_pressed) {
        btn->stable_pressed = raw_pressed;
        return raw_pressed;
    }

    return false;
}
