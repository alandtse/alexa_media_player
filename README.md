[![Validate](https://github.com/alandtse/alexa_media_player/actions/workflows/validate.yaml/badge.svg)](https://github.com/alandtse/alexa_media_player/actions/workflows/validate.yaml)
![semantic_release](https://github.com/alandtse/alexa_media_player/workflows/semantic_release/badge.svg)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
![GitHub all releases](https://img.shields.io/github/downloads/alandtse/alexa_media_player/total)
![GitHub release (latest by SemVer)](https://img.shields.io/github/downloads/alandtse/alexa_media_player/latest/total)

[Alexa Media Player Custom Component](https://github.com/alandtse/alexa_media_player) for homeassistant

# What This Is:

This is a custom component to allow control of Amazon Alexa devices in [Home Assistant](https://home-assistant.io) using the unofficial Alexa API. Please note this mimics the Alexa app but Amazon may cut off access at anytime.

Originally inspired and created by [Keaton Taylor](https://github.com/keatontaylor)

# What It Does:

Allows for control of Amazon Echo products as home assistant media devices with the following features:

- Play/Pause/Stop
- Next/Previous (Track)
- Volume
- Retrieval for displaying in home assistant of:
  - Song Title
  - Artists Name
  - Album Name
  - Album Image

# Features

- Media player controls: play, pause, stop, next/previous, volume, mute,
  shuffle, repeat, Bluetooth source selection and media metadata.
- Send speech, announcements, mobile push notifications and drop-in
  notifications through `notify.alexa_media`.
- Run Alexa routines, skills, sounds and text commands from `play_media`.
- Next alarm, timer and reminder sensors with dismissal events.
- Do Not Disturb, shuffle and repeat switches; alarm and notification volume.
- Echo temperature, Amazon Indoor Air Quality Monitor sensors and Alexa Guard.
- Amazon Kids child-mode switch, select and binary sensor.
- Optional extended discovery of lights, smart plugs/switches, contact sensors
  and their battery levels through Alexa.
- Echo Show / Echo Dot with clock display power, brightness and adaptive
  brightness controls.
- Restart button for Echo devices that support remote reboot.

# Services

| Service | Description |
| --- | --- |
| `alexa_media.force_logout` | Mark one or all accounts for reauthentication. |
| `alexa_media.restore_volume` | Restore the previous volume of a media player. |
| `alexa_media.get_history_records` | Store recent voice-history records on a media player. |
| `alexa_media.update_last_called` | Refresh which Echo received the last voice command. |
| `alexa_media.enable_network_discovery` | Re-run Alexa network discovery. |
| `alexa_media.amazon_kids_enable` | Assign an Echo to an Amazon Kids child profile. |
| `alexa_media.amazon_kids_disable` | Release an Echo from Amazon Kids. |

# Events

- `alexa_media_voice_command`: fired for each new voice-history record with the
  command, response and timestamp.
- `alexa_media_alarm_dismissal_event`: fired when an alarm is dismissed.
- `alexa_media_notification_event`: fired when an alarm, timer or reminder is
  due.

There are no integration-specific conditions.

# Installation and Configuration

Install through HACS or copy `custom_components/alexa_media` into your Home
Assistant configuration directory, restart Home Assistant, then add the
integration from **Settings > Devices & services**. You need an Amazon account
with access to the Alexa devices. If two-step verification is enabled, have the
authenticator key or the current OTP ready.

Detailed configuration options are documented in the
[wiki](https://github.com/alandtse/alexa_media_player/wiki/Configuration).

# Removal

1. Remove the integration from **Settings > Devices & services**.
2. Remove the `alexa_media` custom component directory.
3. Restart Home Assistant.

The integration stores its login cookies under `.storage/alexa_media.*.cookies`.
Removing the config entry removes its runtime entities; delete the cookie files
manually if you also want to discard the Amazon session.

# Further Documentation

Please see the [wiki](https://github.com/alandtse/alexa_media_player/wiki)

# Changelog

Please reference the [release history](https://github.com/alandtse/alexa_media_player/releases).

# How to Help

While it'd be nice to have more developers, you can contribute without knowing how to code. You can [file bugs/feature requests](https://github.com/alandtse/alexa_media_player/issues), help answer questions here and on the HA [forums](https://community.home-assistant.io/t/echo-devices-alexa-as-media-player-testers-needed/58639), or you can help with other tasks like [translations](##translations) and updating the [wiki](https://github.com/alandtse/alexa_media_player/wiki).

## Translations

We are now on [Lokalise](https://app.lokalise.com/project/465185555eee18dd537ca6.39714580/). If you're a native speaker, please [join the team](https://app.lokalise.com/public/465185555eee18dd537ca6.39714580/). See [Translations page](https://github.com/alandtse/alexa_media_player/wiki/Translations) for more details.

## Documentation

The [wiki](https://github.com/alandtse/alexa_media_player/wiki) is a group effort to document how to use the component and other useful [automations](https://github.com/alandtse/alexa_media_player/wiki/Examples%3A-Automation). Don't worry about making mistakes as we can revert using the history.

# License

[Apache-2.0](LICENSE). By providing a contribution, you agree the contribution is licensed under Apache-2.0. This is required for Home Assistant contributions.
