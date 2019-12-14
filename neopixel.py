#!/usr/bin/env python3

import os
import time
import json
import _rpi_ws281x as ws
import paho.mqtt.client as paho

LED_GPIO       = os.getenv('LED_GPIO')
LED_COUNT      = os.getenv('LED_COUNT') 
LED_CHANNEL    = os.getenv('LED_CHANNEL', 0)
LED_FREQ_HZ    = os.getenv('LED_FREQ_HZ', 800000)
LED_DMA_NUM    = os.getenv('LED_DMA_NUM', 10)
LED_BRIGHTNESS = os.getenv('LED_BRIGHTNESS', 255)
LED_INVERT     = os.getenv('LED_INVERT', 0)

MQTT_BROKER   = os.getenv('MQTT_BROKER', 'localhost')
MQTT_USER     = os.getenv('MQTT_USER', None)
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', None)
MQTT_PORT     = os.getenv('MQTT_PORT', 1883)
MQTT_QOS      = os.getenv('MQTT_QOS', 1)
MQTT_ID       = os.getenv('MQTT_ID', 'rpi-ws281x')
MQTT_PREFIX   = os.getenv('MQTT_PREFIX', 'rpi-ws281x')
MQTT_DISCOVERY_PREFIX = os.getenv('MQTT_DISCOVERY_PREFIX', 'homeassistant')

MQTT_STATUS_TOPIC  = MQTT_PREFIX + "/alive"
MQTT_STATE_TOPIC   = MQTT_PREFIX + "/state"
MQTT_COMMAND_TOPIC = MQTT_PREFIX + "/command"
MQTT_CONFIG_TOPIC  = MQTT_DISCOVERY_PREFIX + "/light/" + MQTT_PREFIX + "/config"

color = 0x000000
effect = "None"

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

discovery_data = json.dumps({
    "name": MQTT_ID,
    "schema":"json",
    "command_topic": MQTT_COMMAND_TOPIC,
    "state_topic": MQTT_STATE_TOPIC,
    "availability_topic": MQTT_STATUS_TOPIC,
    "payload_available": "1",
    "payload_not_available": "0",
    "qos": MQTT_QOS,
    "brightness": False,
    "rgb": True,
    "white_value": False,
    "color_temp": False,
    "effect": True,
    "effect_list": ["None", "Knight Rider"],
})

def on_mqtt_message(mqtt, data, message):
    payload = json.loads(str(message.payload.decode("utf-8")))
    print("Message received ", payload)

    response = None
    global color, effect

    if payload["state"] == "ON":
        if "effect" in payload:
            effect = payload["effect"]
            print("Setting new effect: \"%s\"" % payload["effect"])

        if "color" in payload:
            color = 0
            color += payload["color"]["b"]
            color += payload["color"]["g"] << 8
            color += payload["color"]["r"] << 16
            print("Setting new color: 0x%06X" % color)

        elif color == 0:
            color = 0xFFFFFF

        response = json.dumps({
            "state": "ON",
            "color": {
                "r": (color >> 16) & 0xFF,
                "g": (color >> 8) & 0xFF,
                "b": color & 0xFF
            },
            "effect": effect
        })

    elif payload["state"] == "OFF":
        color = 0x000000;
        response = json.dumps({"state": "OFF"})

    if response is not None:
        mqtt.publish(MQTT_STATE_TOPIC, payload=response, qos=MQTT_QOS, retain=True)

def on_mqtt_connect(mqtt, userdata, flags, rc):
    mqtt.subscribe(MQTT_COMMAND_TOPIC)
    mqtt.publish(MQTT_STATUS_TOPIC, payload="1", qos=MQTT_QOS, retain=True)
    mqtt.publish(MQTT_CONFIG_TOPIC, payload=discovery_data, qos=MQTT_QOS, retain=True)

    if color > 0:
        response = json.dumps({
            "state": "ON",
            "color": {
                "r": (color >> 16) & 0xFF,
                "g": (color >> 8) & 0xFF,
                "b": color & 0xFF
            },
            "effect": effect
        })

    else:
        response = json.dumps({"state": "OFF"})

    mqtt.publish(MQTT_STATE_TOPIC, payload=response, qos=MQTT_QOS, retain=True)

print("Setting up %d LEDS on pin %d" %(LED_COUNT, LED_GPIO))
  
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
else:
    print("Setup of WS281x successfull")


mqtt = paho.Client(MQTT_ID)

mqtt.on_message = on_mqtt_message
mqtt.on_connect = on_mqtt_connect

mqtt.will_set(MQTT_STATUS_TOPIC, payload="0", qos=MQTT_QOS, retain=True)
mqtt.username_pw_set(MQTT_USER, MQTT_PASSWORD)
mqtt.connect(MQTT_BROKER, MQTT_PORT)
mqtt.loop_start()

try:
    while True:
        for i in range(LED_COUNT):
            ws.ws2811_led_set(channel, i, color)

        resp = ws.ws2811_render(leds)

        if resp != ws.WS2811_SUCCESS:
            message = ws.ws2811_get_return_t_str(resp)
            raise RuntimeError('ws2811_render failed with code {0} ({1})'.format(resp, message))

        time.sleep(5.0)

finally:
    mqtt.disconnect()
    mqtt.loop_stop()

    ws.ws2811_fini(leds)
    ws.delete_ws2811_t(leds)
