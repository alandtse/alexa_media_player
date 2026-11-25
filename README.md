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

| Service                                     | Description                                             |
| ------------------------------------------- | ------------------------------------------------------- |
| `alexa_media.force_logout`                  | Mark one or all accounts for reauthentication.          |
| `alexa_media.restore_volume`                | Restore the previous volume of a media player.          |
| `alexa_media.get_history_records`           | Store recent voice-history records on a media player.   |
| `alexa_media.update_last_called`            | Refresh which Echo received the last voice command.     |
| `alexa_media.enable_network_discovery`      | Re-run Alexa network discovery.                         |
| `alexa_media.amazon_kids_enable`            | Assign an Echo to an Amazon Kids child profile.         |
| `alexa_media.amazon_kids_disable`           | Release an Echo from Amazon Kids.                       |
| `alexa_media.repeat_last_message`           | Repeat the last message sent to a media player.         |
| `alexa_media.create_alarm`                  | Create an alarm on an Echo.                             |
| `alexa_media.list_alarms`                   | Return cached alarm metadata for one Echo.              |
| `alexa_media.enable_alarm`                  | Turn on an Echo alarm.                                  |
| `alexa_media.disable_alarm`                 | Turn off an Echo alarm without deleting it.             |
| `alexa_media.delete_alarm`                  | Delete an Echo alarm.                                   |
| `alexa_media.skip_next_alarm`               | Skip the next scheduled alarm.                          |
| `alexa_media.get_smart_home_groups`         | Return the smart-home groups and devices of an account. |
| `alexa_media.create_smart_home_group`       | Create a smart-home group (room).                       |
| `alexa_media.rename_smart_home_group`       | Rename a smart-home group.                              |
| `alexa_media.set_smart_home_group_members`  | Replace the devices of a smart-home group.              |
| `alexa_media.delete_smart_home_group`       | Delete a smart-home group.                              |
| `alexa_media.rename_smart_home_device`      | Rename a smart-home device in the Alexa account.        |
| `alexa_media.set_smart_home_device_enabled` | Enable or disable a smart-home device.                  |
| `alexa_media.forget_smart_home_device`      | Remove a smart-home device from the Alexa account.      |
| `alexa_media.discover_smart_home_devices`   | Start an Alexa smart-home device search.                |

## Smart-home groups and devices

The smart-home services change the Alexa account itself, so only Home Assistant
administrators can call them. Each call uses one account: set `email` when more
than one account is set up.

`alexa_media.get_smart_home_groups` returns the groups (rooms) with their `id`,
`name` and `appliance_ids`, and the devices with their `endpoint_id`,
`appliance_id` and `name`. Groups list their devices by `appliance_id`, so use
these IDs for `create_smart_home_group` and `set_smart_home_group_members`. The
device services take the `endpoint_id`.

```yaml
action: alexa_media.create_smart_home_group
data:
  name: Office
  appliance_ids:
    - "<appliance_id from get_smart_home_groups>"
response_variable: group
```

Alexa does not accept device names with an underscore.
`discover_smart_home_devices` works like the device search in the Alexa app:
Echo devices with a Zigbee hub search as well, so it can add new devices to the
account.

# Events

- `alexa_media_voice_command`: fired for new voice-history records that pass the
  integration's filters (for example, records from unknown devices are skipped),
  with the command text in `summary` plus `response`, `timestamp`, `serial` and
  `entity_id`.
- `alexa_media_alarm_dismissal_event`: fired when an alarm is dismissed.
- `alexa_media_notification_event`: fired when an alarm, timer or reminder is
  due.

There are no integration-specific conditions.

# Installation and Configuration

Install through HACS or copy the `custom_components/alexa_media` directory to
`<config>/custom_components/alexa_media`, restart Home Assistant, then add the
integration from **Settings > Devices & services**. You need an Amazon account
with access to the Alexa devices. Two-step verification must be enabled with an
authenticator app, and you need the authenticator app key (the setup secret),
not a one-time password.

Detailed configuration options are documented in the
[wiki](https://github.com/alandtse/alexa_media_player/wiki/Configuration).

# Removal

1. Remove the integration from **Settings > Devices & services**.
2. Remove the `alexa_media` custom component directory.
3. Restart Home Assistant.

Removing the config entry normally deletes the login cookie file
`.storage/alexa_media.<email>.cookies` and the runtime entities. If automatic
cleanup fails, delete that file manually to discard the Amazon session.

## Authentication cookie storage

Since alexapy 1.33, authentication cookies are stored in
`<config>/.storage/alexa_media.<account>.cookies` using alexapy's versioned JSON
format (`alexapy.cookies`), replacing the legacy `.pickle` format. Renaming the
file does not convert it to a pickle; companion tools must support the JSON
format to import the session. alexapy can migrate supported legacy cookie files
when loading them.

Removing a config entry deletes its current `.cookies` file. If removal reports
an error, the log identifies the cookie file to delete manually before re-adding
the integration (with the account name obscured). The `force_logout` action marks
accounts for reauthentication; it does not delete their cookie files. Cookie
files contain authentication credentials and should not be shared or attached to
issues.

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
