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
- Test scheduled retries: scheduling, deduplication and cancellation on unload.
- Test setup-time probing: devices or services that reject the capability must
  not create entities and must not generate repeated calls.

### Entities and state

- Test the success path, unavailable/unknown paths and state restoration.
- Assert entity availability, not only the value.
- Cover listener updates and state writes for shared state objects.
- Verify entity naming, unique IDs, translation keys, device info, entity
  category and device class.
- Test setup, reload and unload cleanup for listeners, timers, tasks and shared
  state.

### Tests and validation

- Add a focused regression test for every reported issue, even when a broader
  refactor is expected to fix it.
- Keep touched modules at high coverage; config flow changes should keep the
  existing 100% coverage target.
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
- Use `entry.runtime_data` for per-entry runtime state and keep `hass.data`
  usage consistent with the surrounding code.
- Give entities stable unique IDs, `has_entity_name`/translation keys, device
  info and the correct entity category and device class.
- Register domain services once in `async_setup`. Use
  `AlexaMediaServices._get_accounts()` and raise `ServiceValidationError` for
  invalid or unavailable targets. Keep `supports_response` for services that
  return data.
- Implement `async_unload_entry` cleanup for listeners, timers, tasks,
  coordinators and per-account state.
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
- Retry transient failures with bounded attempts and avoid tight loops.
- Cancel scheduled retries on unload and deduplicate them per account.
- Treat malformed payloads as failures, not as valid scalar values.

## PR expectations

- Use conventional commit messages.
- Link fixed issues (`Fixes #...`) and explain external dependencies or release
  order.
- Update tests and docs in the same PR.
- Do not commit local workspace files.
