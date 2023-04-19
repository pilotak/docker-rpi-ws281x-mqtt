#!/usr/bin/env python3

import json
import multiprocessing
import os
import paho.mqtt.client as paho
import time
from rpi_ws281x import Color
from rpi_ws281x import Adafruit_NeoPixel, ws
from effects.utils.utils import *

from effects.theater_chase_rainbow import effect_theater_chase_rainbow
from effects.rainbow_cycle import effect_rainbow_cycle
from effects.solid import effect_solid
from effects.knight_rider import effect_knight_rider

LED_GPIO = os.getenv('LED_GPIO', 18)
LED_COUNT = os.getenv('LED_COUNT', 10)
LED_CHANNEL = os.getenv('LED_CHANNEL', 0)
LED_FREQ_HZ = os.getenv('LED_FREQ_HZ', 800000)
LED_DMA_NUM = os.getenv('LED_DMA_NUM', 10)
LED_BRIGHTNESS = os.getenv('LED_BRIGHTNESS', 255)
LED_INVERT = os.getenv('LED_INVERT', 0)
LED_STRIP_TYPE = os.getenv('LED_STRIP_TYPE', 'GRB').upper()

MQTT_BROKER = os.getenv('MQTT_BROKER', 'localhost')
MQTT_USER = os.getenv('MQTT_USER', None)
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', None)
MQTT_PORT = os.getenv('MQTT_PORT', 1883)
MQTT_QOS = os.getenv('MQTT_QOS', 1)
MQTT_ID = os.getenv('MQTT_ID', 'rpi-ws281x')
MQTT_PREFIX = os.getenv('MQTT_PREFIX', 'rpi-ws281x')
MQTT_DISCOVERY_PREFIX = os.getenv('MQTT_DISCOVERY_PREFIX',
                                  'homeassistant')

MQTT_STATUS_TOPIC = '%s/alive' % MQTT_PREFIX
MQTT_STATE_TOPIC = '%s/state' % MQTT_PREFIX
MQTT_COMMAND_TOPIC = '%s/command' % MQTT_PREFIX
MQTT_CONFIG_TOPIC = '%s/light/%s/config' % (MQTT_DISCOVERY_PREFIX,
                                            MQTT_PREFIX)

MQTT_PAYLOAD_ONLINE = '1'
MQTT_PAYLOAD_OFFLINE = '0'

# global states
current = {
    'state': 'OFF',
    'color': {'r': 255, 'g': 255, 'b': 255},
    'brightness': 255,
    'effect': 'effect_solid'
}

# worker process that maintains running effects
effect_process = None
effect_active = False

# key is actually a function name
effects_list = {
    'effects': {
        'effect_theater_chase_rainbow': 'Theater Rainbow',
        'effect_rainbow_cycle': 'Rainbow'
    },
    'color_effects': {
        'effect_solid': 'Solid',
        'effect_knight_rider': 'Knight Rider'
    }
}

strip_type_by_name = {
    "BGR": ws.WS2811_STRIP_BGR,
    "BRG": ws.WS2811_STRIP_BRG,
    "GBR": ws.WS2811_STRIP_GBR,
    "GRB": ws.WS2811_STRIP_GRB,
    "RBG": ws.WS2811_STRIP_RBG,
    "RGB": ws.WS2811_STRIP_RGB,
}

# error checking
LED_CHANNEL = int(LED_CHANNEL)
LED_COUNT = int(LED_COUNT)
LED_FREQ_HZ = int(LED_FREQ_HZ)
LED_DMA_NUM = int(LED_DMA_NUM)
LED_GPIO = int(LED_GPIO)
LED_BRIGHTNESS = int(LED_BRIGHTNESS)
LED_INVERT = int(LED_INVERT)
LED_STRIP_TYPE = strip_type_by_name.get(LED_STRIP_TYPE)

if LED_COUNT is None:
    raise ValueError('LED_COUNT is required env parameter')

if LED_GPIO is None:
    raise ValueError('LED_GPIO is required env parameter')

if not 1 <= LED_BRIGHTNESS <= 255:
    raise ValueError('LED_BRIGHTNESS must be between 1-255')

if LED_FREQ_HZ != 800000 and LED_FREQ_HZ != 400000:
    raise ValueError('LED_FREQ_HZ must be 800khz or 400khz')

if LED_DMA_NUM > 14 or LED_DMA_NUM < 0:
    raise ValueError('LED_DMA_NUM must be between 0-14')

if LED_STRIP_TYPE is None:
    raise ValueError('LED_STRIP_TYPE must be one of %s', ', '.join(strip_type_by_name.keys()))


def effect_list_string():
    global effects_list
    ret = []

    for effect_name in effects_list['effects'].values():
        ret.append(effect_name)

    for effect_name in effects_list['color_effects'].values():
        ret.append(effect_name)

    return ret


def get_fn(name):
    for (effect_fn, effect_name) in effects_list['effects'].items():
        if effect_name == name:
            return effect_fn

    for (effect_fn, effect_name) in effects_list['color_effects'].items():
        if effect_name == name:
            return effect_fn

    return None


def get_fn_pretty(fn):
    if effects_list['effects'].get(fn) is not None:
        return effects_list['effects'].get(fn)

    if effects_list['color_effects'].get(fn) is not None:
        return effects_list['color_effects'].get(fn)

    return None


