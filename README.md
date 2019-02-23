[Alexa Media Player Custom Component](https://github.com/keatontaylor/custom_components) for homeassistant

# What This Is:
This is a custom component to allow control of Amazon Alexa devices in [Homeassistant](https://home-assistant.io) using the unofficial Alexa API. Please note this mimics the Alexa app but Amazon may cut off access at anytime.

# What It Does:
Allows for control of Amazon Echo products as home assistant media devices with the following features:

* Play/Pause/Stop
* Next/Previous (Track)
* Volume
* Retrieval for displaying in home assistant of:
  * Song Title
  * Artists Name
  * Album Name
  * Album Image

# Notable Additional Features
## Text-to-Speech
Can be invoked from the HA UI services menu. media_player.alexa_tts and requires a payload like this:

```json
{"entity_id": "media_player.bedroom_echo_dot", "message": "Test message"}
```

**The Home-Asistant Media_Player UI does not work!**

### Known working languages:
* US English
* [Italian](https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639/1334)
* [Mexican Spanish](https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639/1431)

## Online status of devices
Additional attribute to tell you if the Alexa device is online (extremely useful if you want to send a TTS after one has come back online (such as one in a vehicle)

## Last called device
Each device will report whether it is the `last_called` or not. This allows us to identify the device that was called according to the Alexa Activities API.

# Further Documentation
Please see the [wiki](https://github.com/keatontaylor/custom_components/wiki)

# Changelog
Use the commit history but we try to maintain this [wiki](https://github.com/keatontaylor/custom_components/wiki/Changelog).

# License
[Apache-2.0](LICENSE). By providing a contribution, you agree the contribution is licensed under Apache-2.0. This is required for Home Assistant contributions.
