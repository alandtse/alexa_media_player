# GraphQL smart-home sensor polling validation

Alexa Media Player uses the account's latest successful discovery to map Echo
temperature and air-quality sensor entities to GraphQL endpoint IDs. The
snapshot is kept in memory by the account coordinator and rebuilt when the
login object changes. Failed rediscovery keeps the current login's snapshot.
Partial state responses preserve the original sample timestamps for metrics
missing from the reply.

The integration detects the new API at runtime. AlexaPy 1.38.0 and discovery
responses without endpoint IDs continue to use Phoenix. Guard, lights, switches,
and standalone contact and battery sensors also continue to use Phoenix.
For a release that enables this path by default, update the AlexaPy dependency
after a published version includes the API from
[AlexaPy !525](https://gitlab.com/keatontaylor/alexapy/-/merge_requests/525).

## Validation

Run the normal AMP test suite against the published dependency. The focused
tests mock the GraphQL method to cover the first poll, failed rediscovery,
partial metric responses, and recovery.

For a second run in an isolated Linux test environment, put the AlexaPy draft
checkout on the Python import path. Use this only in the test shell.

```sh
PYTHONPATH=/absolute/path/to/alexapy poetry run python -c 'import alexapy; print(alexapy.__file__); assert hasattr(alexapy.AlexaAPI, "get_entity_state_gql")'
PYTHONPATH=/absolute/path/to/alexapy poetry run pytest -q tests/test_alexa_entity.py tests/test_update_data_timeout.py
```

For affected-account testing, compare temperatures and individual AQM metrics
with the Alexa app across multiple polls, then repeat after reload and a
network discovery retry. Include an unaffected account and a setup with two
accounts if available. Share marketplace, device type, and observed behavior
with [AMP #3705](https://github.com/alandtse/alexa_media_player/issues/3705).
