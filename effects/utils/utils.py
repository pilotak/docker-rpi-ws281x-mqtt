#!/usr/bin/env python3

from rpi_ws281x import Color


def get_color(color, brightness):
    return Color(int(color['r'] * brightness / 255),
                 int(color['g'] * brightness / 255),
                 int(color['b'] * brightness / 255))


def set_all_leds_color(strip, new_color):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, new_color)
    strip.show()
