#ifndef BUTTON_H
#define BUTTON_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    bool stable_pressed;
    bool last_raw_pressed;
    uint32_t changed_ms;
} Button;

void button_init(Button *btn, uint32_t now_ms);
bool button_update_pressed_event(Button *btn, bool raw_pressed, uint32_t now_ms);

#endif
