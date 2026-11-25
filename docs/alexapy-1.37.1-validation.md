# AlexaPy 1.38.0 upgrade validation

AMP pins `alexapy==1.38.0` and retains the cookie adoption and bootstrap
behavior validated with 1.37.1. The expanded GraphQL query adds endpoint
`id`. AMP receives the same legacy appliance records and identifiers through
`get_network_details()`. The legacy-query fallback and throttle handling are
unchanged. The [new management methods](https://gitlab.com/keatontaylor/alexapy/-/merge_requests/520),
device renaming, and skill listing are available in AlexaPy and are not called
by AMP.

## AlexaPy 1.38.0 validation

- The wheel and source distribution SHA-256 digests match PyPI and the Poetry lockfile.
  Both distributions match all 11 Python source files at the
  [release tag](https://gitlab.com/keatontaylor/alexapy/-/tags/v1.38.0) and have
  equivalent Python and dependency requirements.
- The Linux AMP suite passed 842 tests, including the two bootstrap cookie-adoption
  cases. The [draft CI run](https://github.com/alandtse/alexa_media_player/pull/3745/checks)
  records the lockfile regeneration and the integration, lint, formatting, and
  release-note attribution checks.
- Isolated discovery checks used mocked Alexa responses to cover endpoint ID
  stripping, legacy fallback, GraphQL throttling, and unusable discovery responses.

No live Amazon API validation of the published 1.38.0 package has been recorded.
The earlier 1.37.1 verification and live development-build results are below.

## AlexaPy 1.37.1 baseline

AMP moves from `alexapy==1.36.0` to `alexapy==1.37.1`. AMP keeps its existing bootstrap probe. A successful probe now delegates cookie validation and adoption to AlexaPy before AMP can skip the normal login path.

## Release verification

- [x] Confirm [PyPI publication](https://pypi.org/project/AlexaPy/1.37.1/) on November 22, 2026. Downloaded the wheel and source distribution.
- [x] Confirm both fixes in the [release tag](https://gitlab.com/keatontaylor/alexapy/-/tags/v1.37.1) and in both distributions. SHA-256 hashes of `alexalogin.py`, `alexaapi.py`, `request.py`, and `const.py` match the tagged source.
  - [AlexaPy !513](https://gitlab.com/keatontaylor/alexapy/-/merge_requests/513), `7b23371`, validates saved cookies before replacing authentication state and preserves verified state on failed recovery.
  - [AlexaPy !515](https://gitlab.com/keatontaylor/alexapy/-/merge_requests/515), `fc84165`, uses the PitanguiBridge User-Agent for Alexa API calls, notification reads, and OAuth alarm requests. Login and token requests retain their own identities.
- [x] Check package metadata against AMP's Python range and existing dependency constraints. The wheel requires Python `>=3.11,<4` and declares the same runtime dependencies as 1.36.0. AMP requires Python `>=3.13,<4`.

## Automated validation

- AMP CI installed the published AlexaPy 1.37.1 dependency and passed 840 tests on Linux with Python 3.13.18.
- AMP regression tests cover cookie adoption after a successful bootstrap probe and fallback when adoption fails.
- AlexaPy !513 has automated coverage for saved-cookie validation and failed recovery. The [MR discussion](https://gitlab.com/keatontaylor/alexapy/-/merge_requests/513) records the follow-up fixes and outstanding live authentication scenarios.

## Previous live validation

- [AlexaPy !515](https://gitlab.com/keatontaylor/alexapy/-/merge_requests/515) documents Canadian HAOS testing of Git build `eac5338`. TTS, media controls, alarm deletion, and the next notification poll worked.
- UK and Italy volunteers tested build `5233556`. The UK report confirmed recovery of Echo temperature readings. The Italy reports confirmed air-quality monitor discovery and notification polling with PitanguiBridge enabled.

## Optional live HAOS regression checklist

These checks are available for follow-up on an authorized test installation. The published package has no live HAOS result recorded here.

| Area                       | Checks and expected results                                                                                                                                                                                                                                                                                                                                                                                                                             |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Authentication and cookies | Cold-start HAOS with valid saved cookies on US and regional accounts. Verify startup with valid cookies and stale OAuth avoids an unnecessary reauth. Exercise a fresh login, expired-cookie recovery, and phone-based identity where available. With test fixtures, verify wrong-account or failed refresh leaves saved cookies and OAuth intact. Verify legacy cookies migrate only after successful authentication and survive a subsequent restart. |
| PitanguiBridge requests    | Verify discovery, `/nexus/v1/graphql`, and `/api/phoenix/state` use the expected API identity and regional endpoint where applicable. Confirm login and token requests retain their own identities. Recheck a marketplace affected by [AMP #3705](https://github.com/alandtse/alexa_media_player/issues/3705) for successful responses, recovered entities, and absence of recurring HTTP 403/429 responses. Use sanitized request evidence.            |
| Notifications              | Verify one notification read per poll and correct alarm, timer, and reminder state against the Alexa app. Delete a disposable test alarm and confirm the next successful poll reflects the deletion.                                                                                                                                                                                                                                                    |
| TTS                        | Send TTS to an Echo after a saved-cookie cold start and after successful reauth. Confirm audible delivery and no authentication errors.                                                                                                                                                                                                                                                                                                                 |
| Media controls             | Exercise play, pause, and volume on an active Echo. Confirm both the device response and the state reported back to HA.                                                                                                                                                                                                                                                                                                                                 |
| HAOS upgrade and rollback  | Upgrade an existing AMP test installation using the PyPI-built dependency. Verify the loaded AlexaPy version is 1.37.1, config entry setup, device discovery, integration reload, and full Core restart. Record HA Core/OS versions, AMP commit, AlexaPy version, marketplace, and results. Confirm recovery to the previous known-good AMP build and pin on the test installation.                                                                     |
