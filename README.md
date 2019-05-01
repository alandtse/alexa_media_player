[Alexa Media Player Custom Component](https://github.com/keatontaylor/alexa_media_player) for homeassistant

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

# Installation and Configuration
Please see the [wiki.](https://github.com/keatontaylor/alexa_media_player/wiki/Installation-and-Configuration)

# Notable Additional Features
## Play Music
We can basically do anything a Alexa [Routine](https://www.amazon.com/gp/help/customer/display.html?nodeId=G202200080) can do.  You'll have to [discover specifics](https://github.com/keatontaylor/alexa_media_player/wiki/Sequence-Discovery), but here are some examples (and please help add them below!).
To play music using the `media_player.play_media` service, you have to define the media_content_type appropriately. Search the [forum](https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639/2055) for other examples.

## Text-to-Speech
For version 1.2.0 and above, can be provided via the [Notification Component](https://github.com/keatontaylor/alexa_media_player/wiki/Notification-Component) using `TTS` or `Announce`.

**The Media_Player UI will not work!**

## Online status of devices
Additional attribute to tell you if the Alexa device is online (extremely useful if you want to send a TTS after one has come back online (such as one in a vehicle)

## Last called device (versions >= 0.10.0)
Each device will report whether it is the `last_called` or not. This allows us to identify the device that was called according to the Alexa Activities API.

## Sequence commands (versions >= 1.0.0)
Alexa accepts certain pre-defined sequences and this is what provides TTS and play_media. This is now exposed through the `media_player.play_media service` when the `media_content_type` is set to `sequence`

Supported sequences (may be region specific):
* Alexa.Weather.Play
* Alexa.Traffic.Play
* Alexa.FlashBriefing.Play
* Alexa.GoodMorning.Play
* Alexa.GoodNight.Play
* Alexa.SingASong.Play
* Alexa.TellStory.Play
* Alexa.FunFact.Play
* Alexa.Joke.Play
* Alexa.Music.PlaySearchPhrase
* Alexa.Calendar.PlayTomorrow
* Alexa.Calendar.PlayToday
* Alexa.Calendar.PlayNext
* Alexa.CleanUp.Play
* Alexa.ImHome.Play

## Automation routines (versions >= 1.0.0)
Running Alexa automation routines is now supported.  Routines are tasks you can trigger through the Alexa App.
 Please create them using the Alexa [app](https://www.amazon.com/gp/help/customer/display.html?nodeId=G202200080) and ensure they are **enabled**.  This is now exposed through the media_player.play_media service when the `media_content_type` is set to `routine`

## Custom_updater (versions >= 1.1.0)
We now support [custom_updater](https://github.com/custom-components/custom_updater).

Add this to your configuration:
```yaml
custom_updater:
  component_urls:
# Released build
    - https://raw.githubusercontent.com/keatontaylor/alexa_media_player/master/custom_components.json
```

## Notification service (versions >= 1.2.0)
Please see [Notification Component](https://github.com/keatontaylor/alexa_media_player/wiki/Notification-Component).

# Further Documentation
Please see the [wiki](https://github.com/keatontaylor/alexa_media_player/wiki)

# Changelog
Use the commit history but we try to maintain this [wiki](https://github.com/keatontaylor/alexa_media_player/wiki/Changelog).

# License
[Apache-2.0](LICENSE). By providing a contribution, you agree the contribution is licensed under Apache-2.0. This is required for Home Assistant contributions.
