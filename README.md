# Control WS281x connected on Raspberry Pi via MQTT
![Docker Build](https://github.com/pilotak/docker-rpi-ws281x-mqtt/workflows/docker%20build/badge.svg) ![Docker Pulls](https://img.shields.io/docker/pulls/pilotak/rpi-ws281x-mqtt) ![Docker Size](https://img.shields.io/docker/image-size/pilotak/rpi-ws281x-mqtt?color=orange)

This image is ready to be used in HomeAssistant - supports MQTT discovery, for all other purposes, please see topics used below.

For supported GPIOs please see [rpi-ws281x-python](https://github.com/rpi-ws281x/rpi-ws281x-python/blob/master/library/README.rst)

## Environmental variables
| Variable | | Default value | Allowed values |
| --- | --- | :---:| :---: |
| `LED_GPIO` | **required** | | |
| `LED_COUNT` | **required** | | |
| `LED_CHANNEL` | optional| 0 | |
| `LED_FREQ_HZ` | optional | 800000| 400000 or 800000 |
| `LED_DMA_NUM` | optional | 10 | 0-14 |
| `LED_BRIGHTNESS` | optional | 255 | 1-255 |
| `LED_INVERT` | optional | 0 | 0 or 1 |
| `MQTT_BROKER` | optional | 'localhost' | |
| `MQTT_USER` | optional | None | |
| `MQTT_PASSWORD` | optional | None | |
| `MQTT_PORT` | optional | 1883 | 1-65535 |
| `MQTT_QOS` | optional | 1 | 0-2 |
| `MQTT_ID` | optional | 'rpi-ws281x' | |
| `MQTT_PREFIX`  | optional | 'rpi-ws281x' | |
| `MQTT_DISCOVERY_PREFIX` | optional | 'homeassistant' | |


### `docker-compose.yml`
```yaml
version: "3.6"
services:
  mosquitto:
    container_name: mosquitto
    restart: always
    image: eclipse-mosquitto
    ports:
      - 1883:1883

  rpi_ws281x:
    container_name: rpi_ws281x
    restart: unless-stopped
    build: .
    privileged: true
    depends_on:
      - mosquitto
    environment:
      - LED_GPIO=18
      - LED_COUNT=167
      - MQTT_BROKER=mosquitto
      - MQTT_USER=user
      - MQTT_PASSWORD=123456
```

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
