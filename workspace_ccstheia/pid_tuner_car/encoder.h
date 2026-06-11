#ifndef ENCODER_H
#define ENCODER_H

#include <stdint.h>

void encoder_init(void);
void encoder_sample_and_clear(int16_t *left_speed, int16_t *right_speed);

#endif
