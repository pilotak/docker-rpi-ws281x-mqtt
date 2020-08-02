#!/usr/bin/env python3

import json
import multiprocessing
import os
import paho.mqtt.client as paho
import time
from rpi_ws281x import Color
from rpi_ws281x import Adafruit_NeoPixel
from effects import theaterChaseRainbow
from effects import rainbowCycle

LED_GPIO = os.getenv('LED_GPIO', 18)
LED_COUNT = os.getenv('LED_COUNT', 300)
LED_CHANNEL = os.getenv('LED_CHANNEL', 0)
LED_FREQ_HZ = os.getenv('LED_FREQ_HZ', 800000)
LED_DMA_NUM = os.getenv('LED_DMA_NUM', 10)
LED_BRIGHTNESS = os.getenv('LED_BRIGHTNESS', 255)
LED_INVERT = os.getenv('LED_INVERT', 0)

MQTT_BROKER = os.getenv('MQTT_BROKER', 'localhost')
MQTT_USER = os.getenv('MQTT_USER', None)
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', None)
MQTT_PORT = os.getenv('MQTT_PORT', 1883)
MQTT_QOS = os.getenv('MQTT_QOS', 1)
MQTT_ID = os.getenv('MQTT_ID', 'rpi-ws281x')
MQTT_PREFIX = os.getenv('MQTT_PREFIX', 'rpi-ws281x')
MQTT_DISCOVERY_PREFIX = os.getenv('MQTT_DISCOVERY_PREFIX', 'homeassistant')

MQTT_STATUS_TOPIC = "%s/alive" % MQTT_PREFIX
MQTT_STATE_TOPIC = "%s/state" % MQTT_PREFIX
MQTT_COMMAND_TOPIC = "%s/command" % MQTT_PREFIX
MQTT_CONFIG_TOPIC = "%s/light/%s/config" % (MQTT_DISCOVERY_PREFIX, MQTT_PREFIX)

color = 0x000000
state = False
effect = "None"

# worker process that maintains running effects
effect_process = None
effect_active = False

PAYLOAD_STATE_ON = 'ON'
PAYLOAD_STATE_OFF = 'OFF'

STATE_ON = True
STATE_OFF = False

EFFECT_NO_EFFECT = "none"
EFFECT_THEATER_RAINBOW = "Theater Rainbow"
EFFECT_RAINBOW = "Rainbow"
EFFECT_KNIGHT_RIDER = "Knight Rider"

effects_list = [EFFECT_THEATER_RAINBOW, EFFECT_RAINBOW]
color_effects_list = [EFFECT_KNIGHT_RIDER, EFFECT_NO_EFFECT]

if LED_COUNT is None:
    raise ValueError('LED_COUNT is required env parameter')

if LED_GPIO is None:
    raise ValueError('LED_GPIO is required env parameter')

LED_CHANNEL = int(LED_CHANNEL)
LED_COUNT = int(LED_COUNT)
LED_FREQ_HZ = int(LED_FREQ_HZ)
LED_DMA_NUM = int(LED_DMA_NUM)
LED_GPIO = int(LED_GPIO)
LED_BRIGHTNESS = int(LED_BRIGHTNESS)
LED_INVERT = int(LED_INVERT)

if LED_BRIGHTNESS > 255 or LED_BRIGHTNESS < 1:
    raise ValueError('LED_BRIGHTNESS must be between 1-255')

if LED_FREQ_HZ != 800000 and LED_FREQ_HZ != 400000:
    raise ValueError('LED_FREQ_HZ must be 800khz or 400khz')

if LED_DMA_NUM > 14 or LED_DMA_NUM < 0:
    raise ValueError('LED_DMA_NUM must be between 0-14')

discovery_data = json.dumps({
    "name": MQTT_ID,
    "schema": "json",
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
    "effect_list": effects_list + color_effects_list,
})


def get_bright_color(red, green, blue, relative_brightness):
    # takes a color and the desired new relative brightness in percent

    new_red = int(red * relative_brightness)
    new_green = int(green * relative_brightness)
    new_blue = int(blue * relative_brightness)

    new_color = (new_red << 16) + (new_green << 8) + new_blue

    return new_color


