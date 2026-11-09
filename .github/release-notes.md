# Changelog and release note PR attribution

The release workflow prepares a single snapshot of GitHub PR authors **before**
Python Semantic Release v10.2.0 runs. PSR uses it while generating both the
committed `CHANGELOG.md` and the GitHub release notes consumed by Home Assistant.
There is no post-publication release-body edit and no separate Contributors section.

```markdown
- Fix a bug ([#123](https://github.com/alandtse/alexa_media_player/pull/123) by [@username](https://github.com/username), [`abcdef0`](commit-url))
```

`.github/scripts/prepare-release-notes.py` reads the same PSR configuration,
release history, parser, tags and exclusions as the release action. It looks up
only PR references in unreleased parsed commits, caches each PR, and uses
`pull.user` (the actual PR author, rather than the Git commit author or merger).
Validated profile links support normal accounts and GitHub App bot accounts.
Direct commits, missing users and unavailable PRs (404) keep their original text.
Other API errors retry up to three times and fail the preparation step before
PSR can commit, tag or publish. A failed lookup therefore cannot cause the two
artifacts to use different author data.

The preparation copies the installed **10.2.0** conventional Markdown templates
into the ignored `.github/.release-templates` directory. Only the shared
`commit_msg_links` macro changes: it appends the snapshot's author link immediately
beside the existing PR link. Snapshot entries are keyed by unreleased commit SHA.
The changelog and release-note renders both import that same snapshot. Historical
changelog text remains in PSR's update-mode footer; old GitHub releases are not
edited. Template components and metadata are hidden files/directories, so PSR's
recursive renderer only stages the generated `CHANGELOG.md`.

PSR keeps its own ordering, categories, scopes, wrapping, PR/commit links, breaking
changes, notices, first-release masking and release comparison links. Changelog
wrapping remains 100 columns and release notes use PSR's normal wider lines.
Disabling HTML autoescaping matches PSR's built-in Markdown environment.

## Exact upstream execution order

Verified against the tagged [v10.2.0 source](https://github.com/python-semantic-release/python-semantic-release/tree/v10.2.0):

1. [`action.sh`](https://github.com/python-semantic-release/python-semantic-release/blob/v10.2.0/src/gh_action/action.sh)
   invokes `semantic-release version`.
2. [`version.py`](https://github.com/python-semantic-release/python-semantic-release/blob/v10.2.0/src/semantic_release/cli/commands/version.py)
   selects the version, builds release history, writes changelog files, updates
   version declarations, builds, stages, commits, tags and pushes.
3. It then calls `generate_release_notes` and creates the GitHub release.
4. [`changelog_writer.py`](https://github.com/python-semantic-release/python-semantic-release/blob/v10.2.0/src/semantic_release/cli/changelog_writer.py)
   renders changelog templates recursively, but renders `.release_notes.md.j2`
   separately in a fresh environment. Both resolve the same shared macro.

A build-command-only change would be too late for the changelog render and would
not enrich the later release-note render. A post-release edit would miss the
committed changelog. The shared template snapshot covers both rendering paths.
The installed package version and exact macro fragment are checked; review this
integration when upgrading PSR. No PSR monkeypatch or custom commit parser is used.

The action stays pinned to v10.2.0. Version selection, release commit/tag/push,
ZIP creation/upload and master-to-dev synchronization remain with the existing
workflow. Python 3.13 matches the pinned action's container. Preparation runs in
its own job with the automatic `GITHUB_TOKEN`, limited to contents and pull-request
read access. Checkout credentials are not persisted. The generated templates pass
through a run-scoped artifact (including hidden components); the release job checks
out the exact source SHA recorded by preparation and restores the `master` branch.
Only the release job receives contents-write permission for the existing dev sync
and retains the existing release secret for PSR and asset upload.

Preparation installs the complete dependency set from
`.github/requirements/release-notes.txt` using `pip --require-hashes`. Regenerate it
for Python 3.13/Linux from `release-notes.in` with `uv pip compile --generate-hashes`.
The attribution test workflow also installs this locked dependency set.

## Validation

Install `python-semantic-release==10.2.0` and `pytest`, then run:

```sh
python -m pytest -c /dev/null .github/tests/test_release_notes.py
```

The dedicated test workflow uses this exact PSR version. Tests run its real
`version` command in temporary Git repositories: they inspect the committed
changelog, version declarations and tag, and capture release publication while
mocking only remote pushes/publication and PR API responses. They also compare
empty-snapshot output byte-for-byte with upstream, remove attribution to check
preservation of surrounding content, and cover caching, repeated runs, deleted
users, invalid profiles, bots, breaking changes, notices and preparation failures.
A live production release and Home Assistant dialog still require verification
when the next release is published.
