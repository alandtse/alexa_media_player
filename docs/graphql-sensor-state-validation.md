# GraphQL smart-home sensor polling validation

Alexa Media Player uses the account's latest successful discovery to map Echo
temperature and air-quality sensor entities to GraphQL endpoint IDs. The
snapshot is kept in memory by the account coordinator and rebuilt when the
login object changes. Failed rediscovery keeps the current login's snapshot.
Partial state responses preserve the original sample timestamps for metrics
missing from the reply.

AlexaPy 1.38.0 retains legacy Phoenix polling. With the GraphQL state API,
mapped Echo temperatures and AQM entities use GraphQL. Lights and smart switches
join that path when both the GraphQL state and control APIs are available and
discovery returns a usable endpoint mapping. Without a usable mapping or the
required APIs, lights and smart switches continue to poll through Phoenix.
Guard and standalone contact and battery sensors remain on Phoenix.

This describes polling. With the GraphQL control API available, a light or
smart switch command requires a current account mapping. Rejected GraphQL
commands do not retry through Phoenix.

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
