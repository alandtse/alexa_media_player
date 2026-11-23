# AlexaPy 1.37.1 upgrade validation

AMP moves from `alexapy==1.36.0` to `alexapy==1.37.1`. The existing AMP authentication bootstrap workaround stays in place.

## Release prerequisites

- [x] Confirm [PyPI publication](https://pypi.org/project/AlexaPy/1.37.1/) on November 22, 2026. Downloaded the wheel and source distribution.
- [x] Confirm both fixes in the [release tag](https://gitlab.com/keatontaylor/alexapy/-/tags/v1.37.1) and in both distributions. SHA-256 hashes of `alexalogin.py`, `alexaapi.py`, `request.py`, and `const.py` match the tagged source.
  - [AlexaPy !513](https://gitlab.com/keatontaylor/alexapy/-/merge_requests/513), `7b23371`, validates saved cookies before replacing authentication state and preserves verified state on failed recovery.
  - [AlexaPy !515](https://gitlab.com/keatontaylor/alexapy/-/merge_requests/515), `fc84165`, uses the PitanguiBridge User-Agent for Alexa API calls, notification reads, and OAuth alarm requests. Login and token requests retain their own identities.
- [x] Check package metadata against AMP's Python range and existing dependency constraints. The wheel requires Python `>=3.11,<4` and declares the same runtime dependencies as 1.36.0. AMP requires Python `>=3.13,<4`.
- [ ] Verify dependency installation and AMP CI on the supported Python environment.
- [ ] Complete the live checks below on an authorized test HAOS installation before marking the PR ready.

## Regression checklist

| Area | Checks and expected results |
| --- | --- |
| Authentication and cookies | Cold-start HAOS with valid saved cookies on US and regional accounts. Verify startup with valid cookies and stale OAuth avoids an unnecessary reauth. Exercise a fresh login, expired-cookie recovery, and phone-based identity where available. With test fixtures, verify wrong-account or failed refresh leaves saved cookies and OAuth intact. Verify legacy cookies migrate only after successful authentication and survive a subsequent restart. |
| PitanguiBridge requests | Verify discovery, `/nexus/v1/graphql`, and `/api/phoenix/state` use the expected API identity and regional endpoint where applicable. Confirm login and token requests retain their own identities. Recheck a marketplace affected by [AMP #3705](https://github.com/alandtse/alexa_media_player/issues/3705) for successful responses, recovered entities, and absence of recurring HTTP 403/429 responses. Use sanitized request evidence. |
| Notifications | Verify one notification read per poll and correct alarm, timer, and reminder state against the Alexa app. Delete a disposable test alarm and confirm the next successful poll reflects the deletion. |
| TTS | Send TTS to an Echo after a saved-cookie cold start and after successful reauth. Confirm audible delivery and no authentication errors. |
| Media controls | Exercise play, pause, and volume on an active Echo. Confirm both the device response and the state reported back to HA. |
| HAOS upgrade and rollback | Upgrade an existing AMP test installation using the PyPI-built dependency. Verify the loaded AlexaPy version is 1.37.1, config entry setup, device discovery, integration reload, and full Core restart. Record HA Core/OS versions, AMP commit, AlexaPy version, marketplace, and results. Confirm recovery to the previous known-good AMP build and pin on the test installation. |

Earlier Canadian HAOS and UK/Italy volunteer results used Git builds. Live checks for the published package remain pending.
