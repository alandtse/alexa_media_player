# Agent Instructions

Alexa Media Player is a Home Assistant custom component that controls Amazon
Echo devices through the unofficial Alexa API. Start with
`.github/copilot-instructions.md` for environment setup, lint commands and CI
details; this file records the testing and quality-scale expectations that are
easy to miss during a change.

## Testing expectations

### External APIs and unreliable services

- Test the successful path with realistic payloads.
- Test each failure class separately:
  - transient HTTP/network errors (timeouts, 5xx, 429);
  - explicit unsupported responses (for example HTTP 400);
  - malformed, empty or unexpected payloads;
  - exceptions raised by the transport layer.
- Assert that cached state and entity availability are preserved on transient
  failures. A failed read must not overwrite the last good value.
- Test recovery: after a transient failure, a later successful read must update
  state and restore availability.
- Test partial capability: create entities only for supported features and poll
  only those features.
- Test partial outages: one device failing must not remove or block entities
  that another device has already discovered.
- Test authentication failures from setup paths, not only from the refresh
  loop.

### Entities and state

- Test the success path, unavailable/unknown paths and state restoration.
- Assert entity availability, not only the value.
- Verify entity naming, unique IDs, translation keys, device info, entity
  category and device class.
- Test setup, reload and unload cleanup for listeners, timers, tasks and shared
  state.
- Snapshot any live collection before an `await`; skip entries whose dependent
  entity is not registered yet instead of indexing it directly.

### Tests and validation

- Add a focused regression test for every reported issue, even when a broader
  refactor is expected to fix it.
- Assert the specific entity or value the test is about. An assertion that can
  pass through a sibling entity is not a regression test.
- Make timeout tests wait on an unset event with a short timeout; do not raise
  `asyncio.TimeoutError` directly from a mock, which would pass even if the
  timeout wrapper disappeared.
- Keep touched modules at high coverage; config flow changes should keep the
  existing 100% coverage of `config_flow.py`.
- Run the full test suite, coverage for the touched module and pre-commit before
  pushing.
- When a test is environment-specific, note it in the PR and verify the same
  behavior in CI.

## Bronze quality-scale patterns

The project is aligning with the Home Assistant Bronze quality scale. Follow
these patterns when touching integration code:

- Read effective settings through `config_entry_option()` or
  `config_entry_config()`. Reauth moves settings from `entry.data` to
  `entry.options`; never assume a key still lives in `entry.data`.
- Keep `CONFIG_ENTRY_OPTION_KEYS` in sync when adding or moving options.
- Prefer `entry.runtime_data` for per-entry runtime state, and keep `hass.data`
  usage consistent with the surrounding code.
- Give entities stable unique IDs, `has_entity_name`/translation keys, device
  info and the correct entity category and device class.
- Register domain services once in `async_setup`. Use
  `AlexaMediaServices._get_accounts()` and raise `ServiceValidationError` for
  invalid or unavailable targets. Keep `supports_response` for services that
  return data.
- Implement `async_unload_entry` cleanup for listeners, timers, tasks,
  coordinators and per-account state.
- Home Assistant skips `async_unload_entry` when an entry that never finished
  setup is removed, so `async_remove_entry` must also drop runtime state that
  the entry owns.
- Support reauthentication and reconcile `data`/`options`; preserve explicit
  removals and keep unspecified credentials unchanged.
- Raise `ConfigEntryNotReady` for transient setup failures and
  `ConfigEntryAuthFailed` for authentication failures. Do not leave stale login
  objects, listeners or retry timers behind.
- Redact emails and serials with `hide_email`/`hide_serial`; never log tokens,
  cookies, passwords or OTP secrets.
- Keep `strings.json`, `services.yaml` and translations in sync with
  user-facing names and descriptions.
- Add regression tests for service, options, reauth, setup-retry and unload
  paths.

## Failure handling

- Distinguish explicit "unsupported" responses from transient failures.
- Preserve cached state and availability on transient failures.
- Treat malformed payloads as failures, not as valid scalar values.
- Retry transient failures with bounded attempts and avoid tight loops.
- Do not decide whether a response was throttled after awaiting several
  requests; shared client state may already be clear.
- When an upstream dependency hides the status that distinguishes failure
  classes, document the limitation and prefer a safe retry over classifying an
  uncertain response as definitive.
- Report authentication failures from every path that can encounter them, and
  report them once per account episode.
- On unload, cancel timers, listeners and tasks. Do not hold a shared login
  object across an `await` another task can interleave with.

## PR expectations

- Use conventional commit messages.
- Link fixed issues (`Fixes #...`) and explain external dependencies or release
  order.
- Keep the PR scoped to the reported behavior.
- Update tests and docs in the same PR.
- Do not commit local workspace files.
