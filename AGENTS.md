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
- Test concurrent requests when the upstream client shares retry or throttle
  state. Capture that state alongside each request result, not after a
  `gather()` where another request may already have cleared it. If the client
  clears the flag in a `finally` block before returning, sample it while the
  request is still in flight; checking only before and after the call misses a
  request that was throttled and retried internally.
- Share one in-flight capability probe per device between platforms. If it
  fails, remember the failure for the current setup attempt so a sibling
  platform cannot retry it, succeed, and cancel the reload that repairs the
  platform still missing its entities. Clear that memo when a new setup attempt
  begins, because the account record survives setup retries.
- Probe many devices with bounded concurrency. Serializing an unbounded number
  of slow capability probes inside setup turns one throttle into minutes of
  entry startup time.
- Test scheduled retries: scheduling, deduplication, persistence across reloads,
  and cancellation on unload.
- Test setup-time probing: devices or services that reject the capability must
  not create entities and must not generate repeated calls.
- Test authentication failures from setup and probe paths, not only from the
  refresh loop. Keep the probe unresolved and report reauthentication once per
  account episode; allow a new report after a successful read.

### Entities and state

- Test the success path, unavailable/unknown paths and state restoration.
- Assert entity availability, not only the value.
- Cover listener updates and state writes for shared state objects.
- Verify entity naming, unique IDs, translation keys, device info, entity
  category and device class.
- Test setup, reload and unload cleanup for listeners, timers, tasks and shared
  state.
- When setup probes a slow capability, submit unrelated entities first. Snapshot
  any live collection before an `await`; skip entries whose dependent entity is
  not registered yet instead of indexing it directly.

### Tests and validation

- Add a focused regression test for every reported issue, even when a broader
  refactor is expected to fix it.
- Assert the specific entity or value the test is about. An assertion that can
  pass through a sibling entity is not a regression test.
- Make timeout tests wait on an unset event with a short timeout; do not raise
  `asyncio.TimeoutError` directly from a mock, which would pass even if the
  timeout wrapper disappeared. For a shared/group timeout, let one request
  succeed and another hang, and assert that partial results are discarded.
- When setup probes many devices, assert the concurrency bound and that every
  device still receives a result.
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
- Treat malformed payloads as failures, not as valid scalar values.
- Capture shared retry/throttle state per request. Do not decide whether a
  response was throttled after awaiting several requests, because the shared
  flag may already be clear. When the client clears the flag before returning,
  sample it while the request is in flight instead of only before and after.
- When an upstream dependency hides the status that distinguishes failure
  classes, document the limitation and prefer a safe retry over classifying an
  uncertain response as definitive.
- Retry transient failures with bounded attempts and avoid tight loops.
- Scope retry budgets to the entry and to the devices that still need recovery.
  A successful sibling must not release the budget while another device is
  unresolved. Keep that state in `hass.data` so it survives config-entry
  reloads, prune it against the current device inventory, and clear it on entry
  removal.
- Share one in-flight capability probe per device across platforms and remember
  a failure for the current setup attempt. Letting a sibling retry and succeed
  would cancel the reload that repairs the platform still missing its entities.
  Reset the memo on each setup attempt; the account record survives setup
  retries.
- Bound how many capability probes run at once, and bound the whole probe group.
  A per-request timeout alone can still multiply into minutes of setup time.
- Report authentication failures from every path that can encounter them,
  including initial probing. Deduplicate once per account episode and reset the
  marker after a successful read.
- Resolve the account record first and return early when it is already gone:
  a failed setup may never have created one. Then cancel scheduled retries
  before the first `await`; keep the timer active during normal operation.
- On unload, cancel timers, listeners and tasks. Keep entry-scoped recovery
  state across automatic reloads, and drop it on entry removal so a removed
  entry cannot be recovered or reloaded behind the user's back.

## PR expectations

- Use conventional commit messages.
- Link fixed issues (`Fixes #...`) and explain external dependencies or release
  order.
- Keep the PR scoped to the reported behavior. Move unrelated documentation,
  test checklists or refactors to a separate PR.
- Update tests and docs in the same PR.
- Do not commit local workspace files.
