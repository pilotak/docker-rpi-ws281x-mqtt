#!/usr/bin/env python3
# Author: Henning Häcker

import time
from effects.utils import utils


def effect_knight_rider(strip, color, brightness, effect_seconds=1, offset=0, step=2):
    # mandatory: R,G,B intensity values
    # optionally:
    #   effect_seconds: desired effect duration (roughly) in seconds for passing the entire LED strip once
    #   NOTE: ws2812 can only be updated ~83 times per second, for higher effect speed use the step parameter
    #   offset: exclude all LEDs before that LED number
    #   step: shift the effect these many LEDs forward during each iteration
    total_pixels = strip.numPixels()
    wait_ms = 1000 * effect_seconds / (total_pixels-offset)

    for i in range(0+offset, total_pixels):
        strip.setPixelColor(i, utils.get_color(color, 3))
    strip.show()
    for i in range(2+offset, total_pixels-2):
        start_ms = int(round(time.time() * 1000))
        strip.setPixelColor(i-2, utils.get_color(color, 26))
        strip.setPixelColor(i-1, utils.get_color(color, 127))
        strip.setPixelColor(i, utils.get_color(color, 255))
        strip.setPixelColor(i+1, utils.get_color(color, 127))
        strip.setPixelColor(i+2, utils.get_color(color, 26))
        if i % step == 0:
            strip.show()
        end_ms = int(round(time.time() * 1000))
        diff_ms = wait_ms - round(end_ms - start_ms)
        if diff_ms > 0:
            time.sleep(diff_ms/1000.0)
        strip.setPixelColor(i-2, utils.get_color(color, 3))
    for i in range(total_pixels-2, 2+offset, -1):
        start_ms = int(round(time.time() * 1000))
        strip.setPixelColor(i+2, utils.get_color(color, 26))
        strip.setPixelColor(i+1, utils.get_color(color, 127))
        strip.setPixelColor(i, utils.get_color(color, 255))
        strip.setPixelColor(i-1, utils.get_color(color, 127))
        strip.setPixelColor(i-2, utils.get_color(color, 26))
        if i % step == 0:
            strip.show()
        end_ms = int(round(time.time() * 1000))
        diff_ms = wait_ms - round(end_ms - start_ms)
        if diff_ms > 0:
            time.sleep(diff_ms/1000.0)
        strip.setPixelColor(i+2, utils.get_color(color, 3))
