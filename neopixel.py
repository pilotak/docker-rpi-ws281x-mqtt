import os
import time
import _rpi_ws281x as ws

LED_GPIO       = os.getenv('LED_GPIO')
LED_COUNT      = os.getenv('LED_COUNT') 
LED_CHANNEL    = os.getenv('LED_CHANNEL') or 0
LED_FREQ_HZ    = os.getenv('LED_FREQ_HZ') or 800000
LED_DMA_NUM    = os.getenv('LED_DMA_NUM') or 10
LED_BRIGHTNESS = os.getenv('LED_BRIGHTNESS') or 255
LED_INVERT     = os.getenv('LED_INVERT') or 0

if LED_COUNT is None:
    raise ValueError('LED_COUNT is required env parameter')

if LED_GPIO is None:
    raise ValueError('LED_GPIO is required env parameter')

LED_CHANNEL    = int(LED_CHANNEL)
LED_COUNT      = int(LED_COUNT)
LED_FREQ_HZ    = int(LED_FREQ_HZ)
LED_DMA_NUM    = int(LED_DMA_NUM)
LED_GPIO       = int(LED_GPIO)
LED_BRIGHTNESS = int(LED_BRIGHTNESS)
LED_INVERT     = int(LED_INVERT)

if LED_BRIGHTNESS > 255 or LED_BRIGHTNESS < 1:
    raise ValueError('LED_BRIGHTNESS must be between 1-255')

if LED_FREQ_HZ != 800000 and LED_FREQ_HZ != 400000:
    raise ValueError('LED_FREQ_HZ must be 800khz or 400khz')

if LED_DMA_NUM > 14 or LED_DMA_NUM < 0:
    raise ValueError('LED_DMA_NUM must be between 0-14')

print("Setup of %d LEDS on pin %d" %(LED_COUNT, LED_GPIO))
  
leds = ws.new_ws2811_t()

for channum in range(2):
    channel = ws.ws2811_channel_get(leds, channum)
    ws.ws2811_channel_t_count_set(channel, 0)
    ws.ws2811_channel_t_gpionum_set(channel, 0)
    ws.ws2811_channel_t_invert_set(channel, 0)
    ws.ws2811_channel_t_brightness_set(channel, 0)

channel = ws.ws2811_channel_get(leds, LED_CHANNEL)

ws.ws2811_channel_t_count_set(channel, LED_COUNT)
ws.ws2811_channel_t_gpionum_set(channel, LED_GPIO)
ws.ws2811_channel_t_invert_set(channel, LED_INVERT)
ws.ws2811_channel_t_brightness_set(channel, LED_BRIGHTNESS)

ws.ws2811_t_freq_set(leds, LED_FREQ_HZ)
ws.ws2811_t_dmanum_set(leds, LED_DMA_NUM)

resp = ws.ws2811_init(leds)

if resp != ws.WS2811_SUCCESS:
    message = ws.ws2811_get_return_t_str(resp)
    raise RuntimeError('ws2811_init failed with code {0} ({1})'.format(resp, message))

try:
    while True:
        for i in range(LED_COUNT):
            ws.ws2811_led_set(channel, i, 0x000000)

        resp = ws.ws2811_render(leds)

        if resp != ws.WS2811_SUCCESS:
            message = ws.ws2811_get_return_t_str(resp)
            raise RuntimeError('ws2811_render failed with code {0} ({1})'.format(resp, message))
        time.sleep(5.0)

finally:
    ws.ws2811_fini(leds)
    ws.delete_ws2811_t(leds)