def on_mqtt_message(mqtt, data, message):
    payload = json.loads(str(message.payload.decode('utf-8')))
    print('Message received ', payload)

    global current, effect_active, effect_process
    response = {}

    if payload['state'] == 'ON' or payload['state'] == 'OFF':
        if current['state'] != payload['state']:
            print("Turning %s" % payload['state'])

            # set global state
            current['state'] = payload['state']

        # terminate active effect
        if effect_active:
            effect_process.terminate()
            effect_active = False

        # power on led strip
        if current['state'] == 'ON':
            # extract fields from payload
            if 'effect' in payload:
                fn = get_fn(payload['effect'])

                if fn is None:
                    response['error'] = "Unsupported effect '%s'" % payload['effect']

                else:
                    # set global efect
                    current['effect'] = fn

            if 'brightness' in payload:
                if 0 <= payload['brightness'] <= 255:
                    # set global brightness
                    current['brightness'] = payload['brightness']
                else:
                    response['error'] = "Invalid brightness '%u'" % payload['brightness']

            if 'color' in payload:
                if ('r' in payload['color'] and 0 <= payload['color']['r'] <= 255) \
                    and ('g' in payload['color'] and 0 <= payload['color']['g'] <= 255) \
                        and ('b' in payload['color'] and 0 <= payload['color']['b'] <= 255):
                    # set global color
                    current['color'] = payload['color']
                else:
                    response['error'] = "Invalid color payload"

            response['effect'] = get_fn_pretty(current['effect'])
            response['brightness'] = current['brightness']
            response['color'] = current['color']

            # efects with color
            if current['effect'] in effects_list['color_effects']:
                print('Setting new color effect: "%s"' %
                      get_fn_pretty(current['effect']))

                effect_process = \
                    multiprocessing.Process(target=loop_function_call, args=(
                        current['effect'], strip, current['color'], current['brightness']))
                effect_process.start()
                effect_active = True

            # efects not dependant on the color
            elif current['effect'] in effects_list['effects']:
                print('Setting new effect: "%s"' %
                      get_fn_pretty(current['effect']))

                effect_process = \
                    multiprocessing.Process(target=loop_function_call,
                                            args=(current['effect'], strip, 30))
                effect_process.start()
                effect_active = True

            else:
                response['error'] = \
                    'Invalid request: A color or a valid effect has to be provided'

        else:
            set_all_leds_color(strip, 0x000000)

        response['state'] = current['state']

    else:
        response['state'] = 'none'
        response['error'] = "Invalid request: Missing/invalid 'state' field"

    if 'error' in response:
        print(response['error'])

        current['state'] = 'OFF'
        response['state'] = current['state']

    response = json.dumps(response)
    mqtt.publish(MQTT_STATE_TOPIC, payload=response, qos=MQTT_QOS,
                 retain=True)


def on_mqtt_connect(mqtt, userdata, flags, rc):
    if rc == 0:
        print('MQTT connected')

        discovery_data = json.dumps({
            'name': MQTT_ID,
            'schema': 'json',
            'command_topic': MQTT_COMMAND_TOPIC,
            'state_topic': MQTT_STATE_TOPIC,
            'availability_topic': MQTT_STATUS_TOPIC,
            'payload_available': MQTT_PAYLOAD_ONLINE,
            'payload_not_available': MQTT_PAYLOAD_OFFLINE,
            'qos': MQTT_QOS,
            'brightness': True,
            'rgb': True,
            'color_temp': False,
            'effect': True,
            'effect_list': effect_list_string(),
            'optimistic': False,
            'unique_id': MQTT_ID,
        })

        mqtt.subscribe(MQTT_COMMAND_TOPIC)
        mqtt.publish(MQTT_STATUS_TOPIC, payload=MQTT_PAYLOAD_ONLINE,
                     qos=MQTT_QOS, retain=True)
        mqtt.publish(MQTT_CONFIG_TOPIC, payload=discovery_data,
                     qos=MQTT_QOS, retain=True)

        if current['state'] == 'ON':
            response = {
                'state': current['state'],
                'color': current['color'],
                'effect': get_fn_pretty(current['effect']),
                'brightness': current['brightness']
            }
        else:
            response = {'state': current['state']}

        response = json.dumps(response)
        mqtt.publish(MQTT_STATE_TOPIC, payload=response, qos=MQTT_QOS,
                     retain=True)
    else:
        print('MQTT connect failed:', rc)


print('Setting up %d LEDS on pin %d' % (LED_COUNT, LED_GPIO))

# Create NeoPixel object with appropriate configuration.
strip = Adafruit_NeoPixel(
    LED_COUNT,
    LED_GPIO,
    LED_FREQ_HZ,
    LED_DMA_NUM,
    LED_INVERT,
    LED_BRIGHTNESS,
    LED_CHANNEL,
    LED_STRIP_TYPE
)

# Intialize the library (must be called once before other functions).
strip.begin()
set_all_leds_color(strip, 0x000000)

mqtt = paho.Client(MQTT_ID)

mqtt.on_message = on_mqtt_message
mqtt.on_connect = on_mqtt_connect

mqtt.will_set(MQTT_STATUS_TOPIC, payload=MQTT_PAYLOAD_OFFLINE,
              qos=MQTT_QOS, retain=True)
mqtt.username_pw_set(MQTT_USER, MQTT_PASSWORD)
mqtt.connect(MQTT_BROKER, MQTT_PORT)
mqtt.loop_start()


def loop_function_call(function, *args):
    while True:
        if isinstance(function, str):
            globals()[function](*args)
        else:
            function(*args)


try:
    loop_function_call(time.sleep, 0.1)
except KeyboardInterrupt:

    pass
finally:

    set_all_leds_color(strip, 0x000000)
    mqtt.disconnect()
    mqtt.loop_stop()
    try:
        effect_process.terminate()
    except AttributeError:
        pass
