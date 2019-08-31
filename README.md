[Alexa Media Player Custom Component](https://github.com/custom-components/alexa_media_player) for homeassistant

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
Please see the [wiki.](https://github.com/custom-components/alexa_media_player/wiki/Installation-and-Configuration)

# Notable Additional Features
## Play Music
We can basically do anything a Alexa [Routine](https://www.amazon.com/gp/help/customer/display.html?nodeId=G202200080) can do.  You'll have to [discover specifics](https://github.com/custom-components/alexa_media_player/wiki/Sequence-Discovery), but here are some examples (and please help add them below!).
To play music using the `media_player.play_media` service, you have to define the media_content_type appropriately. Search the [forum](https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639/2055) for other examples.

## Notification service (versions >= 1.2.0)
Please see [Notification Component](https://github.com/custom-components/alexa_media_player/wiki/Notification-Component) for TTS, announcements, or mobile push.
**Please note we do not support the the Media Player UI for TTS!**

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

## HACS - Home Assistant Community Store (versions >= 1.3.0)
We also support [HACS](https://custom-components.github.io/hacs/). **This cannot be used with custom_updater.**

In order to find Alexa Media Player, you first need to add the repository:
1. Open HACS
2. Go to Settings
3. Enter `https://github.com/custom-components/alexa_media_player`in **ADD CUSTOM REPOSITORY**. Select type `integration`.

## Guard Mode (versions >= 1.3.0)
Arm and disarm Alexa guard mode using an Alarm Control Panel. To arm, use `ARM_AWAY`.  `ARM_HOME` is the same as `DISARM`.  Please ensure you've enabled through the [Alexa app](https://www.amazon.com/b?ie=UTF8&node=18021383011).

We do not support any Guard notifications at the moment.

## Notification service (versions >= 1.2.0)
Please see [Notification Component](https://github.com/custom-components/alexa_media_player/wiki/Notification-Component).

# Further Documentation
Please see the [wiki](https://github.com/custom-components/alexa_media_player/wiki)

# Changelog
Use the commit history but we try to maintain this [wiki](https://github.com/custom-components/alexa_media_player/wiki/Changelog).

# License
[Apache-2.0](LICENSE). By providing a contribution, you agree the contribution is licensed under Apache-2.0. This is required for Home Assistant contributions.
