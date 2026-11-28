# Phase 2 GraphQL live validation

Use a disposable Linux Home Assistant Container with its own configuration directory and a test Amazon account with safe test loads. Keep both Phase 2 reviews in Draft while collecting results. These instructions use a fresh Home Assistant 2026.11.3 configuration. See the [Home Assistant Container documentation](https://www.home-assistant.io/installation/linux#install-home-assistant-container).

| Component                | Revision                                   |
| ------------------------ | ------------------------------------------ |
| AMP Phase 2 code         | `158613e131a84309f56394194ceaec9837e5bef1` |
| AMP Phase 1 parent       | `7fa786edd7d63e86aed803fd348de047e0429fe6` |
| AlexaPy Phase 2          | `2b5dd7d202c39a765bdc0479f7eaf854022e2884` |
| AlexaPy Phase 1 parent   | `2127bb31b1c5722afad8dc2961bce15985d4c03f` |
| AMP published dependency | `alexapy==1.38.0`                          |

## Install

1. In a fresh directory on a disposable Linux host, run the commands below. Keep the config and its backup on that host.
2. Open `http://127.0.0.1:18123` on that host, complete onboarding and add Alexa Media Player with the test account. Enable **Extended entity discovery** for lights and plugs. For remote access, use a trusted tunnel to the host's loopback port.
3. Confirm the source module path and that both GraphQL methods are available. Verify the exact SHAs before recording results. On a second independent instance, omit the AlexaPy mount and `PYTHONPATH` to compare the published dependency. A published-dependency failure on a Phoenix-blocked account is an expected comparison result.

```sh
set -eu
git clone https://github.com/danielbrunt57/alexa_media_player.git amp
git clone https://gitlab.com/b366/alexapy.git alexapy-src
git -C amp checkout --detach 158613e131a84309f56394194ceaec9837e5bef1
git -C alexapy-src checkout --detach 2b5dd7d202c39a765bdc0479f7eaf854022e2884
git -C amp rev-parse HEAD
git -C alexapy-src rev-parse HEAD
mkdir -p ha-phase2-config/custom_components
cp -a amp/custom_components/alexa_media ha-phase2-config/custom_components/
docker run -d --name ha-alexa-phase2 \
  -p 127.0.0.1:18123:8123 \
  --mount "type=bind,source=$PWD/ha-phase2-config,target=/config" \
  --mount "type=bind,source=$PWD/alexapy-src,target=/opt/alexapy-phase2,readonly" \
  -e PYTHONPATH=/opt/alexapy-phase2 \
  ghcr.io/home-assistant/home-assistant:2026.11.3
```

After adding the integration, verify the import from the container.

```sh
docker exec ha-alexa-phase2 python -c 'import alexapy; print(alexapy.__file__); assert alexapy.__file__.startswith("/opt/alexapy-phase2/"); assert hasattr(alexapy.AlexaAPI, "get_entity_state_gql"); assert hasattr(alexapy.AlexaAPI, "set_light_state_gql")'
```

## Live test matrix

Record pass, fail or unsupported for each row. Record marketplace, device model, exact AMP and AlexaPy revisions, UTC timestamps, the Alexa app's displayed values and Home Assistant's observed values. Use a colour-capable bulb for the colour rows.

| Case                      | How to exercise it                                                                                                                              | Observe                                                                                    |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Echo temperature          | Compare with the Alexa app across several polls and one reload.                                                                                 | Value, units, freshness and availability                                                   |
| Seven AQM metrics         | Compare temperature, humidity, CO, PM2.5, PM10, VOC and AQI individually. Repeat after reload.                                                  | Each value and unit, with a separate result for all seven                                  |
| AQM LED                   | Turn it off and on from HA and repeat from the Alexa app if available.                                                                          | Physical indicator and switch feedback                                                     |
| Smart plug                | Toggle off and on in HA with a safe test load.                                                                                                  | Physical response and switch feedback                                                      |
| Bulb power                | Toggle off and on in HA.                                                                                                                        | Physical response and light feedback                                                       |
| Brightness                | Test zero, intermediate and maximum. Record whether the HA UI converts zero to off.                                                             | Values sent and read back, including any device-specific clamping                          |
| Colour                    | Set two distinct hues and a lower saturation.                                                                                                   | Colour feedback and brightness retained or explicitly updated                              |
| Colour temperature        | Set warm and cool values supported by the device.                                                                                               | Reported kelvin or device rounding                                                         |
| External changes          | Change plug, light and supported attributes in the Alexa app while HA is idle.                                                                  | HA feedback on the next poll                                                               |
| Post-mutation convergence | Make successive changes, including after integration reload.                                                                                    | Time to confirmed state and any old sample shown after a newer one                         |
| Rejection and offline     | Disconnect a test endpoint and issue a command. Capture any naturally rejected or unsupported command.                                          | HA error, no optimistic state change and no Phoenix retry for the rejected GraphQL command |
| Accounts and recovery     | If a second test account is available, use different devices and reauthenticate one account. Disable and re-enable a test entity during a poll. | Each account and entity retains only its own eligible samples                              |

For zero brightness, distinguish an HA service call that becomes a power-off command from an actual GraphQL brightness payload of zero. The latter is covered by the AlexaPy mock even if the HA frontend converts zero to off.

## Diagnostics and evidence

- Record the command time and collect only the surrounding lines from the disposable container. For example, retrieve recent logs locally with `docker logs --since 5m ha-alexa-phase2`. Use normal logging first and enable integration debug logging only while reproducing a specific failure.
- Share a hand-redacted excerpt with HTTP method, path, status, GraphQL operation name, error code, and command-to-feedback latency. Replace endpoint, appliance, device, account and serial IDs with consistent labels. Remove email addresses, cookies, tokens, CSRF fields, authorization headers, credentials, request or response bodies, and any login or proxy URLs containing query strings. Keep HA backups, diagnostics bundles and Amazon login files private. Unrelated devices may independently poll Phoenix. Attribute requests to the tested endpoint and operation before concluding that a retry occurred.
- Linux regression tests use mocked device responses. The [US report](https://github.com/alandtse/alexa_media_player/issues/3705#issuecomment-7228471047) supplies observed Phoenix 403 evidence. Existing clients corroborate the proposed [GraphQL command shapes](https://github.com/johnccarroll/homebridge-alexa-sync/tree/bcefdd00f8e4615fa06f6793fd7d22fb823c0d7c/src/providers/alexa), while AMP's AQM LED supplies the instance-specific precedent. Record successful live results only from the exact combined revisions and account tested.

## Rollback

Stop the test container with `docker stop ha-alexa-phase2`. Preserve its config and private logs if needed. To return the disposable instance to a previously working version, start a fresh container with the prior AMP release and a matching pretest config backup, without the source mount or `PYTHONPATH`. Restore the config only into the disposable instance. If no prior working version exists, leave the test instance stopped or create a clean published-build comparison.
