# Control WS281x connected on Raspberry Pi via MQTT
For supported GPIOs please see [rpi-ws281x-python](https://github.com/rpi-ws281x/rpi-ws281x-python/blob/master/library/README.rst)

## Environmental variables
- `LED_GPIO` *(required)*
- `LED_COUNT` *(required)*
- `LED_CHANNEL` *(optional; default=0)*
- `LED_FREQ_HZ` *(optional; default=800000; 400000 or 800000)*
- `LED_DMA_NUM` *(optional; default=10; range=0-14)*
- `LED_BRIGHTNESS` *(optional; default=255; range=1-255)*
- `LED_INVERT` *(optional; default=0; 0 or 1)*
- `MQTT_BROKER` *(optional; default='localhost')*
- `MQTT_USER` *(optional; default=None*)
- `MQTT_PASSWORD` *(optional; default=None)*
- `MQTT_PORT` *(optional; default=1883; range=1-65535)*
- `MQTT_QOS` *(optional; default=1; range=0-2)*
- `MQTT_ID`   *(optional; default='rpi-ws281x')*
- `MQTT_PREFIX`  *(optional; default='rpi-ws281x')*
- `MQTT_DISCOVERY_PREFIX` *(optional; default='homeassistant')*


`docker-compose.yml`
```yaml
version: "3.6"
services:  
  rpi_ws281x:
    container_name: rpi_ws281x
    restart: always
    build: ./docker-homeassistant-ws281x
    privileged: true
    environment:
      - LED_GPIO=12
      - LED_COUNT=10
```

**This image is ready to be used in HomeAssistant - supports MQTT discovery, for all other purposes, please see topics used below**

## MQTT topics
### To set color
Send to topic: `rpi-ws281x/command`

*Note: `color` and `effect` are optional keys, you can send both or just one or none in which case last color selected is used.*
```json
{
    "state": "ON",
    "color": {
        "r": 0,
        "g": 255,
        "b": 0
    },
    "effect": "Knight Rider"
}
```

### To turn off
Send to topic: `rpi-ws281x/command`
```json
{
    "state": "OFF"
}
```

### Last state
Topic: `rpi-ws281x/state`
```json
{
    "state": "ON",
    "color": {
        "r": 255,
        "g": 109,
        "b": 109
    },
    "effect": "None"
}
```

### Availability
Topic: `rpi-ws281x/alive`
Response: `1` or `0`