def knight_rider(strip, red, green, blue, effect_seconds=2, offset=0, step=2):
    # mandatory: R,G,B intensity values
    # optionally:
    #   effect_seconds: desired effect duration (roughly) in seconds for passing the entire LED strip once
    #   NOTE: ws2812 can only be updated ~83 times per second, for higher effect speed use the step parameter
    #   offset: exclude all LEDs before that LED number
    #   step: shift the effect these many LEDs forward during each iteration
    global strip
    wait_ms = 1000 * effect_seconds / (LED_COUNT-offset)

    for i in range(0+offset, LED_COUNT):
        strip.setPixelColor(i, get_bright_color(red, green, blue, 0.01))
    strip.show()
    for i in range(2+offset, LED_COUNT-2):
        start_ms = int(round(time.time() * 1000))
        strip.setPixelColor(i-2, get_bright_color(red, green, blue, 0.1))
        strip.setPixelColor(i-1, get_bright_color(red, green, blue, 0.5))
        strip.setPixelColor(i, get_bright_color(red, green, blue, 1.0))
        strip.setPixelColor(i+1, get_bright_color(red, green, blue, 0.5))
        strip.setPixelColor(i+2, get_bright_color(red, green, blue, 0.1))
        if i % step == 0:
            strip.show()
        end_ms = int(round(time.time() * 1000))
        diff_ms = wait_ms - round(end_ms - start_ms)
        if diff_ms > 0:
            time.sleep(diff_ms/1000.0)
        strip.setPixelColor(i-2, get_bright_color(red, green, blue, 0.01))
    for i in range(LED_COUNT-2, 2+offset, -1):
        start_ms = int(round(time.time() * 1000))
        strip.setPixelColor(i+2, get_bright_color(red, green, blue, 0.1))
        strip.setPixelColor(i+1, get_bright_color(red, green, blue, 0.5))
        strip.setPixelColor(i, get_bright_color(red, green, blue, 1.0))
        strip.setPixelColor(i-1, get_bright_color(red, green, blue, 0.5))
        strip.setPixelColor(i-2, get_bright_color(red, green, blue, 0.1))
        if i % step == 0:
            strip.show()
        end_ms = int(round(time.time() * 1000))
        diff_ms = wait_ms - round(end_ms - start_ms)
        if diff_ms > 0:
            time.sleep(diff_ms/1000.0)
        strip.setPixelColor(i+2, get_bright_color(red, green, blue, 0.01))


def apply_plain_color(new_color):
    red_intensity = new_color["r"]
    green_intensity = new_color["g"]
    blue_intensity = new_color["b"]
    color = 0
    color += blue_intensity
    color += (green_intensity << 8)
    color += (red_intensity << 16)
    color_dict = {"r": red_intensity,
                    "g": green_intensity,
                    "b": blue_intensity}
    set_all_leds_color(color)
    return color_dict

def apply_effect(new_effect, new_color):
    global effect_process, state, effect
    result_dict = {}
    effect = new_effect
    color = new_color
    # terminate active effect
    if effect_active:
        effect_process.terminate()
        effect_active = False
    # power on led strip
    if state == STATE_ON:
        result_dict["state"] = "ON"
        # effects without specific color, e.g. rainbow
        # TODO unify effects + plain color in one implementation with effect_function and default effect 'none'
        if new_effect == EFFECT_NO_EFFECT:
            color_dict = apply_plain_color(new_color)
            result_dict["color"] = color_dict
            effect_active = False
        else:
            if effect in effects_list:
                if new_effect == EFFECT_RAINBOW:
                    effect_process = multiprocessing.Process(
                        target=loop_function_call, args=(rainbowCycle, 30))
                elif new_effect == EFFECT_THEATER_RAINBOW:
                    effect_process = multiprocessing.Process(
                        target=loop_function_call, args=(theaterChaseRainbow, strip, 30))
                effect_process.start()
                effect_active = True
                print("Setting new effect: \"%s\"" % effect)
            else:
                print("Unsupported effect '%s'" % effect)

        elif color_payload:
            red_intensity = new_color["r"]
            green_intensity = new_color["g"]
            blue_intensity = new_color["b"]
            color = 0
            color += blue_intensity
            color += (green_intensity << 8)
            color += (red_intensity << 16)
            color_dict = {"r": red_intensity,
                          "g": green_intensity,
                          "b": blue_intensity}
            result_dict["color"] = color_dict

            # effects with specific color, e.g. knight rider
            if effect != EFFECT_NO_EFFECT:

                if effect in color_effects_list:
                    print("Setting new color effect: \"%s\"" % effect)
                    effect_function = None
                    if effect == EFFECT_KNIGHT_RIDER:
                        effect_function = knight_rider
                    else:
                        error += "No implementation for color effect '%s' found" % effect
                    effect_process = multiprocessing.Process(target=loop_function_call,
                                                             args=(effect_function, strip, red_intensity,
                                                                   green_intensity, blue_intensity))
                    effect_process.start()
                    effect_active = True
                else:
                    error += "Unsupported color effect '%s'\n" % effect
                    if effect in effects_list:
                        error += "This effect is only supported without the 'color' field\n"
            # plain color
            else:
                print("Setting new color: 0x%06X" % color)
                set_all_leds_color(strip, color)

        # neither color nor effect was requested
        else:
            print("Invalid request: A color or an effect has to be provided")

    # power off led strip
    elif state == False:
        result_dict["state"] = "OFF"
        all_leds_off(strip)
    return result_dict


