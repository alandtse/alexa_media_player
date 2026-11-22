# AlexaPy 1.38.0 upgrade validation

The preparation branch starts from AMP `dev` at `3438573`, where `custom_components/alexa_media/manifest.json` pins `alexapy==1.36.0`.

## Release prerequisites

- [ ] Verify the published [PyPI release](https://pypi.org/project/AlexaPy/#history) provides an installable `1.38.0` artifact for Home Assistant's supported Python environment. Verify the source tag and released package include both fixes below or equivalent changes. The MRs target different branches.
  - [AlexaPy !513](https://gitlab.com/keatontaylor/alexapy/-/merge_requests/513) targets `master`. It validates saved cookies in an isolated session before recovery or migration and preserves existing auth state when recovery fails.
  - [AlexaPy !515](https://gitlab.com/keatontaylor/alexapy/-/merge_requests/515) targets `dev`. It uses a dedicated PitanguiBridge User-Agent for Alexa API traffic, including notifications and OAuth alarm requests, while preserving login and token identities.
- [ ] Once publication and contents are confirmed, refresh against upstream `dev`, check the effective dependency pin, and update the manifest and any repository dependency references that must match it.
- [ ] Run AMP CI with the published dependency and complete the HAOS checks below before marking the PR ready. Keep AMP's existing bootstrap workaround in place for this upgrade.

## Regression checklist

| Area | Checks and expected results |
| --- | --- |
| Authentication and cookies | Cold-start HAOS with valid saved cookies on US and regional accounts. Verify startup with valid cookies and stale OAuth avoids an unnecessary reauth. Exercise a fresh login, expired-cookie recovery, and phone-based identity where available. With test fixtures, verify wrong-account or failed refresh leaves saved cookies and OAuth intact. Verify legacy cookies migrate only after successful authentication and survive a subsequent restart. |
| PitanguiBridge requests | Verify discovery, `/nexus/v1/graphql`, and `/api/phoenix/state` use the expected API identity and regional endpoint where applicable. Confirm login and token requests retain their own identities. Recheck a marketplace affected by [AMP #3705](https://github.com/alandtse/alexa_media_player/issues/3705) for successful responses and recovered entities. Use sanitized request evidence. |
| Notifications | Verify one notification read per poll and correct alarm, timer, and reminder state against the Alexa app. Delete a disposable test alarm and confirm the next successful poll reflects the deletion. |
| TTS | Send TTS to an Echo after a saved-cookie cold start and after successful reauth. Confirm audible delivery and no authentication errors. |
| Media controls | Exercise play, pause, and volume on an active Echo. Confirm both the device response and the state reported back to HA. |
| HAOS upgrade and rollback | Upgrade an existing AMP test installation using the PyPI-built dependency. Verify the loaded AlexaPy version, config entry setup, device discovery, integration reload, and full Core restart. Record HA Core/OS versions, AMP commit, AlexaPy version, marketplace, and results. Confirm recovery to the previous known-good AMP build and pin on the test installation. |

GitLab reported green head pipelines for both MRs at inspection. The !515 description records earlier Canadian HAOS testing using a Git-pinned build and UK/Italy testing using an earlier volunteer build. The checklist remains pending for the published package.