def on_mqtt_message(mqtt, data, message):
    payload = json.loads(str(message.payload.decode("utf-8")))
    print("Message received ", payload)

    global color, effect_active, effect_process, effect, state
    response_dict = {}
    error = ''

    if "state" in payload:
        if payload["state"] == PAYLOAD_STATE_ON:
            state = STATE_ON
        elif payload["state"] == PAYLOAD_STATE_OFF:
            state = STATE_OFF
        else:
            error += "Invalid request: Invalid value for 'state' field: '%s'\n" % payload["state"]
        new_effect = payload.get('effect', EFFECT_NO_EFFECT)
        new_color = payload.get('color', None)
        sub_response_dict = apply_effect(new_effect, new_color)
        for key in sub_response_dict:
            response_dict[key] = sub_response_dict[key]
    else:
        # no state provided
        response_dict["state"] = 'none'
        error += "Invalid request: Missing 'state' field\n"

    if error != '':
        response_dict["error"] = error
        print(error)

    response_json = json.dumps(response_dict)
    mqtt.publish(MQTT_STATE_TOPIC, payload=response_json,
                 qos=MQTT_QOS, retain=True)


def on_mqtt_connect(mqtt, userdata, flags, rc):
    print("MQTT connected")
    mqtt.subscribe(MQTT_COMMAND_TOPIC)
    mqtt.publish(MQTT_STATUS_TOPIC, payload="1", qos=MQTT_QOS, retain=True)
    mqtt.publish(MQTT_CONFIG_TOPIC, payload=discovery_data,
                 qos=MQTT_QOS, retain=True)

    if state and color > 0:
        response_dict = {
            "state": "ON",
            "color": {
                "r": (color >> 8) & 0xFF,
                "g": (color >> 16) & 0xFF,
                "b": color & 0xFF
            },
            "effect": effect
        }
    else:
        response_dict = {"state": "OFF"}

    response = json.dumps(response_dict)
    mqtt.publish(MQTT_STATE_TOPIC, payload=response, qos=MQTT_QOS, retain=True)


def set_all_leds_color(new_color):
    global strip
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, new_color)
    strip.show()


def all_leds_off():
    set_all_leds_color(0)


print("Setting up %d LEDS on pin %d" % (LED_COUNT, LED_GPIO))

global strip

# Create NeoPixel object with appropriate configuration.
strip = Adafruit_NeoPixel(LED_COUNT, LED_GPIO, LED_FREQ_HZ,
                          LED_DMA_NUM, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
# Intialize the library (must be called once before other functions).
strip.begin()

mqtt = paho.Client(MQTT_ID)

mqtt.on_message = on_mqtt_message
mqtt.on_connect = on_mqtt_connect

mqtt.will_set(MQTT_STATUS_TOPIC, payload="0", qos=MQTT_QOS, retain=True)
mqtt.username_pw_set(MQTT_USER, MQTT_PASSWORD)
mqtt.connect(MQTT_BROKER, MQTT_PORT)
mqtt.loop_start()


def loop_function_call(function, *args):
    while True:
        function(*args)


try:
    loop_function_call(time.sleep, 0.1)

except KeyboardInterrupt:
    pass

finally:
    all_leds_off()
    mqtt.disconnect()
    mqtt.loop_stop()
    try:
        effect_process.terminate()
    except AttributeError:
        pass
