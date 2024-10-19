# CHANGELOG

## v4.13.5 (2024-10-19)

### Fix

* fix: bump alexapy to 1.29.3

Fix login loop issue (1825583)([`1825583`](https://gitlab.com/keatontaylor/alexapy/-/commit/18255832673fd7e7639c114766e7aa4e74ffe42f))

## v4.7.7 (2023-10-08)

### Build

* build: pre-commit autoupdate

updates:
- [github.com/commitizen-tools/commitizen: 3.8.2 → 3.10.0](https://github.com/commitizen-tools/commitizen/compare/3.8.2...3.10.0) ([`b23f27a`](https://github.com/custom-components/alexa_media_player/commit/b23f27aaa541a93c4fd643ec393338d1e158d4d6))

* build: Update required version of wrapt (#2050) ([`383ac6c`](https://github.com/custom-components/alexa_media_player/commit/383ac6c5da36f165774d0f72b9272f301feee32a))

### Fix

* fix: bump alexapy 1.27.6

closes #2059 ([`1b48a38`](https://github.com/custom-components/alexa_media_player/commit/1b48a38e3895a31f8c89b531f90bb83d928ca71d))

* fix: try to refresh tokens when http2 auth error

The http2 stream is sensitive to auth token errors. Instead of declaring
a bad login immediately, include one attempt to refresh auth tokens.
This may help reduce the frequency of reauth requests but is not
guaranteed. ([`4accda1`](https://github.com/custom-components/alexa_media_player/commit/4accda13412dc92a165915791b678de05ea3b77b))

### Unknown

* Merge pull request #2064 from custom-components/dev ([`1e28c9b`](https://github.com/custom-components/alexa_media_player/commit/1e28c9b1c805a21ff301f7a9aa0849353759df68))

* Merge pull request #2063 from alandtse/dev ([`ba30ce1`](https://github.com/custom-components/alexa_media_player/commit/ba30ce15ba8154107fde230996ae687ac8b6ea14))

* Merge pull request #2062 from alandtse/dev ([`4dfe25d`](https://github.com/custom-components/alexa_media_player/commit/4dfe25ddcdd4c8ff04bf51c561004a50b285c796))


## v4.7.6 (2023-09-30)

### Fix

* fix: bump alexapy to 1.27.4

Adds additional HTTP2 domains ([`9794b0a`](https://github.com/custom-components/alexa_media_player/commit/9794b0a2c290971bdfe6712792dbc82a5931ca7c))

### Unknown

* Merge pull request #2048 from alandtse/dev ([`0e22b69`](https://github.com/custom-components/alexa_media_player/commit/0e22b6955cb34b8f2db2e91ca177a1e05caf3903))


## v4.7.5 (2023-09-30)

### Documentation

* docs: update localization ([`1753564`](https://github.com/custom-components/alexa_media_player/commit/1753564655a22fcf5c27881416d9e5ca26c3874e))

* docs: fix validate badge in readme ([`9bd0ffc`](https://github.com/custom-components/alexa_media_player/commit/9bd0ffcb12965048df33c9e07a69c6899c563739))

### Fix

* fix: fix reconnect on http2 close ([`adbbf91`](https://github.com/custom-components/alexa_media_player/commit/adbbf910f26693737eda4535e04737e7c6d424d8))

### Unknown

* Merge pull request #2047 from alandtse/dev ([`f23fc18`](https://github.com/custom-components/alexa_media_player/commit/f23fc18a8668a9790914b9cd8515f377018d0250))


## v4.7.4 (2023-09-30)

### Documentation

* docs: update localization ([`6327d04`](https://github.com/custom-components/alexa_media_player/commit/6327d04ac05edc42be2634b6a9eaade572a751dc))

### Fix

* fix: fix http2 push for non-NA domains

closes #1982
closes #1953 ([`b83bfff`](https://github.com/custom-components/alexa_media_player/commit/b83bfffc108edea24a88ca45d30c17d9751102ec))

* fix: fix unload error when entity_id None ([`d8f270e`](https://github.com/custom-components/alexa_media_player/commit/d8f270eb5ae9195d22b19237c4a06d7e743f13e5))

* fix: Restore NOTIFICATION_CHANGE command (#2044)

* Restore NOTIFICATION_CHANGE

Partial revert of 8f0dfa2 to restore NOTIFICATION_CHANGE functionality for timers and alarms.

* style: auto fixes from pre-commit.com hooks

for more information, see https://pre-commit.ci

---------

Co-authored-by: pre-commit-ci[bot] &lt;66853113+pre-commit-ci[bot]@users.noreply.github.com&gt; ([`a4f8499`](https://github.com/custom-components/alexa_media_player/commit/a4f849918bd285b90f67065e94bfad60fe018c58))

### Unknown

* Merge pull request #2046 from custom-components/dev

chore: release 2023-09-30 ([`b90221d`](https://github.com/custom-components/alexa_media_player/commit/b90221d3a34189c988b5d00d3065b844693fe04e))

* Merge pull request #2045 from alandtse/dev

fix: fix http2 push for non-NA domains ([`aaf81a0`](https://github.com/custom-components/alexa_media_player/commit/aaf81a091324f3718b20347a764fad37ce562239))


## v4.7.3 (2023-09-29)

### Build

* build: fix precommit ignore ([`ca05a0a`](https://github.com/custom-components/alexa_media_player/commit/ca05a0a1b6c7f238ae40ce78d123526eea42b2a2))

* build: ignore changelog.md spelling ([`a5be5c7`](https://github.com/custom-components/alexa_media_player/commit/a5be5c7f3e6fcf11529a0fbd313d5c7ae906a586))

* build: update precommit ([`823e952`](https://github.com/custom-components/alexa_media_player/commit/823e952e6092544de8d00c74b90c858c37a499cf))

### Documentation

* docs: update localization ([`3bc121c`](https://github.com/custom-components/alexa_media_player/commit/3bc121cd772ca91f9bb014893d09da112bf319b2))

### Fix

* fix: add http2 push to replace websocket

This should restore push updates.

Also includes dependency updates.

closes #1953
closes #1976
closes #1967 ([`a3dde7f`](https://github.com/custom-components/alexa_media_player/commit/a3dde7f42dcb24cbb69a365458d6e131cfdbd19e))

### Unknown

* Merge pull request #2041 from custom-components/dev

chore: release 2023-09-29 ([`5833acc`](https://github.com/custom-components/alexa_media_player/commit/5833acc37b2e4d0649a3416f8357df93f18b8e8b))

* Merge pull request #2040 from alandtse/dev

fix: add http2 push to replace websocket ([`cfc723d`](https://github.com/custom-components/alexa_media_player/commit/cfc723d29608d7433298eb01482bd14a97116318))


## v4.7.2 (2023-09-22)

### Documentation

* docs: update localization ([`d430e7e`](https://github.com/custom-components/alexa_media_player/commit/d430e7e22b96569c395454970a326a59b4d25c38))

* docs: update localization ([`3e41767`](https://github.com/custom-components/alexa_media_player/commit/3e41767ee98fd721e09f26955ca78f0077e703d4))

### Fix

* fix: create each subfolder for `www/alexa_tts` (#2034)

Create the root www folder before trying to create alexa_tts.

fixes #2032 ([`20cbfcd`](https://github.com/custom-components/alexa_media_player/commit/20cbfcde6d769ecc99dea16b3831883376bee5a3))

### Unknown

* Merge pull request #2036 from custom-components/dev

chore: release 2023-09-22 ([`ed7d047`](https://github.com/custom-components/alexa_media_player/commit/ed7d047d309fe3fd7a0655e68404fdbd500ab93b))

* Merge branch &#39;master&#39; into dev ([`a56374c`](https://github.com/custom-components/alexa_media_player/commit/a56374c17a11619acb9596905dd571142163fc3e))


## v4.7.1 (2023-09-15)

### Documentation

* docs: update localization ([`38f81e9`](https://github.com/custom-components/alexa_media_player/commit/38f81e93e8f9d7a6b6ed5bb5633bbbd25e2b95d3))

### Fix

* fix: use native HA methods to create paths (#2025)

closes #2022 ([`1f60c0b`](https://github.com/custom-components/alexa_media_player/commit/1f60c0b50f8696a1a2d66d748e0da33f364b47bc))

* fix: use native HA methods to create paths (#2025)

closes #2022 ([`c31dacd`](https://github.com/custom-components/alexa_media_player/commit/c31dacdab0931213990abd87c2685f0f64b16d01))


## v4.7.0 (2023-09-15)

### Build

* build: pre-commit autoupdate (#1978)

* build: pre-commit autoupdate

updates:
- [github.com/commitizen-tools/commitizen: 3.5.2 → 3.8.2](https://github.com/commitizen-tools/commitizen/compare/3.5.2...3.8.2)
- [github.com/psf/black: 23.3.0 → 23.9.1](https://github.com/psf/black/compare/23.3.0...23.9.1)
- [github.com/pre-commit/mirrors-prettier: v3.0.0-alpha.9-for-vscode → v3.0.3](https://github.com/pre-commit/mirrors-prettier/compare/v3.0.0-alpha.9-for-vscode...v3.0.3)
- [github.com/asottile/pyupgrade: v3.4.0 → v3.10.1](https://github.com/asottile/pyupgrade/compare/v3.4.0...v3.10.1)

* style: auto fixes from pre-commit.com hooks

for more information, see https://pre-commit.ci

---------

Co-authored-by: pre-commit-ci[bot] &lt;66853113+pre-commit-ci[bot]@users.noreply.github.com&gt; ([`fe67b76`](https://github.com/custom-components/alexa_media_player/commit/fe67b76f04b1ddbdbd76b33499bb72e0ef936727))

* build(deps-dev): bump gitpython from 3.1.31 to 3.1.34 (#2016)

Bumps [gitpython](https://github.com/gitpython-developers/GitPython) from 3.1.31 to 3.1.34.
- [Release notes](https://github.com/gitpython-developers/GitPython/releases)
- [Changelog](https://github.com/gitpython-developers/GitPython/blob/main/CHANGES)
- [Commits](https://github.com/gitpython-developers/GitPython/compare/3.1.31...3.1.34)

---
updated-dependencies:
- dependency-name: gitpython
  dependency-type: indirect
...

Signed-off-by: dependabot[bot] &lt;support@github.com&gt;
Co-authored-by: dependabot[bot] &lt;49699333+dependabot[bot]@users.noreply.github.com&gt; ([`4c97df8`](https://github.com/custom-components/alexa_media_player/commit/4c97df8fae007b6296cb3de6310521b73b6705ff))

### Chore

* chore: release 2023-09-14 ([`af99698`](https://github.com/custom-components/alexa_media_player/commit/af99698d580963abcf0bfafdb9dde7574796e22c))

### Documentation

* docs: update localization ([`62a477d`](https://github.com/custom-components/alexa_media_player/commit/62a477d88469e958e1d79da77ecc8d2bb8ddf7d4))

### Feature

* feat: Add support to tts.cloud_say (#2014)

* Add support to tts.cloud_say

* style: auto fixes from pre-commit.com hooks

for more information, see https://pre-commit.ci

* Fixed pre-commit validations

* style: auto fixes from pre-commit.com hooks

for more information, see https://pre-commit.ci

* Fixed pre-commit validations

* style: auto fixes from pre-commit.com hooks

for more information, see https://pre-commit.ci

* Comment as first method statement

---------

Co-authored-by: pre-commit-ci[bot] &lt;66853113+pre-commit-ci[bot]@users.noreply.github.com&gt; ([`a31e05f`](https://github.com/custom-components/alexa_media_player/commit/a31e05f3bc867da3e55ade9eeb3aed3e18576961))


## v4.6.5 (2023-06-29)

### Build

* build(deps): bump requests from 2.28.2 to 2.31.0

Bumps [requests](https://github.com/psf/requests) from 2.28.2 to 2.31.0.
- [Release notes](https://github.com/psf/requests/releases)
- [Changelog](https://github.com/psf/requests/blob/main/HISTORY.md)
- [Commits](https://github.com/psf/requests/compare/v2.28.2...v2.31.0)

---
updated-dependencies:
- dependency-name: requests
  dependency-type: indirect
...

Signed-off-by: dependabot[bot] &lt;support@github.com&gt; ([`c7f036d`](https://github.com/custom-components/alexa_media_player/commit/c7f036dea8bee42fcc72a1d226749a057f7c70e3))

* build: pre-commit autoupdate

updates:
- [github.com/commitizen-tools/commitizen: 3.2.2 → 3.5.2](https://github.com/commitizen-tools/commitizen/compare/3.2.2...3.5.2)
- [github.com/asottile/pyupgrade: v3.4.0 → v3.7.0](https://github.com/asottile/pyupgrade/compare/v3.4.0...v3.7.0)
- [github.com/floatingpurr/sync_with_poetry: 1.0.0 → 1.1.0](https://github.com/floatingpurr/sync_with_poetry/compare/1.0.0...1.1.0)
- [github.com/codespell-project/codespell: v2.2.4 → v2.2.5](https://github.com/codespell-project/codespell/compare/v2.2.4...v2.2.5) ([`bb32585`](https://github.com/custom-components/alexa_media_player/commit/bb3258578e20c8afcf19216e426af1ca2760d4f3))

* build: pre-commit autoupdate

updates:
- [github.com/commitizen-tools/commitizen: 3.2.1 → 3.2.2](https://github.com/commitizen-tools/commitizen/compare/3.2.1...3.2.2)
- [github.com/adrienverge/yamllint.git: v1.31.0 → v1.32.0](https://github.com/adrienverge/yamllint.git/compare/v1.31.0...v1.32.0)
- [github.com/floatingpurr/sync_with_poetry: 0.4.0 → 1.0.0](https://github.com/floatingpurr/sync_with_poetry/compare/0.4.0...1.0.0)
- [github.com/PyCQA/prospector: v1.9.0 → 1.10.2](https://github.com/PyCQA/prospector/compare/v1.9.0...1.10.2) ([`bb3ce86`](https://github.com/custom-components/alexa_media_player/commit/bb3ce8696cb2fbdbbde7c6250c9341fb5eb8be2e))

* build: fix grammar for autocloser ([`93ef95d`](https://github.com/custom-components/alexa_media_player/commit/93ef95dc64d13b3ec2f4b34f3706735b8a6c37cd))

* build: add more details to closure message ([`105f09e`](https://github.com/custom-components/alexa_media_player/commit/105f09edccbfd72f8c020e02a7f50b7fcb303941))

* build: update close message ([`2515f87`](https://github.com/custom-components/alexa_media_player/commit/2515f87dc5db19b6550a01c43dfffc8110dbacee))

* build: remove stray , ([`ffe1c8a`](https://github.com/custom-components/alexa_media_player/commit/ffe1c8a6528ec847e5a43ed433ed53482ea53b55))

* build: switch to autocloser ([`c7e815c`](https://github.com/custom-components/alexa_media_player/commit/c7e815cdee3ebb3806d1a20285abf2235064c873))

* build: remove grouping in regex ([`58002da`](https://github.com/custom-components/alexa_media_player/commit/58002da44c6883929928ee3a9a48b8d9ddd97f26))

* build: update moderator regex ([`8e8833d`](https://github.com/custom-components/alexa_media_player/commit/8e8833d0ca136202ccb52f4a4bb3ae38e372e72a))

* build: add missing brackets ([`5707576`](https://github.com/custom-components/alexa_media_player/commit/57075761f4d16106055462c5f51bc0a7fc95a4d3))

* build: remove some escapes ([`dc639bc`](https://github.com/custom-components/alexa_media_player/commit/dc639bc90dcf0c542e1ed09344f4c85d0038a279))

* build: add further json escaping ([`ff52184`](https://github.com/custom-components/alexa_media_player/commit/ff521843e8a30e56ec7a25388c3b909e0391bab7))

* build: escape regex special chars ([`d853162`](https://github.com/custom-components/alexa_media_player/commit/d853162b5b1e5bca4b4728bd02ee50312eb3f69f))

* build: add issue moderator ([`cd75e7a`](https://github.com/custom-components/alexa_media_player/commit/cd75e7a24dbff815fb28c68db72643ebe2c9143d))

* build: pre-commit autoupdate

updates:
- [github.com/commitizen-tools/commitizen: 3.1.1 → 3.2.1](https://github.com/commitizen-tools/commitizen/compare/3.1.1...3.2.1) ([`5d3421f`](https://github.com/custom-components/alexa_media_player/commit/5d3421f1783ab4f58bd590f88e16395e64af3009))

### Ci

* ci: Create moderate.yaml

Reenable autocloser. ([`115811e`](https://github.com/custom-components/alexa_media_player/commit/115811e97edee8dcb5bcb9b40e00ac54fedb2964))

### Fix

* fix: update notifications on PUSH_ACTIVITY (#1974)

Amazon appears to have deprecated the prior NOTIFICATION_UPDATE event.

closes #1971 ([`8f0dfa2`](https://github.com/custom-components/alexa_media_player/commit/8f0dfa2f6585ebac08bd5a708951155c80f63588))

### Style

* style: fix yamllint ([`1c8bc37`](https://github.com/custom-components/alexa_media_player/commit/1c8bc370bf7003d15ecba17090ad403d95fcc0eb))

* style: auto fixes from pre-commit.com hooks

for more information, see https://pre-commit.ci ([`b1079d4`](https://github.com/custom-components/alexa_media_player/commit/b1079d45bf113161d652ed79498f4a905fd7ed92))

* style: auto fixes from pre-commit.com hooks

for more information, see https://pre-commit.ci ([`eab6bbd`](https://github.com/custom-components/alexa_media_player/commit/eab6bbdcad258f9537794899c3bd336206d6402d))

### Unknown

* Merge pull request #1975 from custom-components/dev

chore: release 2023-06-29 ([`7d1cd86`](https://github.com/custom-components/alexa_media_player/commit/7d1cd86e6efefeabec86bfd8c62fedaad15c08e0))

* Merge pull request #1973 from custom-components/dependabot/pip/requests-2.31.0

build(deps): bump requests from 2.28.2 to 2.31.0 ([`e097e38`](https://github.com/custom-components/alexa_media_player/commit/e097e389c622792410c88d96f349c7f77c8dbe2b))

* Merge pull request #1962 from custom-components/pre-commit-ci-update-config

build: pre-commit autoupdate ([`2c111c0`](https://github.com/custom-components/alexa_media_player/commit/2c111c0554049caa4c51cbacc1f187ee09ec6f8b))

* Merge pull request #1952 from custom-components/pre-commit-ci-update-config

build: pre-commit autoupdate ([`b3d5fd5`](https://github.com/custom-components/alexa_media_player/commit/b3d5fd5b82481b9765036853e84c2164fa8862a3))

* Merge pull request #1938 from custom-components/pre-commit-ci-update-config

build: pre-commit autoupdate ([`080c8f8`](https://github.com/custom-components/alexa_media_player/commit/080c8f87b8960a635f052a4793161bf4b3cf063f))


## v4.6.4 (2023-05-08)

### Build

* build: bump precommit deps ([`11bf978`](https://github.com/custom-components/alexa_media_player/commit/11bf97861df29e8311cfb0121393af0429085dc0))

### Fix

* fix: fix unbound account variable ([`3867a54`](https://github.com/custom-components/alexa_media_player/commit/3867a54e170b85239c8cd076e84125c47f1f2af4))

* fix: bump alexapy to 1.26.8

closes #1932 ([`0c65b41`](https://github.com/custom-components/alexa_media_player/commit/0c65b4131de4c5fff20633250f05da44c58a1a01))

### Unknown

* Merge pull request #1934 from custom-components/dev

chore: release 2023-05-07 3 ([`2a3be7e`](https://github.com/custom-components/alexa_media_player/commit/2a3be7e20ab8d90c31c77c6d6bbe2fe165fa739f))

* Merge pull request #1933 from alandtse/dev

fix: bump alexapy to 1.26.8 ([`35cc257`](https://github.com/custom-components/alexa_media_player/commit/35cc2572b27874c9b185adef345c2053fab18fbf))


## v4.6.3 (2023-05-07)

### Build

* build: pre-commit autoupdate

updates:
- [github.com/commitizen-tools/commitizen: 3.0.1 → 3.1.1](https://github.com/commitizen-tools/commitizen/compare/3.0.1...3.1.1)
- [github.com/psf/black: 23.1.0 → 23.3.0](https://github.com/psf/black/compare/23.1.0...23.3.0)
- [github.com/asottile/pyupgrade: v3.3.1 → v3.3.2](https://github.com/asottile/pyupgrade/compare/v3.3.1...v3.3.2) ([`b3f0df7`](https://github.com/custom-components/alexa_media_player/commit/b3f0df7661de6222d78be60c4ed8368284c32f49))

* build: pre-commit autoupdate

updates:
- [github.com/commitizen-tools/commitizen: v2.42.1 → 3.0.1](https://github.com/commitizen-tools/commitizen/compare/v2.42.1...3.0.1)
- [github.com/psf/black: 23.1.0 → 23.3.0](https://github.com/psf/black/compare/23.1.0...23.3.0)
- [github.com/pre-commit/mirrors-prettier: v3.0.0-alpha.6 → v3.0.0-alpha.9-for-vscode](https://github.com/pre-commit/mirrors-prettier/compare/v3.0.0-alpha.6...v3.0.0-alpha.9-for-vscode)
- [github.com/adrienverge/yamllint.git: v1.30.0 → v1.31.0](https://github.com/adrienverge/yamllint.git/compare/v1.30.0...v1.31.0) ([`9b6b67e`](https://github.com/custom-components/alexa_media_player/commit/9b6b67e18d97f1cc93f54357d23b004bd6f19ea8))

* build: pre-commit autoupdate

updates:
- [github.com/psf/black: 23.1.0 → 23.3.0](https://github.com/psf/black/compare/23.1.0...23.3.0) ([`d699da6`](https://github.com/custom-components/alexa_media_player/commit/d699da6ee6f97439f2e88c274acc5a7205692a42))

* build: pre-commit autoupdate

updates:
- [github.com/psf/black: 23.1.0 → 23.3.0](https://github.com/psf/black/compare/23.1.0...23.3.0)
- [github.com/adrienverge/yamllint.git: v1.29.0 → v1.30.0](https://github.com/adrienverge/yamllint.git/compare/v1.29.0...v1.30.0) ([`d360eb0`](https://github.com/custom-components/alexa_media_player/commit/d360eb026d925974b9e7c510f03b7c320017fbed))

* build: pre-commit autoupdate

updates:
- [github.com/PyCQA/bandit: 1.7.4 → 1.7.5](https://github.com/PyCQA/bandit/compare/1.7.4...1.7.5)
- [github.com/codespell-project/codespell: v2.2.2 → v2.2.4](https://github.com/codespell-project/codespell/compare/v2.2.2...v2.2.4) ([`e9873a1`](https://github.com/custom-components/alexa_media_player/commit/e9873a14a756ceb56a95cad50855138223e38192))

### Chore

* chore: release 2023-05-07 ([`84d2af5`](https://github.com/custom-components/alexa_media_player/commit/84d2af541076fd13e443c6513efb04f5b5ab5a42))

* chore: merge dev 23-05-07 ([`74d2e7a`](https://github.com/custom-components/alexa_media_player/commit/74d2e7a8f4b4895001a3944074212e052a3844b1))

### Documentation

* docs: update localization ([`2ef2032`](https://github.com/custom-components/alexa_media_player/commit/2ef2032404ccee65a715f743946286f82e252bf4))

* docs: replace deprecated Text with str ([`d6e706d`](https://github.com/custom-components/alexa_media_player/commit/d6e706d81eee81d3195f5a3d29752b5471f644bf))

### Fix

* fix: bump alexapy to 1.26.6

This should remove the :0 for hass urls without port designations.

closes #1927
closes #1928 ([`06ec7be`](https://github.com/custom-components/alexa_media_player/commit/06ec7be963acab33bea721180b9ae7501de74543))

* fix: handle missing email from config

fixes #1889
fixes #1929 ([`358fd5c`](https://github.com/custom-components/alexa_media_player/commit/358fd5cb646267b4b2a2463e5a9cc37d84d0fcaa))

* fix: skip null entity_ids for notify service

closes #1878
closes #1889
closes #1929 ([`ed0c028`](https://github.com/custom-components/alexa_media_player/commit/ed0c0281006d89450a6d785cd7e0113e39dfe404))

* fix: fix otp_secret grammar (#1918) ([`4e1158e`](https://github.com/custom-components/alexa_media_player/commit/4e1158e4adc10cd14a7f67117d782a3edec63a66))

### Style

* style: auto fixes from pre-commit.com hooks

for more information, see https://pre-commit.ci ([`c7acfd7`](https://github.com/custom-components/alexa_media_player/commit/c7acfd717f2cc453d66f36074c0514bf30a57a04))

* style: auto fixes from pre-commit.com hooks

for more information, see https://pre-commit.ci ([`7469c28`](https://github.com/custom-components/alexa_media_player/commit/7469c28c60bf1708f1a5536a83856af380cd966c))

* style: auto fixes from pre-commit.com hooks

for more information, see https://pre-commit.ci ([`735f06c`](https://github.com/custom-components/alexa_media_player/commit/735f06c8f88b2d649183231320f53d44fa125618))

* style: auto fixes from pre-commit.com hooks

for more information, see https://pre-commit.ci ([`4f1f82d`](https://github.com/custom-components/alexa_media_player/commit/4f1f82d7ce04424281e7ac611f81d4eb135ef44f))

### Unknown

* Merge pull request #1920 from custom-components/pre-commit-ci-update-config

build: pre-commit autoupdate ([`eb5a260`](https://github.com/custom-components/alexa_media_player/commit/eb5a26098d48e8b9e45aeeea50e10033e8780800))

* Grammar fix ([`4c2c93a`](https://github.com/custom-components/alexa_media_player/commit/4c2c93a247ac49a5104c1266dd1abceb41d8b863))

* Merge pull request #1909 from custom-components/pre-commit-ci-update-config

build: pre-commit autoupdate ([`f02e698`](https://github.com/custom-components/alexa_media_player/commit/f02e6988984326d3fa6a81f345cb00735e0c4f19))

* Merge pull request #1903 from custom-components/pre-commit-ci-update-config

build: pre-commit autoupdate ([`037b3b9`](https://github.com/custom-components/alexa_media_player/commit/037b3b9462152638b9c2a09c86ad07da81dfd076))

* Merge pull request #1893 from custom-components/pre-commit-ci-update-config

build: pre-commit autoupdate ([`a0243b4`](https://github.com/custom-components/alexa_media_player/commit/a0243b4027575967c205af6b818733a7e6bcace6))

* Merge pull request #1885 from custom-components/pre-commit-ci-update-config

build: pre-commit autoupdate ([`aecd79c`](https://github.com/custom-components/alexa_media_player/commit/aecd79c960217b46b3b6c342de838c6fae0e19cf))


## v4.6.2 (2023-03-08)

### Fix

* fix: exclude alarm json data from database

This addresses the next_alarm filling up the database.

closes #1867 ([`18e4bcf`](https://github.com/custom-components/alexa_media_player/commit/18e4bcf49c49e77cd37519d97b0cc5ac5556ecc7))

### Unknown

* Merge pull request #1876 from custom-components/dev

chore: release 2023-03-07 ([`67fcd92`](https://github.com/custom-components/alexa_media_player/commit/67fcd9295e8c221ef5f9393810ff3e5ab2b82cea))

* Merge pull request #1875 from alandtse/dev

fix: exclude alarm json data from database ([`c5bfbe8`](https://github.com/custom-components/alexa_media_player/commit/c5bfbe846e4efdd15a33b0e71e9adb2ada258f80))


## v4.6.1 (2023-03-07)

### Build

* build: bump pre-commit ([`0c11127`](https://github.com/custom-components/alexa_media_player/commit/0c11127465e109ce93d7ccc77ebc0f5f05c6ddaa))

* build: pre-commit autoupdate

updates:
- [github.com/commitizen-tools/commitizen: v2.40.0 → v2.42.1](https://github.com/commitizen-tools/commitizen/compare/v2.40.0...v2.42.1)
- [github.com/psf/black: 23.1a1 → 23.1.0](https://github.com/psf/black/compare/23.1a1...23.1.0)
- [github.com/pre-commit/mirrors-prettier: v3.0.0-alpha.4 → v3.0.0-alpha.6](https://github.com/pre-commit/mirrors-prettier/compare/v3.0.0-alpha.4...v3.0.0-alpha.6)
- [github.com/PyCQA/prospector: v1.8.4 → v1.9.0](https://github.com/PyCQA/prospector/compare/v1.8.4...v1.9.0) ([`52864b1`](https://github.com/custom-components/alexa_media_player/commit/52864b1e1e620054a83f7e930ba170ae8d93195c))

* build: update min HA version ([`53aa5e9`](https://github.com/custom-components/alexa_media_player/commit/53aa5e911af8d6625d95c46a9c58c084cb5ab70d))

* build: pre-commit autoupdate

updates:
- [github.com/psf/black: 23.1a1 → 23.1.0](https://github.com/psf/black/compare/23.1a1...23.1.0) ([`8ff7175`](https://github.com/custom-components/alexa_media_player/commit/8ff7175c5436a381f74dc1a435d3a063bdda25e7))

### Documentation

* docs: update localization ([`f70d613`](https://github.com/custom-components/alexa_media_player/commit/f70d613a9959a6ebd5ed735ba30b1d30141d99ab))

### Fix

* fix: add None checks

closes #1872 ([`40bb9d2`](https://github.com/custom-components/alexa_media_player/commit/40bb9d23523faf13a4a8abc8ee84f6852dab0218))

* fix: bump alexapy to 1.26.5

Fix case where domainAttributes is empty from dnd endpoint.

closes #1844 ([`289c611`](https://github.com/custom-components/alexa_media_player/commit/289c611a5331637f031a4e97b7f3a0e296bd1179))

### Style

* style: auto fixes from pre-commit.com hooks

for more information, see https://pre-commit.ci ([`f9addd3`](https://github.com/custom-components/alexa_media_player/commit/f9addd3e7b63d6dfcf040790e23fb7e08663fc96))

* style: sort manifest.json ([`7cff7fd`](https://github.com/custom-components/alexa_media_player/commit/7cff7fd97c54b3421f61091d6ab72ad438f8eebf))

* style: auto fixes from pre-commit.com hooks

for more information, see https://pre-commit.ci ([`0875141`](https://github.com/custom-components/alexa_media_player/commit/087514119155698a561834ff4cc5c5b9e34ba73b))

### Unknown

* Merge pull request #1874 from custom-components/dev

chore: release 2023-03-06 ([`e2b1da9`](https://github.com/custom-components/alexa_media_player/commit/e2b1da9e91cd57af1b06398ada18cf8a067222d6))

* Merge pull request #1873 from alandtse/dev

chore: fix various outstanding bugs ([`4cd6ef8`](https://github.com/custom-components/alexa_media_player/commit/4cd6ef85e56f187eaf23ba728910eb4b380653fd))

* Merge pull request #1858 from custom-components/pre-commit-ci-update-config

build: pre-commit autoupdate ([`f16ea2d`](https://github.com/custom-components/alexa_media_player/commit/f16ea2d75ddfa13173a7bd2a586ff34084845fa8))

* Merge pull request #1868 from alandtse/dev

style: sort manifest.json ([`9bb197c`](https://github.com/custom-components/alexa_media_player/commit/9bb197c54d4142af4af1e28a36d6fe1dde18a0b5))

* Merge branch &#39;dev&#39; of https://github.com/alandtse/alexa_media_player into dev ([`10664b2`](https://github.com/custom-components/alexa_media_player/commit/10664b2ce0f7a17ce858c231b79ad3b3d064646b))

* Merge pull request #1855 from custom-components/pre-commit-ci-update-config

build: pre-commit autoupdate ([`2ee19cf`](https://github.com/custom-components/alexa_media_player/commit/2ee19cf92749ba3e1f829d9aebcf83e777890f85))

* Merge pull request #1812 from custom-components/pre-commit-ci-update-config

build: pre-commit autoupdate ([`f89aedb`](https://github.com/custom-components/alexa_media_player/commit/f89aedb0767d9e7eee2dbce79283f2db2a9929aa))


## v4.6.0 (2023-01-31)

### Build

* build: pre-commit autoupdate

updates:
- [github.com/commitizen-tools/commitizen: v2.38.0 → v2.40.0](https://github.com/commitizen-tools/commitizen/compare/v2.38.0...v2.40.0)
- [github.com/psf/black: 23.1a1 → 22.12.0](https://github.com/psf/black/compare/23.1a1...22.12.0)
- [github.com/adrienverge/yamllint.git: v1.27.1 → v1.29.0](https://github.com/adrienverge/yamllint.git/compare/v1.27.1...v1.29.0)
- [github.com/PyCQA/isort: 5.11.4 → 5.12.0](https://github.com/PyCQA/isort/compare/5.11.4...5.12.0)
- [github.com/PyCQA/prospector: v1.8.3 → v1.8.4](https://github.com/PyCQA/prospector/compare/v1.8.3...v1.8.4) ([`a37687f`](https://github.com/custom-components/alexa_media_player/commit/a37687fef1dcdcf36d7130813587db67398d3147))

### Feature

* feat: add ledvance bluetooth bulbs (#1847)

closes #1839 ([`5816afe`](https://github.com/custom-components/alexa_media_player/commit/5816afe60852218684594471fb86b8d399eda64b))

### Style

* style: auto fixes from pre-commit.com hooks

for more information, see https://pre-commit.ci ([`ee86e16`](https://github.com/custom-components/alexa_media_player/commit/ee86e169c1dfa8a7875b8f158112d0420df0f2ff))

### Unknown

* Merge pull request #1848 from custom-components/dev

feat: add ledvance bluetooth bulbs (#1847) ([`4e0eba4`](https://github.com/custom-components/alexa_media_player/commit/4e0eba4481779e60f0653a4d67b46769978a393d))


## v4.5.3 (2023-01-14)

### Fix

* fix: update coordinator callback to update sensors

closes #1834
closes #1833 ([`708b6c5`](https://github.com/custom-components/alexa_media_player/commit/708b6c52eba7d2bb853005a5acb6ce6ad11ffa7a))

### Unknown

* Merge pull request #1838 from custom-components/dev

2023-01-14.3 ([`a666234`](https://github.com/custom-components/alexa_media_player/commit/a666234dc9826e83d96e8db1958f11b88eb6178e))

* Merge pull request #1837 from custom-components/1824

fix: update coordinator callback to update sensors ([`d521dc7`](https://github.com/custom-components/alexa_media_player/commit/d521dc7b9175cad39b836c521bb5338d5af0e818))


## v4.5.2 (2023-01-14)

### Fix

* fix: restore alexa_entity_id attribute

closes #1830 ([`7ca77d9`](https://github.com/custom-components/alexa_media_player/commit/7ca77d97e6f71d66aba036a260ee1553c0f55e39))

### Unknown

* Merge pull request #1832 from custom-components/dev

2023-01-14.2 ([`f466e69`](https://github.com/custom-components/alexa_media_player/commit/f466e6922e01745c75f4649384a1117efde768cc))

* Merge pull request #1831 from custom-components/1824

fix: restore alexa_entity_id attribute ([`64a2a41`](https://github.com/custom-components/alexa_media_player/commit/64a2a41d9394a6c2397e10b6980b0f5bf56ca62e))


## v4.5.1 (2023-01-14)

### Fix

* fix: set state_class for numerical sensors

closes #1827 ([`0a0788e`](https://github.com/custom-components/alexa_media_player/commit/0a0788e94eeb7b9be35c38580cdf4be7f96ff399))

* fix: fix alarms, timers, and reminders

Complete update to native_value units deprecated as of HA 2021.12.

closes #1824 ([`65ae48a`](https://github.com/custom-components/alexa_media_player/commit/65ae48a016204c7b45a3f9ae5f7018ee66dcd07c))

### Refactor

* refactor: simplify code

Swap to _attr based variables ([`6017a62`](https://github.com/custom-components/alexa_media_player/commit/6017a62e4965d2dc5678b37fdaf61189049906e7))

### Unknown

* Merge pull request #1829 from custom-components/dev

2023-01-14 ([`ad20d27`](https://github.com/custom-components/alexa_media_player/commit/ad20d279ea5ecef2e243dc3305b87c50241a0a1b))

* Merge pull request #1828 from custom-components/1824

fix: fix alarms, timers, and reminders ([`998264a`](https://github.com/custom-components/alexa_media_player/commit/998264a1dd791e4960b16874c43b7f89d3f5969b))


## v4.5.0 (2023-01-12)

### Build

* build: exclude changelog from prettier ([`769467c`](https://github.com/custom-components/alexa_media_player/commit/769467cfcadb933785f771d3b358634367d9fc76))

* build: exclude translations ([`fe147a4`](https://github.com/custom-components/alexa_media_player/commit/fe147a41f7ff13b1935da2e148f247f9876e8d17))

* build: disable mccabe ([`7841491`](https://github.com/custom-components/alexa_media_player/commit/784149140c737bb35df055992a532c16b431324a))

* build: ignore hass ([`09682d1`](https://github.com/custom-components/alexa_media_player/commit/09682d1f8c01258e6e413c5cc8b0ac50a4b59721))

* build: simplify deps ([`f06a1d0`](https://github.com/custom-components/alexa_media_player/commit/f06a1d01398558d44e988489457258c2afa21af5))

* build: ignore flake errors ([`c11af6f`](https://github.com/custom-components/alexa_media_player/commit/c11af6fd83add796928730d743add3a5ca5eca55))

* build: suppress additional pylint errors ([`db2a86c`](https://github.com/custom-components/alexa_media_player/commit/db2a86cdf7c9012f971436bcf07d507b43c7c83b))

* build: update precommit to python39 ([`7ec13d3`](https://github.com/custom-components/alexa_media_player/commit/7ec13d354e2e68ffeb87996a0e62bac258a93ab7))

* build: fix pylintrc name ([`9d36c5d`](https://github.com/custom-components/alexa_media_player/commit/9d36c5db15403a972b4da0c5a268c7a1ea938542))

* build: disable devcontainer lint ([`6302f97`](https://github.com/custom-components/alexa_media_player/commit/6302f97cfc4890d4dbc028169b76d77bdb375474))

* build: fix flake8 url ([`059b05c`](https://github.com/custom-components/alexa_media_player/commit/059b05cd8fb6e13b73e719a2b9d5fe6ab9b0c143))

* build: add codespell and flake8 ([`87785e6`](https://github.com/custom-components/alexa_media_player/commit/87785e6bb5bfff3384df26b5995c9e5ae77b1bf3))

* build: add pre-commit.ci ([`7c25444`](https://github.com/custom-components/alexa_media_player/commit/7c2544433873bab2de7ab2505853826e3b44b9bf))

### Ci

* ci: add yamllint ([`df1ad70`](https://github.com/custom-components/alexa_media_player/commit/df1ad70cdbb17c1f7b419e98d9c765861c79a2dd))

### Feature

* feat: Add Amazon Indoor Air Quality Monitor (#1803) ([`09915ea`](https://github.com/custom-components/alexa_media_player/commit/09915eafa8b8b54e8f00b8053b582538b5d96b02))

### Style

* style: commit prettier changes ([`2afd331`](https://github.com/custom-components/alexa_media_player/commit/2afd3314e5943d5130d582cb49ed0162dadd9af2))

* style: fix prospector errors ([`b2b4e37`](https://github.com/custom-components/alexa_media_player/commit/b2b4e377dfd74d57273213dfeb07662ad30a8f6c))

### Unknown

* Merge pull request #1822 from custom-components/dev

2023-01-11 ([`0ce8d4c`](https://github.com/custom-components/alexa_media_player/commit/0ce8d4cdac8ac470f2aa6e26d01e46740b944ea2))

* Merge pull request #1811 from alandtse/dev ([`d88a8f2`](https://github.com/custom-components/alexa_media_player/commit/d88a8f26ba4d9602a06f44eadcd1b881f07573b3))


## v4.4.0 (2022-12-24)

### Build

* build(deps): bump cryptography from 38.0.2 to 38.0.3

Bumps [cryptography](https://github.com/pyca/cryptography) from 38.0.2 to 38.0.3.
- [Release notes](https://github.com/pyca/cryptography/releases)
- [Changelog](https://github.com/pyca/cryptography/blob/main/CHANGELOG.rst)
- [Commits](https://github.com/pyca/cryptography/compare/38.0.2...38.0.3)

---
updated-dependencies:
- dependency-name: cryptography
  dependency-type: indirect
...

Signed-off-by: dependabot[bot] &lt;support@github.com&gt; ([`470a25b`](https://github.com/custom-components/alexa_media_player/commit/470a25bcd7811a1a31c2082332ba60c83c44f1e4))

* build(deps): bump certifi from 2022.9.24 to 2022.12.7

Bumps [certifi](https://github.com/certifi/python-certifi) from 2022.9.24 to 2022.12.7.
- [Release notes](https://github.com/certifi/python-certifi/releases)
- [Commits](https://github.com/certifi/python-certifi/compare/2022.09.24...2022.12.07)

---
updated-dependencies:
- dependency-name: certifi
  dependency-type: indirect
...

Signed-off-by: dependabot[bot] &lt;support@github.com&gt; ([`001670f`](https://github.com/custom-components/alexa_media_player/commit/001670f09f3766d3dab478b25bd1227abb5ced69))

### Feature

* feat: add debug loggers support ([`37a795d`](https://github.com/custom-components/alexa_media_player/commit/37a795d42367f2e1527a01c9177c41443ccc386b))

### Unknown

* Merge pull request #1805 from custom-components/dev

2022-12-23 ([`8b20f38`](https://github.com/custom-components/alexa_media_player/commit/8b20f38b6d3f2cfab2d69d91aeb95e7f41bb4fe2))

* Merge pull request #1804 from alandtse/debug_loggers

feat: add debug loggers support ([`e9dc226`](https://github.com/custom-components/alexa_media_player/commit/e9dc2263545e0ffcf7f56b3791cf0d816f2d9656))

* Merge pull request #1796 from custom-components/dependabot/pip/cryptography-38.0.3

build(deps): bump cryptography from 38.0.2 to 38.0.3 ([`fc6070f`](https://github.com/custom-components/alexa_media_player/commit/fc6070f0e379fb62c791f8e51378527173dc17ce))

* Merge pull request #1795 from custom-components/dependabot/pip/certifi-2022.12.7

build(deps): bump certifi from 2022.9.24 to 2022.12.7 ([`ff3d4aa`](https://github.com/custom-components/alexa_media_player/commit/ff3d4aa2564060f69eeec3e1e1e067abb478d04b))


## v4.3.2 (2022-11-03)

### Fix

* fix: fix misconfigured HA url overriding url input

The get_url command would throw an exception even when hass_url was
provided through the form.
This would end up ignoring the hass_url input and result in a form loop.

Thanks to @String-656 for testing and discovering this.

closes #1727 ([`02297a4`](https://github.com/custom-components/alexa_media_player/commit/02297a4537ea36c77551ba10e4efe57e3dacfc8a))

### Unknown

* Merge pull request #1770 from custom-components/dev

2022-11-02 ([`24c93c0`](https://github.com/custom-components/alexa_media_player/commit/24c93c01f1159f5dfeabf2f9d24d056d8e3f56bf))

* Merge pull request #1769 from alandtse/1727

fix: fix misconfigured HA url overriding url input ([`9daa957`](https://github.com/custom-components/alexa_media_player/commit/9daa957739fb78e4634610061814d85b5a03dc56))


## v4.3.1 (2022-11-02)

### Fix

* fix(notify): handle null data key (#1767)

* FIX New default tts missing

* FIX if condition data

Co-authored-by: Carsten Docktor &lt;carsten.docktor@fgh-zertifizierung.de&gt;
closes #1764 ([`08c2109`](https://github.com/custom-components/alexa_media_player/commit/08c2109ee24d673a7b29d1f1244569f5dee40004))

### Unknown

* Merge pull request #1768 from custom-components/dev

fix(notify): handle null data key (#1767) ([`06091a8`](https://github.com/custom-components/alexa_media_player/commit/06091a8bffdcb6ec979fba87c8b7b0858d421380))


## v4.3.0 (2022-10-31)

### Feature

* feat: Add ZigBee contact sensors support (#1754)

* Add ZigBee contact sensors support

* Respect unavailable state of binary_sensor

* Add safe get of applianceTypes

Co-authored-by: Cosimo Meli &lt;cosimo.meli@chili.com&gt; ([`cd162cb`](https://github.com/custom-components/alexa_media_player/commit/cd162cbb8ebbea5af19c0d370621c4f8e169cf5a))

### Unknown

* Merge pull request #1766 from custom-components/dev

feat: Add ZigBee contact sensors support (#1754) ([`15f9290`](https://github.com/custom-components/alexa_media_player/commit/15f92906a85ae2183315c50e0b040566dc9db0e1))


## v4.2.0 (2022-10-29)

### Chore

* chore: update bug template ([`0d5588a`](https://github.com/custom-components/alexa_media_player/commit/0d5588aebf30a5b942d62dc786d0289735185ac7))

### Ci

* ci: streamline semantic_release ([`318209d`](https://github.com/custom-components/alexa_media_player/commit/318209dc6e2ed2979134c867418723a4de633d38))

### Documentation

* docs: update localization ([`9176592`](https://github.com/custom-components/alexa_media_player/commit/9176592572a160f5af04c575079688ac12be2a2e))

### Feature

* feat(notify): set default data `type` to `tts` (#1739)

* CHANGE Set `data` value to empty dict instead of None if missing

* CHANGE Set `type: tts` as default type for notify service

* UPDATE Specify error message if data type could not be recognized

Co-authored-by: Carsten Docktor &lt;carsten.docktor@fgh-zertifizierung.de&gt; ([`7027e4a`](https://github.com/custom-components/alexa_media_player/commit/7027e4a992259029a7745bc2d8b32ea08076d7da))

### Fix

* fix: handle None responses in clear_history

Bumps alexapy to 1.26.4

closes #1735 ([`52b1c6e`](https://github.com/custom-components/alexa_media_player/commit/52b1c6e85b4aaa021ed5bc09f2ef6172f00b1700))

* fix: handle key errors due to bad alexa responses

closes #1753 ([`5788ab8`](https://github.com/custom-components/alexa_media_player/commit/5788ab887ec621d8811936f79f1308e5948b0e92))

### Unknown

* Merge pull request #1763 from custom-components/dev

2022-10-28 ([`072fcfb`](https://github.com/custom-components/alexa_media_player/commit/072fcfb2bca231fb6eea1c87925fec924b3bb1ed))

* Merge pull request #1762 from alandtse/1753

fix: handle None responses in clear_history ([`4191452`](https://github.com/custom-components/alexa_media_player/commit/4191452666efa36940c2d70f7f7d4c192162397b))

* Merge pull request #1761 from alandtse/1753

fix: handle key errors due to bad alexa responses ([`94ae728`](https://github.com/custom-components/alexa_media_player/commit/94ae728f2986d33883b71177943ce9eddc683d73))


## v4.1.2 (2022-09-07)

### Fix

* fix: check for missing hass_url during auto reauth

Reauth attempts may not have a hass url configured. Now, it will try to
generate it or request it from the user.

closes #1702 ([`7d181a3`](https://github.com/custom-components/alexa_media_player/commit/7d181a39435cb7958d0b3ccba36e7a0ebd8eccdb))

* fix: fix reauth caused by bad amazon response

Amazon EU servers are returning random http errors now beyond 500.
The responses aren&#39;t json and would trigger the reauth code.

Thanks to @dpembo for providing the logs
closes #1717 ([`58af5b3`](https://github.com/custom-components/alexa_media_player/commit/58af5b3027d34fdcf13c16dae9e12f92671958b3))

### Unknown

* Merge pull request #1720 from custom-components/dev

2022-09-07 ([`1475ba7`](https://github.com/custom-components/alexa_media_player/commit/1475ba76e7d71f94a004c7c5ab3ce653083fa320))

* Merge pull request #1719 from alandtse/1717

1717 ([`3991e24`](https://github.com/custom-components/alexa_media_player/commit/3991e24fe5cc7bbd3036ec45be3fc0fa4e3d6948))


## v4.1.1 (2022-09-05)

### Chore

* chore: disable blank issues ([`458a594`](https://github.com/custom-components/alexa_media_player/commit/458a594354055d49efc29a42e36a9d909b8deaec))

### Documentation

* docs: update localization ([`5b174b7`](https://github.com/custom-components/alexa_media_player/commit/5b174b7ada550485eaa02ffb48227aa529fed72a))

### Fix

* fix(notify): improve message for missing keys

closes #1679 ([`c2ce6a4`](https://github.com/custom-components/alexa_media_player/commit/c2ce6a42caf7f9355671c4488358e318c45ff2a4))

* fix: fix unnecessary reauth if 500 error detected

When Amazon servers experience an internal server error, this would
return a bad response that was treated as a bad login. We now ignore
this response. This was likely an issue happening in the EU.

closes #1701 ([`a8aab6b`](https://github.com/custom-components/alexa_media_player/commit/a8aab6bfe513bf4dbec361baa5d3b60fa98c99ef))

* fix: ignore missing async_remove_listener

This should fix the unload/reload error when the DataUpdateCoordinator
is in a weird state.
https://github.com/custom-components/alexa_media_player/issues/1697#issuecomment-1233873130 ([`06626dc`](https://github.com/custom-components/alexa_media_player/commit/06626dc1455f8b6c288249544ecd8439782663a5))

* fix: fix temperature showing in Celsius (#1682) ([`13afaa8`](https://github.com/custom-components/alexa_media_player/commit/13afaa846e3b40c364699f873b54bd4feaa8b24e))

### Unknown

* Merge pull request #1707 from custom-components/dev

2022-09-04 ([`5e055a5`](https://github.com/custom-components/alexa_media_player/commit/5e055a538ecc37968bdaad0867a02573caa46fa3))

* Merge pull request #1706 from alandtse/1701

1701 ([`5afe608`](https://github.com/custom-components/alexa_media_player/commit/5afe608fdacade6419db3e951c9b6cfab7fbd6be))

* Merge pull request #1674 from alandtse/templates

chore: disable blank issues ([`3a12819`](https://github.com/custom-components/alexa_media_player/commit/3a1281977556d4d698b5fb54452739316edaf312))


## v4.1.0 (2022-07-21)

### Build

* build: update pre-commit hooks ([`3ee5544`](https://github.com/custom-components/alexa_media_player/commit/3ee5544c21e7e2ae5ce569d9d290a7ee045000b5))

### Chore

* chore: require template use for issues ([`ac93145`](https://github.com/custom-components/alexa_media_player/commit/ac93145cfdbbad3c0ae112ff512a61502738f36d))

### Documentation

* docs: update localization ([`76cfff2`](https://github.com/custom-components/alexa_media_player/commit/76cfff281cbdad9d6ef27a05b6ec9585c7e9af6f))

### Feature

* feat: allow skipping of proxy warning

Allow users to bypass test to confirm HA is reachable. Users will not
get further login support when bypassing. ([`5ed2082`](https://github.com/custom-components/alexa_media_player/commit/5ed208250f6c3e951e653fa2f88ff3345c5496ce))

### Refactor

* refactor: replace hard coded strings ([`a08cc04`](https://github.com/custom-components/alexa_media_player/commit/a08cc04754d2fa960ffe5c89812717c4683994ab))

### Unknown

* Merge pull request #1672 from custom-components/dev

2022-07-20 ([`92962a5`](https://github.com/custom-components/alexa_media_player/commit/92962a574b3b62185bc09a2feac9244c2b0bc3b1))

* Merge pull request #1671 from alandtse/templates

Proxy warning skipping ([`93e8e40`](https://github.com/custom-components/alexa_media_player/commit/93e8e40dca94bf2f38a1ef9ab7ed69881b0b2c7d))


## v4.0.3 (2022-06-26)

### Build

* build: bump precommit deps ([`b6f78d7`](https://github.com/custom-components/alexa_media_player/commit/b6f78d7c1b2fc956efe441ca1930615fcef2a85b))

* build: bump pre-commit hooks ([`8dd43ea`](https://github.com/custom-components/alexa_media_player/commit/8dd43eab0184c3f2d78293bf2b87ab27a5bda4f3))

### Ci

* ci: freeze psr to v7.28.1

https://github.com/relekang/python-semantic-release/issues/442 ([`ba338c2`](https://github.com/custom-components/alexa_media_player/commit/ba338c23b51f41b2de5fa6b233c2dd32f7ac0354))

### Documentation

* docs: update localization ([`bc0ddbb`](https://github.com/custom-components/alexa_media_player/commit/bc0ddbbecea25b5dd864782d2c7ec03cfaaa0e30))

### Fix

* fix(sensor): inherit from SensorEntity

closes #1633 ([`c28b8ef`](https://github.com/custom-components/alexa_media_player/commit/c28b8efd1f800b73761db6960dc97c68af71b7c3))

* fix: fix forced relogin using configuration.yaml

Fixes bug where a configuration.yaml import always required a relogin
due to missing oauth info even if stored in config_entry. ([`a006bcc`](https://github.com/custom-components/alexa_media_player/commit/a006bcc18f81ffcb1c734b77a06f9f320dbbf842))

* fix(notifications): handle new recurrence rules

Handle new Amazon reminder and alarm recurrence rules.

closes #1608 ([`2c70eda`](https://github.com/custom-components/alexa_media_player/commit/2c70eda500d000547970c0d2d67657bcfea0e90c))

* fix: bump alexapy==1.26.1

closes #1634 ([`56a1633`](https://github.com/custom-components/alexa_media_player/commit/56a1633fe0de965ee74b0ea217a14962fb768335))

* fix: address potential race condition with last_called

closes #1638 ([`f197307`](https://github.com/custom-components/alexa_media_player/commit/f19730729413c353997f5bb5f2edff8452deacad))

### Refactor

* refactor: add next_alarm label ([`33f5d4c`](https://github.com/custom-components/alexa_media_player/commit/33f5d4c2b70c976641ff419d9d791ed0970b99d7))

### Style

* style: black ([`0ddd624`](https://github.com/custom-components/alexa_media_player/commit/0ddd6245c46d3cc2b7dfe6274fa12b159c606266))

### Unknown

* Merge pull request #1655 from custom-components/dev

2022-05-25 ([`a2da5df`](https://github.com/custom-components/alexa_media_player/commit/a2da5df411038d7ede47c909b8b1b7e1ca52636d))

* Merge pull request #1654 from alandtse/psr_v7.28.1

ci: freeze psr to v7.28.1 ([`73d4c84`](https://github.com/custom-components/alexa_media_player/commit/73d4c847b23ed61cb1a814914cadc9278d72ddd9))

* Merge pull request #1653 from alandtse/sensor_entity

fix(sensor): inherit from SensorEntity ([`3550e96`](https://github.com/custom-components/alexa_media_player/commit/3550e9699a70471b974f15fa59ba1b1e1eb371a8))

* Merge pull request #1652 from alandtse/config_import_fix

Config import fix ([`c27bfdd`](https://github.com/custom-components/alexa_media_player/commit/c27bfdd5119e529aca1a9cbcb36a207cd3bdcb66))

* Merge pull request #1651 from alandtse/#1608

fix(notifications): handle new recurrence rules ([`22a6eb1`](https://github.com/custom-components/alexa_media_player/commit/22a6eb17cb77ef744f38eb99d9cf6b426699efe0))

* Merge pull request #1650 from alandtse/#1634

#1634 ([`6711ca3`](https://github.com/custom-components/alexa_media_player/commit/6711ca328977b8be7d9fd52a616f1b5fcb434f30))


## v4.0.2 (2022-06-04)

### Documentation

* docs: update localization ([`3afd369`](https://github.com/custom-components/alexa_media_player/commit/3afd369f82f10493f9a9ad3927e3bfc0dc8360cd))

### Fix

* fix: store and reuse mac_dms between sessions

Store mac_dms in the config. This should reduce the frequency of reauth
requirements if registration is failing. This does not remove the requirement for
Amazon to provide a valid mac_dms token at least once. Users who are
unable to receive a valid mac_dms token will need to use the unsupported
3.x series.

closes #1620 ([`d663209`](https://github.com/custom-components/alexa_media_player/commit/d6632093d39a989b705ee0f8b993abae97805819))

### Unknown

* Merge pull request #1626 from custom-components/dev

2022-06-03 ([`ea849f2`](https://github.com/custom-components/alexa_media_player/commit/ea849f2928ee7e85a835408823caa51ff979e6ae))

* Merge pull request #1625 from alandtse/#1620

fix: store and reuse mac_dms between sessions ([`8518e4d`](https://github.com/custom-components/alexa_media_player/commit/8518e4dc4a3f1f8022c181331f646c5d26bbf060))


## v4.0.1 (2022-05-29)

### Build

* build: make breaking changes first in changelog ([`441688c`](https://github.com/custom-components/alexa_media_player/commit/441688cb3946f5102e9bb497b4ff28e7bc69f5c9))

### Fix

* fix: remove CONF_OAUTH_LOGIN calls

closes #1612 ([`139fded`](https://github.com/custom-components/alexa_media_player/commit/139fded9a3dcd18b78e6bcecc16034f602f4bce4))

### Unknown

* Merge pull request #1615 from custom-components/dev

2022-05-29 ([`3cda15e`](https://github.com/custom-components/alexa_media_player/commit/3cda15eb46f40738efc516c6043dd760ef219db9))

* Merge pull request #1614 from alandtse/#1612

fix: remove CONF_OAUTH_LOGIN calls ([`f229b94`](https://github.com/custom-components/alexa_media_player/commit/f229b9493562bc059f0e91f4fd5c6e3e4a4be9ac))

* Merge pull request #1611 from alandtse/breaking

build: make breaking changes first in changelog ([`3b716c5`](https://github.com/custom-components/alexa_media_player/commit/3b716c58507114467416c7020a6ebf1a95b54f46))


## v4.0.0 (2022-05-29)

### Breaking

* refactor: remove legacy login options

Remove non-proxy login and non-oauth logins. These were provided for
compatability but caused issues when users are in this state. They are
now removed. Users who require the older compatibility should use the
older versions.

BREAKING CHANGE: Legacy login and options have been removed. These options resulted in degraded operations and generated extra support requests. You will be forced to relogin if an older method is detected. ([`ee724ab`](https://github.com/custom-components/alexa_media_player/commit/ee724ab693ef58cfc2b15d3b3eeee216b9ce7caa))

### Ci

* ci: remove deprecated hacs keys ([`e78adf6`](https://github.com/custom-components/alexa_media_player/commit/e78adf6a8c3c4afe57247c7c8413a9902b55647e))

### Documentation

* docs: update localization ([`d5bbfd0`](https://github.com/custom-components/alexa_media_player/commit/d5bbfd09099da6f8197348ec17b50fad5d2c9410))

* docs: change Homeassistant to Home Assistant (#1597) ([`90037ed`](https://github.com/custom-components/alexa_media_player/commit/90037edc4db536b973b7f8d23d4a28f7df47f21c))

* docs: update HACS url (#1596) ([`d9d119a`](https://github.com/custom-components/alexa_media_player/commit/d9d119a6e8aca13bd0acf6a583ea808d2be87597))

### Fix

* fix: catch httpx.ConnectError during proxy

closes #1607 ([`96bbd55`](https://github.com/custom-components/alexa_media_player/commit/96bbd55ca99c3e314a08fe9d78e405416c0b9fcb))

* fix: treat lack of mac_dms as login failure

mac_dms field is required for websocket. To avoid degraded operations
that generate issues, we are now removing degraded operations. ([`d7c9a8c`](https://github.com/custom-components/alexa_media_player/commit/d7c9a8ce16745c747e5b83a3e4677c9c3f747c83))

* fix: handle unknown recurring patterns

Amazon appears to have abandoned the `recurringPattern` field in favor
of `rRuleData`. The older recurrence is likely only found in legacy
reminders. Sensors will likely need to be reworked to handle.

closes #1490 ([`92bab7c`](https://github.com/custom-components/alexa_media_player/commit/92bab7c1ad73e9809cbab8de830aa7fb3d82bc55))

* fix: use non-deprecated async_get

closes #1604 ([`113b5e2`](https://github.com/custom-components/alexa_media_player/commit/113b5e274831687563659a8163b33e5d0bb39532))

* fix: ignore PUSH_MEDIA_PREFERENCE_CHANGE

closes #1599 ([`0dbcddf`](https://github.com/custom-components/alexa_media_player/commit/0dbcddfc3ed03b9c4874666d8b556e28f1102573))

### Style

* style: black ([`a6fcca0`](https://github.com/custom-components/alexa_media_player/commit/a6fcca0348cff703093fa1291ab4536db3818339))

### Unknown

* Merge pull request #1610 from custom-components/dev

2022-05-28 ([`35f5c73`](https://github.com/custom-components/alexa_media_player/commit/35f5c738741dada5bc0749c545c25bb35a86a05c))

* Merge pull request #1609 from alandtse/multi_fixes

Multi fixes ([`2b8dcf0`](https://github.com/custom-components/alexa_media_player/commit/2b8dcf0276583e8c60782a40f32d053bbb7dca79))


## v3.11.3 (2022-04-28)

### Documentation

* docs: update localization ([`5f2de48`](https://github.com/custom-components/alexa_media_player/commit/5f2de48b9f113f56cf0a41bcb970dbca944d6924))

### Fix

* fix: bump dependencies
Fixes HA beta dependency conflict

closes #1579 ([`beedc06`](https://github.com/custom-components/alexa_media_player/commit/beedc062eb67114762ce2b322e68748f6e896ee6))

### Unknown

* Merge pull request #1585 from custom-components/dev

2022-04-28 ([`9f7434a`](https://github.com/custom-components/alexa_media_player/commit/9f7434a7957c043b7f2690e5af6e5a8c01b6fe24))

* Merge pull request #1584 from alandtse/#1579

fix: bump dependencies ([`4226658`](https://github.com/custom-components/alexa_media_player/commit/4226658b1ed26a7e3a56ac247c2d7ddf66ab4d94))


## v3.11.2 (2022-04-17)

### Fix

* fix: reset cookies on proxy start (#1568)

Resets all cookies when loading the proxy. However, this removes the ability to start a login using the legacy method (including relogin attempts) and then resuming them with the proxy.

closes #1512

Co-authored-by: quthla &lt;quthla@users.noreply.github.com&gt; ([`7aef24b`](https://github.com/custom-components/alexa_media_player/commit/7aef24b4d5be75fa302d9e1e12aff2b85ce057e5))

* fix: reset cookies on proxy start

Resets all cookies when loading the proxy. However, this removes the ability to start a login using the legacy method (including relogin attempts) and then resuming them with the proxy.

closes #1512 ([`f064532`](https://github.com/custom-components/alexa_media_player/commit/f06453289189adb484a9b9a003489620b05abead))


## v3.11.1 (2022-04-05)

### Build

* build: add dev container (#1551) ([`2bdee55`](https://github.com/custom-components/alexa_media_player/commit/2bdee55927103c8795285d528bd817b4d535d0ab))

### Fix

* fix: use EntityCategory enum instead of strings (#1554)

closes #1553 ([`695839c`](https://github.com/custom-components/alexa_media_player/commit/695839cbbf0a8cc51400f736c8c3d20ec99bb35b))

* fix: use ConfigEntryNotReady during startup (#1557)

closes #1529 ([`2b14c3b`](https://github.com/custom-components/alexa_media_player/commit/2b14c3bf65c93cd39cf9992c912b29dcc8f28fb2))

### Unknown

* 2022-04-04 (#1558)

* build: add dev container (#1551)

* fix: use ConfigEntryNotReady during startup (#1557)

closes #1529

* fix: use EntityCategory enum instead of strings (#1554)

closes #1553

Co-authored-by: Simone Chemelli &lt;simone.chemelli@gmail.com&gt;
Co-authored-by: Mike Degatano &lt;michael.degatano@gmail.com&gt; ([`e0c9aba`](https://github.com/custom-components/alexa_media_player/commit/e0c9aba63d0e5d44e18febd64b06c4fb4a0cefcf))


## v3.11.0 (2022-03-16)

### Ci

* ci: switch to hassfest ([`a27ee46`](https://github.com/custom-components/alexa_media_player/commit/a27ee46b1f68628d39b80a5db41e2f7d377c165e))

### Documentation

* docs: update localization ([`a19d9e2`](https://github.com/custom-components/alexa_media_player/commit/a19d9e2996df9e71645ef36144f23723c17b5578))

### Feature

* feat: add entity_category to the AlexaMediaSwitches (#1537)

Co-authored-by: Robert Ansel &lt;ransel@slack-corp.com&gt; ([`3f42a45`](https://github.com/custom-components/alexa_media_player/commit/3f42a4577219c3ab76e50d8f956640376bdcd9d5))

### Unknown

* 2022-03-15 (#1540)

* ci: switch to hassfest

* feat: add entity_category to the AlexaMediaSwitches (#1537)

Co-authored-by: Robert Ansel &lt;ransel@slack-corp.com&gt;

Co-authored-by: mr-ransel &lt;robert.ansel@gmail.com&gt;
Co-authored-by: Robert Ansel &lt;ransel@slack-corp.com&gt; ([`ac548a4`](https://github.com/custom-components/alexa_media_player/commit/ac548a43f7758c34d72decc75eb5eaffc42b2e7b))


## v3.10.15 (2021-12-03)

### Fix

* fix: loosen allowed versions of dependencies

Reverts unintended change. ([`f083f80`](https://github.com/custom-components/alexa_media_player/commit/f083f80677e644fb937ae58e739c56f8ab23d900))

* fix: allow beta versions of 2021.12

closes #1446 ([`29e2032`](https://github.com/custom-components/alexa_media_player/commit/29e2032535296add0f77beef7bba3f5649da4645))

### Unknown

* Merge pull request #1448 from custom-components/dev

2021-12-03 ([`2b5a871`](https://github.com/custom-components/alexa_media_player/commit/2b5a871b7b5e6f115f2b111eb786bef3508e1993))

* Merge pull request #1447 from alandtse/#1446

#1446 ([`bc6695f`](https://github.com/custom-components/alexa_media_player/commit/bc6695fc57013c317bca1e88dd7b8805afa0c5ef))


## v3.10.14 (2021-11-23)

### Fix

* fix: require 2021.12.0

Due to changes in aiohttp dependency in HA and alexa_media, need to bump
the HA requirement.

closes #1434 ([`994a2fb`](https://github.com/custom-components/alexa_media_player/commit/994a2fbfab9203d2486007fdf177f68bf6d42971))

### Unknown

* Merge pull request #1437 from custom-components/dev

2021-11-23-b ([`e65a3e9`](https://github.com/custom-components/alexa_media_player/commit/e65a3e9d1f1abc5f32a93a9ea432a9fc65106e5d))

* Merge pull request #1436 from alandtse/#1434

fix: require 2021.12.0 ([`c2eab13`](https://github.com/custom-components/alexa_media_player/commit/c2eab13b703a2b05083a26ad5919e27672044eff))


## v3.10.13 (2021-11-23)

### Ci

* ci: restore requirements check ([`1b2b890`](https://github.com/custom-components/alexa_media_player/commit/1b2b890ae20141885128eb0adcc050736adb6e83))

### Fix

* fix: fix key error if entry exists ([`4f2a2b2`](https://github.com/custom-components/alexa_media_player/commit/4f2a2b2f328ec4855be1848c4889b1c513e99fd1))

* fix: bump deps

closes #1403
closes #1428 ([`f6fb70b`](https://github.com/custom-components/alexa_media_player/commit/f6fb70b467033c7f1da3f94c01655253d2c0dd56))

* fix: handle deprecation of device_state_attributes

Swap to extra_state_attributes ([`c224ee4`](https://github.com/custom-components/alexa_media_player/commit/c224ee4af0bff57efc89b6f8a9707b10ff548538))

### Unknown

* Merge pull request #1433 from custom-components/dev

2021-11-23 ([`7a6103b`](https://github.com/custom-components/alexa_media_player/commit/7a6103b0514ec9e109f4347b653f51bb7beecd41))

* Merge pull request #1432 from alandtse/#1403

#1403 ([`7862074`](https://github.com/custom-components/alexa_media_player/commit/78620745fe9fadbd893a1d16460ab8e37b6df85b))


## v3.10.12 (2021-11-19)

### Ci

* ci: ignore requirements

https://github.com/hacs/integration/issues/2298 ([`45f20e7`](https://github.com/custom-components/alexa_media_player/commit/45f20e7868df6d947ac124fe13a7f76bf1334111))

### Fix

* fix: fix conversion of aiohttp cookie to httpx

This fixes the case of switching from legacy to proxy login method.

closes #1418 ([`598175f`](https://github.com/custom-components/alexa_media_player/commit/598175f3e8297aea256a22417565df79638c1d8b))

* fix: set default `accounts` key in dictionary

Sets a default dictionary key even during reauth.
closes #1419 ([`ac4d3f9`](https://github.com/custom-components/alexa_media_player/commit/ac4d3f93db2249c16a02fe64d0b3a78e68cd039c))

### Unknown

* Merge pull request #1424 from custom-components/dev

2021-11-18 ([`a97709c`](https://github.com/custom-components/alexa_media_player/commit/a97709c97f463a4f526b261e95d424ef9493e959))

* Merge pull request #1423 from alandtse/#1418

fix: fix conversion of aiohttp cookie to httpx ([`c486420`](https://github.com/custom-components/alexa_media_player/commit/c486420bac7ca01b9e0009cc80497658b699f114))

* Merge pull request #1422 from alandtse/#1419

fix: set default `accounts` key in dictionary ([`f951369`](https://github.com/custom-components/alexa_media_player/commit/f95136985f44560a77dd079281ec0b23c48c91ca))


## v3.10.11 (2021-11-16)

### Fix

* fix: bump alexapy to 1.25.2
This replaces the websocket algorithm to use the latest A:F protocol.
closes #1409 ([`7de579d`](https://github.com/custom-components/alexa_media_player/commit/7de579d2fbd6fff7fb8a4196a5e79e8a65a31b44))

* fix: bump alexapy to 1.25.2
This replaces the websocket algorithm to use hte latest A:F protocol.
closes #1409 ([`f41c8fe`](https://github.com/custom-components/alexa_media_player/commit/f41c8fe9a94150cd37311aaff845ad5511cdf881))

### Unknown

* Merge pull request #1416 from custom-components/dev

2021-11-15 ([`0e5f79a`](https://github.com/custom-components/alexa_media_player/commit/0e5f79aaa31688beb5f7f10bd0683ae554c12350))

* Merge pull request #1415 from alandtse/#1409

#1409 ([`8d1eaca`](https://github.com/custom-components/alexa_media_player/commit/8d1eaca1d760bace946bd16bbe0daac71d259bfe))

* Merge branch &#39;#1409&#39; of https://github.com/alandtse/alexa_media_player into #1409 ([`4cd3c0d`](https://github.com/custom-components/alexa_media_player/commit/4cd3c0d587891122f905e51d457c2895b07c90e0))


## v3.10.10 (2021-10-13)

### Unknown

* 2021-10-12 (#1383)

* ci: remove non-recommended it checkout

* build(deps): allow newer versions of packaging

* Home Assistant 2021.8.x uses packaging~=21.0 now.

* fix: fix issue where next_alarm would cancel on reload (#1379)

Where multiple instances of the component are in use, the &#34;dev_id&#34; is made up
from a combination of the serial number &amp; account email address.

This was being used when trying to load out the notifications from the
async_update call. The key that should have been used is only the serial
number of the device. This commit changes to using the serial.

Co-authored-by: Chris Edester &lt;edestecd@miamioh.edu&gt;
Co-authored-by: David Hutchison &lt;dhutchison86+wp@gmail.com&gt; ([`05001b3`](https://github.com/custom-components/alexa_media_player/commit/05001b380aa01f856e83680634454885f56b7418))


## v3.10.9 (2021-10-13)

### Build

* build(deps): allow newer versions of packaging

* Home Assistant 2021.8.x uses packaging~=21.0 now. ([`f45a8e2`](https://github.com/custom-components/alexa_media_player/commit/f45a8e2efb23225c6865e50f55518191537b8349))

### Ci

* ci: remove non-recommended it checkout ([`30b6108`](https://github.com/custom-components/alexa_media_player/commit/30b6108215c16568f7f0cb1bf9467672ff576dbf))

### Documentation

* docs: update localization ([`a30af11`](https://github.com/custom-components/alexa_media_player/commit/a30af11fa5a8cd6848401023597b4be96d6c1104))

### Fix

* fix: fix icon on do not disturb switch (#1377)

Update to new MDI entry for do not disturb switch per Home Assistant update 2021.10.0. ([`5407be3`](https://github.com/custom-components/alexa_media_player/commit/5407be36fd4e34782224212af5659a63d9dc306a))

* fix: fix issue where next_alarm would cancel on reload (#1379)

Where multiple instances of the component are in use, the &#34;dev_id&#34; is made up
from a combination of the serial number &amp; account email address.

This was being used when trying to load out the notifications from the
async_update call. The key that should have been used is only the serial
number of the device. This commit changes to using the serial. ([`a5dd83a`](https://github.com/custom-components/alexa_media_player/commit/a5dd83a3ab1a7bec565e470e11d28d3d5076b695))


## v3.10.8 (2021-08-03)

### Ci

* ci: fix help wanted tag ([`6ed9d4b`](https://github.com/custom-components/alexa_media_player/commit/6ed9d4b8a7f4d9a57aa1d111527299ccf00c8322))

### Documentation

* docs: update localization ([`d1ece99`](https://github.com/custom-components/alexa_media_player/commit/d1ece992d5fdf8e5c7934d0db7c5f21a05707ea8))

### Fix

* fix: fix color mapping during color conversion (#1345)

Use a hard-coded list of Alexa colors and force brightness to 100 during color conversion

closes #1341 ([`c296aef`](https://github.com/custom-components/alexa_media_player/commit/c296aefed824f0ba8acde166a4a43bf29c6f9cd8))

* fix: parse timezone from timestamp
This relies on pulling the timestamp from the string instead of defaulting to UTC
closes #1350 ([`c7dc5f2`](https://github.com/custom-components/alexa_media_player/commit/c7dc5f27082e253903fd596d86947dcfd7c80cc5))

### Unknown

* 2021-08-02 (#1352)

* fix: parse timezone from timestamp
This relies on pulling the timestamp from the string instead of defaulting to UTC
closes #1350

* fix: fix color mapping during color conversion (#1345)

Use a hard-coded list of Alexa colors and force brightness to 100 during color conversion

closes #1341

Co-authored-by: Brady Mulhollem &lt;blm126@gmail.com&gt; ([`77395b9`](https://github.com/custom-components/alexa_media_player/commit/77395b93ae5ec302f03a6f6a8444d0b59c0460c8))

* Merge pull request #1351 from alandtse/#1350

fix: parse timezone from timestamp ([`5d31811`](https://github.com/custom-components/alexa_media_player/commit/5d31811ae6caef7e8b5524db1f98057f128d6324))

* Merge pull request #1343 from custom-components/dev

ci: fix help wanted tag ([`684205a`](https://github.com/custom-components/alexa_media_player/commit/684205a97dbc3d88a78cc881da30331f6db7c9d2))


## v3.10.7 (2021-07-15)

### Fix

* fix: fix comparison between offset-naive and offset-aware datetimes (#1338) (#1339)

closes #1334

Co-authored-by: Chris &lt;chris@spoon.nz&gt; ([`bcc996a`](https://github.com/custom-components/alexa_media_player/commit/bcc996a6088a0c2826d828cdb114f36abcf69ee9))

* fix: fix comparison between offset-naive and offset-aware datetimes (#1338)

closes #1334 ([`0ccdb18`](https://github.com/custom-components/alexa_media_player/commit/0ccdb181c52f61f221eb50aad0fc2ad97b71b59f))


## v3.10.6 (2021-06-16)

### Documentation

* docs: update localization ([`9e8f7d9`](https://github.com/custom-components/alexa_media_player/commit/9e8f7d90084c88473e3449be11971d694e6953d6))

### Fix

* fix: use timezone aware datetime for timers
closes #1317 ([`de4a962`](https://github.com/custom-components/alexa_media_player/commit/de4a96230828e7226fb6c58461f983210892ca10))

* fix: handle unknown recurrence patterns
close #1321 ([`a7a173c`](https://github.com/custom-components/alexa_media_player/commit/a7a173c4f82500eeb0a3525990777665920790ad))

### Unknown

* Merge pull request #1325 from custom-components/dev

2021-06-15 ([`c49acee`](https://github.com/custom-components/alexa_media_player/commit/c49acee988a5b590f4495ca3708ee9dc25635a64))

* Merge pull request #1324 from alandtse/#1317

#1317 ([`b8106af`](https://github.com/custom-components/alexa_media_player/commit/b8106af7350d1edebdd02e5915f0e219c824b5fe))


## v3.10.5 (2021-05-18)

### Documentation

* docs: update localization ([`d368377`](https://github.com/custom-components/alexa_media_player/commit/d3683774e07e10c9416f189b8f7d654e33957b5b))

### Fix

* fix: avoid pruning devices in secondary accounts
closes #1300 ([`a62a371`](https://github.com/custom-components/alexa_media_player/commit/a62a3710aee48e2ddb0ab72ca491384b1d95e597))

### Unknown

* Merge pull request #1305 from custom-components/dev

2021-05-17 ([`4aae42f`](https://github.com/custom-components/alexa_media_player/commit/4aae42f42059048c258b2875b5cccaab65016a7a))

* Merge pull request #1304 from alandtse/#1300

fix: avoid pruning devices in secondary accounts ([`78698b9`](https://github.com/custom-components/alexa_media_player/commit/78698b9dc8280d4a697c99dfcc896933400c9b72))


## v3.10.4 (2021-05-15)

### Documentation

* docs: update localization ([`e148ae4`](https://github.com/custom-components/alexa_media_player/commit/e148ae40219a0610a6e401dd97e81aaec75ba531))

* docs: update localization ([`fb952ca`](https://github.com/custom-components/alexa_media_player/commit/fb952cadc34a47aaf4dba1d2760cf4d0ee5a54e4))

### Fix

* fix: handle case where alexa guard is disabled (#1297)

This also changes the entity parsing code to be extremely defensive so that this function won&#39;t break startup no matter what Amazon returns.
Fixes #1296 ([`6295e93`](https://github.com/custom-components/alexa_media_player/commit/6295e93a0761da1365f761a56e2d29d125998f9a))

### Unknown

* 2021-05-15 (#1298)

* docs: update localization

* fix: handle case where alexa guard is disabled (#1297)

This also changes the entity parsing code to be extremely defensive so that this function won&#39;t break startup no matter what Amazon returns.
Fixes #1296

Co-authored-by: semantic-release &lt;semantic-release@GitHub&gt;
Co-authored-by: Brady Mulhollem &lt;blm126@gmail.com&gt; ([`daa308c`](https://github.com/custom-components/alexa_media_player/commit/daa308cda2e372794a974585f31d4929d667772c))


## v3.10.3 (2021-05-15)

### Fix

* fix: update entity state after network discovery (#1291) (#1295)

Previously, each platform forced a refresh on the coordinator. This was slow and error prone. Now, when the network is discovered full entity state is discovered as well.
Fixes #1289

Co-authored-by: Brady Mulhollem &lt;blm126@gmail.com&gt; ([`b2302ec`](https://github.com/custom-components/alexa_media_player/commit/b2302ec16da19657bc1dfd7c6cd0b4343c7404db))

* fix: update entity state after network discovery (#1291)

Previously, each platform forced a refresh on the coordinator. This was slow and error prone. Now, when the network is discovered full entity state is discovered as well.
Fixes #1289 ([`9804dd3`](https://github.com/custom-components/alexa_media_player/commit/9804dd35188befb7e1053369f7a6fa6befa1e860))


## v3.10.2 (2021-05-13)

### Ci

* ci: set translation commit as optional ([`8487641`](https://github.com/custom-components/alexa_media_player/commit/8487641519295b895f8e015c40bc7c5d13d8f78b))

### Documentation

* docs: update localization ([`74ec44b`](https://github.com/custom-components/alexa_media_player/commit/74ec44b00334e91678541c2c2b096ea022294e86))

### Fix

* fix: prune devices removed from amazon
Devices that are no longer reported by Amazon are now removed from HA
automatically.
closes #1281 ([`f75f8b9`](https://github.com/custom-components/alexa_media_player/commit/f75f8b92253e256f727f1f75c6516460a7774327))

### Style

* style: black ([`b3f9d6a`](https://github.com/custom-components/alexa_media_player/commit/b3f9d6a97f858013878760dbd9e081d51d61a733))

### Unknown

* Merge pull request #1286 from custom-components/dev

2021-05-12 ([`41d1014`](https://github.com/custom-components/alexa_media_player/commit/41d1014ecb2f4836ee6635616c83995a2b1f14d7))

* Merge pull request #1285 from alandtse/#1281

#1281 ([`a859784`](https://github.com/custom-components/alexa_media_player/commit/a859784f14179571742b2f1443ac9cd7595a8566))


## v3.10.1 (2021-05-08)

### Ci

* ci: auto add translations ([`e93587d`](https://github.com/custom-components/alexa_media_player/commit/e93587d4f99df40738fc3b5e75a74fedf4a3642f))

### Documentation

* docs: update localization ([`7041760`](https://github.com/custom-components/alexa_media_player/commit/7041760701a3d9acb3b35f82a3cb84b1c9fc7f99))

### Fix

* fix: improve checking for skill backed appliances #1277 ([`ea04bae`](https://github.com/custom-components/alexa_media_player/commit/ea04bae4968df557fd6e8fab6b0745bae04b807c))

### Unknown

* 2021-05-07 (#1278)

* ci: auto add translations

* fix: improve checking for skill backed appliances #1277

Co-authored-by: Brady Mulhollem &lt;blm126@gmail.com&gt; ([`6ad8680`](https://github.com/custom-components/alexa_media_player/commit/6ad8680c2f319d50680b216ae35eeedf3f3badc4))

* Merge pull request #1274 from alandtse/translation_ci

ci: auto add translations ([`07f9f64`](https://github.com/custom-components/alexa_media_player/commit/07f9f64fdbe7ad3344c3a0c4cb7b178130ed8137))


## v3.10.0 (2021-05-04)

### Build

* build: rename pt-br to json ([`56111a0`](https://github.com/custom-components/alexa_media_player/commit/56111a0abcfd4ccaf1d185c4753687df95704aa5))

### Ci

* ci: add token to checkout action ([`b6ad7b8`](https://github.com/custom-components/alexa_media_player/commit/b6ad7b83fc78b5d2103bbc9f6d33ee35644a6e45))

* ci: swap to semantic release action ([`b756cc7`](https://github.com/custom-components/alexa_media_player/commit/b756cc7fc5560061c28b6f1ec7acf08e66872a5f))

### Documentation

* docs: update localization ([`9394e97`](https://github.com/custom-components/alexa_media_player/commit/9394e9750075e4f5c665030dd4f86074bc085cbb))

### Feature

* feat: improve lights controls and support colors (#1270)

* Make lights controls more responsive and support colors.

* Support versions of HA older than 2021.4. ([`fe48034`](https://github.com/custom-components/alexa_media_player/commit/fe480342498556cbf1e42ed965c69993940aea7d))

* feat: add &#34;alexa_media_alarm_dismissal_event&#34; &#34;status&#34;/&#34;dismissed&#34; events to alarms. (#1271) ([`32e802f`](https://github.com/custom-components/alexa_media_player/commit/32e802f0552f4f05f039b8a3c11555e9a2dcd227))

* feat: add PT-BR localization (#1266)

brazilian portuguese localization ([`6a365ad`](https://github.com/custom-components/alexa_media_player/commit/6a365adaa69c3a00297164c3c8dfc79161ea67e4))

### Fix

* fix: fix tesla_custom compatibility

Users of tesla_custom required a newer version of authcaptureproxy.
AMP is now compatible with tesla_custom. ([`dada99f`](https://github.com/custom-components/alexa_media_player/commit/dada99f83461c0b189ff098a9b2e010d772f4867))

* fix: add iot_class to manifest.json
This is a new requirement in HA revealed by hassfest. ([`b7a3688`](https://github.com/custom-components/alexa_media_player/commit/b7a36887a0e25849c2b2f3824abd8b86344d9b77))

### Unknown

* Merge pull request #1273 from custom-components/dev

2021-05-03 ([`107a85e`](https://github.com/custom-components/alexa_media_player/commit/107a85efb51fe152ae4906ad64436895399275d9))

* Merge pull request #1268 from alandtse/hassfest

fix: fix tesla_custom compatibility ([`80a6d56`](https://github.com/custom-components/alexa_media_player/commit/80a6d56f5f9613d115b9b084f8ded7e6c8212592))

* Merge pull request #1267 from alandtse/hassfest

fix: add iot_class to manifest.json ([`c84633c`](https://github.com/custom-components/alexa_media_player/commit/c84633c7246f2991e9ce0f85a419b5a11bc14265))


## v3.9.0 (2021-04-24)

### Feature

* feat: add lights and the temperature sensors (#1244)

Closes #1237 and #1202. Since this is based on polling it is disabled by default and is enabled in options. Please check the instructions on the wiki.
https://github.com/custom-components/alexa_media_player/wiki#discover-and-control-devices-connected-to-an-echo ([`26b4b51`](https://github.com/custom-components/alexa_media_player/commit/26b4b51b26899636b2b3ae8ac2f58b1fc2e6b433))

### Fix

* fix: detect and ignore lights created by emulated_hue (#1253)

* Detect and ignore lights created by emulated_hue plus some general cleanup.

* Adjust naming and comments to be more accurate. ([`4cef90e`](https://github.com/custom-components/alexa_media_player/commit/4cef90ef73c1adcdf8e870654abc25cb2e0326e0))

* fix: auto reload when extended entity discovery is enabled (#1254)

* Automatically reload the integration when extended entity discovery is enabled.

* fix: reload only after all values processed

Co-authored-by: Alan Tse &lt;alandtse@users.noreply.github.com&gt; ([`8a8f8ee`](https://github.com/custom-components/alexa_media_player/commit/8a8f8ee0e54fd4d09e3f7fc4ab2e114bbee9e2f0))

* fix: TypeError: _typeddict_new() missing typename ([`b89852d`](https://github.com/custom-components/alexa_media_player/commit/b89852d2e50bb9c04dc5d7a70721c7073f647b3b))

* fix: check for existence of properties key
closes #1249 ([`211015f`](https://github.com/custom-components/alexa_media_player/commit/211015fc16731ac496f0b4365499cf2b77928c22))

### Style

* style: fix lint errors ([`e944c61`](https://github.com/custom-components/alexa_media_player/commit/e944c612e3ee031438dd49ac853ba84a1e41514d))

### Unknown

* 2021-04-23 (#1261)

* feat: add lights and the temperature sensors (#1244)

Closes #1237 and #1202. Since this is based on polling it is disabled by default and is enabled in options. Please check the instructions on the wiki.
https://github.com/custom-components/alexa_media_player/wiki#discover-and-control-devices-connected-to-an-echo

* fix: check for existence of properties key
closes #1249

* fix: TypeError: _typeddict_new() missing typename

* style: fix lint errors

* fix: auto reload when extended entity discovery is enabled (#1254)

* Automatically reload the integration when extended entity discovery is enabled.

* fix: reload only after all values processed

Co-authored-by: Alan Tse &lt;alandtse@users.noreply.github.com&gt;

* fix: detect and ignore lights created by emulated_hue (#1253)

* Detect and ignore lights created by emulated_hue plus some general cleanup.

* Adjust naming and comments to be more accurate.

Co-authored-by: Brady Mulhollem &lt;blm126@gmail.com&gt; ([`faa4fde`](https://github.com/custom-components/alexa_media_player/commit/faa4fdebfc32286db0ff5d47a94bd72b016fc025))

* Merge pull request #1252 from alandtse/#1249

#1249 ([`0920a7d`](https://github.com/custom-components/alexa_media_player/commit/0920a7da337a1cd4d38133708366ce09af452ee6))

* Merge pull request #1250 from alandtse/#1249

fix: check for existence of properties key ([`cb34b7d`](https://github.com/custom-components/alexa_media_player/commit/cb34b7dc157bc606e41132026ab6771ae447b37f))


## v3.8.6 (2021-04-12)

### Build

* build(deps): bump dependencies ([`dc11397`](https://github.com/custom-components/alexa_media_player/commit/dc113978918b65629afb019501ed498d59a4c3f5))

### Fix

* fix: check for hass existence and fallback call
The use of async_create_task requires entity has been added to hass. If this
has not occured use the old direct call.
closes #1221 ([`f2d8362`](https://github.com/custom-components/alexa_media_player/commit/f2d83625dd90c8d431ce0169714275c6d2cee836))

### Unknown

* Merge pull request #1243 from custom-components/dev

2021-04-11 ([`191b915`](https://github.com/custom-components/alexa_media_player/commit/191b9157337add122a4990c94660a382f6784a8b))

* Merge pull request #1242 from alandtse/#1221

build(deps): bump dependencies ([`a946166`](https://github.com/custom-components/alexa_media_player/commit/a94616621e4da1bb5ce188bdc8071b75d16a924c))

* Merge pull request #1239 from alandtse/#1221

fix: check for hass existence and fallback call ([`4b17cc5`](https://github.com/custom-components/alexa_media_player/commit/4b17cc5c82ffb8b6e96e99b45d1821fc3b4a190c))


## v3.8.5 (2021-03-17)

### Fix

* fix: fix case where proxy receives ip address only
closes #1203 ([`2c423a4`](https://github.com/custom-components/alexa_media_player/commit/2c423a4d8752450fe95d7893b86a3207b962944e))

* fix: use ha converter for local time
closes #1217 ([`6c03b9c`](https://github.com/custom-components/alexa_media_player/commit/6c03b9c0ee13a813d99422f2fc800513155d88f5))

### Unknown

* Merge pull request #1220 from custom-components/dev

2021-03-16 ([`2f99253`](https://github.com/custom-components/alexa_media_player/commit/2f99253fd743abf2afaa0f0e16760915cd861a31))

* Merge pull request #1219 from alandtse/#1203

fix: fix case where proxy receives ip address only ([`d92d735`](https://github.com/custom-components/alexa_media_player/commit/d92d7357fc93da6f6548b5043b97e936770466c6))

* Merge pull request #1218 from alandtse/#1217

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`f513343`](https://github.com/custom-components/alexa_media_player/commit/f51334375435fee3de339b33ff872f0c01d0960b))


## v3.8.4 (2021-03-12)

### Fix

* fix: handle non-json domainAttributes in activities
Uncaught exception was incorrectly detecting a forced logout
closes #1207 ([`05025cf`](https://github.com/custom-components/alexa_media_player/commit/05025cf2ab23a33eed1f0a4f47ab2a4a9c50b323))

* fix: handle case when hass has no detectable url
closes #1208 ([`3796a85`](https://github.com/custom-components/alexa_media_player/commit/3796a857fe9841b345f4c24a3e38f2a7086a777a))

### Unknown

* Merge pull request #1211 from custom-components/dev

2021-03-12 ([`8e46201`](https://github.com/custom-components/alexa_media_player/commit/8e46201fe205398fa41a33e13741729bf803a422))

* Merge pull request #1210 from alandtse/#1207

fix: handle non-json domainAttributes in activities ([`0bcb191`](https://github.com/custom-components/alexa_media_player/commit/0bcb191befc9563bce52194b6f7be66f03ba1ed3))

* Merge pull request #1209 from alandtse/#1208

fix: handle case when hass has no detectable url ([`bcd679f`](https://github.com/custom-components/alexa_media_player/commit/bcd679f0a2eb774255667d78ee0f202711c026d8))


## v3.8.3 (2021-03-11)

### Build

* build(deps): bump alexapy to 1.24.3 ([`4b4da1e`](https://github.com/custom-components/alexa_media_player/commit/4b4da1ee57881c1574259832f82f5e8787582e62))

### Fix

* fix: ignore typerrors for update_last_called
Activites page may return {&#34;message&#34;:&#34;Rate exceeded&#34;} with a http 200
message.
closes #1196 ([`c2c57ed`](https://github.com/custom-components/alexa_media_player/commit/c2c57eda15b6d090d129ee0bb7c5c640787bd71e))

### Unknown

* Merge pull request #1205 from custom-components/dev

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`6b243ad`](https://github.com/custom-components/alexa_media_player/commit/6b243ad0db8d3ca8e11367f298e3a8aa8e3fcef9))

* Merge pull request #1197 from alandtse/#1196

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`94b2565`](https://github.com/custom-components/alexa_media_player/commit/94b25657142de3b55692b11c0c84446803222a53))


## v3.8.2 (2021-02-20)

### Build

* build: add yamllint ([`aeea945`](https://github.com/custom-components/alexa_media_player/commit/aeea9450a16b061721aa2a8224e913e858c750b4))

### Ci

* ci: update stale to include help-wanted ([`149d43e`](https://github.com/custom-components/alexa_media_player/commit/149d43e6b46e03c668871a309f9b58fb674e3863))

### Fix

* fix: bump alexapy==1.24.2
Include support for blank action attributes in forms
closes #1187
closes #1182 ([`9489268`](https://github.com/custom-components/alexa_media_player/commit/9489268a3dd469df5767a263e9d6f61644ac62d2))

* fix: ignore PUSH_LIST_CHANGE
closes #1190 ([`d1737fe`](https://github.com/custom-components/alexa_media_player/commit/d1737fee541c8642967486420fc9643b660d5f56))

### Style

* style: move license header into docstring ([`bc7dda7`](https://github.com/custom-components/alexa_media_player/commit/bc7dda72c38eeae117cad1e68e35cc8bfbe500cb))

### Unknown

* Merge pull request #1193 from custom-components/dev

2021-02-19 ([`ac65cc4`](https://github.com/custom-components/alexa_media_player/commit/ac65cc4dce63033098207adf41035fa4c517b650))

* Merge pull request #1192 from alandtse/fix_ci

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`41d309b`](https://github.com/custom-components/alexa_media_player/commit/41d309b0c4a2eabbde0f2033f4c73c4eac7d4ead))

* Merge pull request #1186 from alandtse/fix_ci

Fix ci ([`03d5bb6`](https://github.com/custom-components/alexa_media_player/commit/03d5bb604155cb6b8b15261052e50167604406c1))


## v3.8.1 (2021-02-15)

### Build

* build(deps): update alexapy to 1.24.1
closes #1182 ([`2815bc6`](https://github.com/custom-components/alexa_media_player/commit/2815bc62998994992c56bb01951f698c6c21a55c))

* build: use poetry to manage environment ([`0f8b7fd`](https://github.com/custom-components/alexa_media_player/commit/0f8b7fd58dbf92664638186f9c30ae47365c22ca))

* build: do not scan .lock for spellng ([`2f61d42`](https://github.com/custom-components/alexa_media_player/commit/2f61d420ada1d52cf0767f8bbd449e38f8dde0b8))

### Ci

* ci: fix semantic release process ([`ac4435d`](https://github.com/custom-components/alexa_media_player/commit/ac4435d3d11aff3569ce3c26361e2066b7f4ee91))

* ci: add commit of translations and push to dev ([`5cd45d4`](https://github.com/custom-components/alexa_media_player/commit/5cd45d4c4cc873e5831b58def7dacd41155eb037))

### Documentation

* docs: update badges ([`2081e0f`](https://github.com/custom-components/alexa_media_player/commit/2081e0f9075aa9706f5fab7fe0494382e7c4337c))

### Fix

* fix: use external hass url as default for proxy ([`aa8df7e`](https://github.com/custom-components/alexa_media_player/commit/aa8df7e94db696977eec8dc0c85c0dabea18df74))

* fix: wrap calls to alexapi in async_create_task

This allows all function calls to return despite the queue_delay in alexaapi. This will allow successive calls in the same HA script to trigger the queue building functionality.
closes #1118 ([`0445b72`](https://github.com/custom-components/alexa_media_player/commit/0445b7227b2994b9e6dcf2bbc1b95fc203e569c2))

### Style

* style: lint and black ([`9e3a7c7`](https://github.com/custom-components/alexa_media_player/commit/9e3a7c7b875be9283b17da0d70f6d7cd0e61e5f4))

### Unknown

* Merge pull request #1185 from alandtse/fix_ci

ci: fix semantic release process ([`9a06d77`](https://github.com/custom-components/alexa_media_player/commit/9a06d777236c358d56bd85032e384101a3fdcaed))

* Merge pull request #1184 from custom-components/dev

2021-02-14 ([`5226e59`](https://github.com/custom-components/alexa_media_player/commit/5226e59e3dce1cfdfd19bab98e6d4516516480ed))

* Merge pull request #1183 from alandtse/authcaptureproxy

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`b364d70`](https://github.com/custom-components/alexa_media_player/commit/b364d7057b1853be2a0f19a203e5719c071f52ce))

* Merge pull request #1175 from alandtse/authcaptureproxy

docs: update badges ([`b924af0`](https://github.com/custom-components/alexa_media_player/commit/b924af02fac97175671e8369bc582c7a044ce4d4))

* Merge pull request #1174 from custom-components/master

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`2fc0134`](https://github.com/custom-components/alexa_media_player/commit/2fc0134d0cc27be203cfad9290b2eddfcbdbbdc6))


## v3.8.0 (2021-02-08)

### Feature

* feat: add name and entity_id to notification_event
closes #1137 ([`9c6f6f8`](https://github.com/custom-components/alexa_media_player/commit/9c6f6f875c769524ba3f7b7a34f414029acc11b7))

### Fix

* fix: fix https proxy login ([`f873721`](https://github.com/custom-components/alexa_media_player/commit/f873721f2df741240f0a2120ecd432e2ee762edd))

### Refactor

* refactor: remove unused lock ([`3ba2b6f`](https://github.com/custom-components/alexa_media_player/commit/3ba2b6ffac6df782305a27f1db578b3f61622d86))

### Unknown

* Merge pull request #1173 from custom-components/dev

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`452fff4`](https://github.com/custom-components/alexa_media_player/commit/452fff4d9e4ad2ff57ca5074dfc57480e2ba81fa))

* Merge pull request #1172 from alandtse/authcaptureproxy

Authcaptureproxy ([`3d34f55`](https://github.com/custom-components/alexa_media_player/commit/3d34f553569776767245dcb5c73512489ce96a5c))

* Merge pull request #1171 from alandtse/#1137

#1137 ([`1df6087`](https://github.com/custom-components/alexa_media_player/commit/1df608785e006a48384d589fb64941749580ee49))

* Merge pull request #1170 from custom-components/master

Master ([`83b4901`](https://github.com/custom-components/alexa_media_player/commit/83b49019899807fc2aa32b1ca833562443bb4a34))


## v3.7.0 (2021-02-07)

### Feature

* feat: use HA view for proxy address
This should allow https or using the external url.
closes #1167 ([`3eb09ea`](https://github.com/custom-components/alexa_media_player/commit/3eb09ea0834f36178c8fd11423c0202760d96c02))

### Unknown

* Merge pull request #1169 from custom-components/dev

2021-01-06 ([`fd6c6f2`](https://github.com/custom-components/alexa_media_player/commit/fd6c6f22e6a8f66fe3508ebc62c780909724810b))

* Merge pull request #1168 from alandtse/authcaptureproxy

feat: use HA view for proxy address ([`70bf808`](https://github.com/custom-components/alexa_media_player/commit/70bf8083467c52f20f1c4305ca195e1f923b5a02))

* Merge pull request #1164 from custom-components/master

Master ([`65afa57`](https://github.com/custom-components/alexa_media_player/commit/65afa57652335ca43cdc838558fc492e8515fc15))


## v3.6.4 (2021-02-03)

### Fix

* fix: update last_update before notify update
closes #1159 ([`77223a9`](https://github.com/custom-components/alexa_media_player/commit/77223a9b6f89cfa3bc9a4102151181c6a7b22f4d))

* fix: add version to manifest.json ([`faef7a1`](https://github.com/custom-components/alexa_media_player/commit/faef7a1bedfc5cec2f1415294afdf7f9276851bd))

### Unknown

* Merge pull request #1163 from custom-components/dev

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`c6eedc8`](https://github.com/custom-components/alexa_media_player/commit/c6eedc82bf28fe3ebb5b80941e4dba8f676f8c81))

* Merge pull request #1162 from alandtse/#1159

fix: update last_update before notify update ([`8a8cdbb`](https://github.com/custom-components/alexa_media_player/commit/8a8cdbb7496bbddd0d9ebe4d9b791edd091c9ac0))

* Merge pull request #1158 from alandtse/manifest_version

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`17d45a5`](https://github.com/custom-components/alexa_media_player/commit/17d45a52847ba56af00fa84a04d3927211b0513b))

* Merge pull request #1153 from custom-components/master

Master ([`fd21842`](https://github.com/custom-components/alexa_media_player/commit/fd218425ce05291a538fea26def5f47e7cfe140f))


## v3.6.3 (2021-01-28)

### Fix

* fix: bump to alexapy 1.22.3
Fix to use latest automations url
closes #1149 ([`c3df546`](https://github.com/custom-components/alexa_media_player/commit/c3df54653318f8416ec66d7d56d421df3e3e2b2d))

* fix: cancel proxy after 10 minutes
If a user cancels setup through the UI, it is possible the proxy will remain
active until HA restart. This will now force the proxy to close after
10 minutes. ([`d818f48`](https://github.com/custom-components/alexa_media_player/commit/d818f481981f63dcb620e1c554cf2fb4a65e8d87))

* fix: check for valid ha url
The server will now try to connect to the provided HA url. This will
catch basic errors related to the wrong ip addres or port or the use of
https. It will not catch firewall issue which are not detectable from
the server. ([`1b21b4a`](https://github.com/custom-components/alexa_media_player/commit/1b21b4a92888304c7f750a560f1d2a953c6509d5))

* fix: add otp confirmation step for proxy ([`c82d3f1`](https://github.com/custom-components/alexa_media_player/commit/c82d3f1d87e854ff6402af327a9c2624692672c1))

* fix: provide warning for invalid built-in 2fa key
Check for exception AlexapyPyotpInvalidKey for proxy method.
closes #1146 ([`af86368`](https://github.com/custom-components/alexa_media_player/commit/af863689f53993939296faeacd06516f5cd8bd04))

### Refactor

* refactor: move translation directory ([`cd2a39a`](https://github.com/custom-components/alexa_media_player/commit/cd2a39a16223b69dc1afcef830aa005d190fc2d7))

### Unknown

* Merge pull request #1152 from custom-components/dev

2021-01-28 ([`3af7644`](https://github.com/custom-components/alexa_media_player/commit/3af7644fd75041e85f897be0b7d63b49a76a4031))

* Merge pull request #1151 from alandtse/#1149

fix: bump to alexapy 1.22.3 ([`2a02c73`](https://github.com/custom-components/alexa_media_player/commit/2a02c7387aed8abad5dfde539e7386056fe0cd1a))

* Merge pull request #1150 from alandtse/check_ha_url

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`70eee72`](https://github.com/custom-components/alexa_media_player/commit/70eee72e7a119619777184c9556e8110ab25d631))

* Merge pull request #1148 from alandtse/check_ha_url

fix: check for valid ha url ([`5d2752f`](https://github.com/custom-components/alexa_media_player/commit/5d2752f092d7f56299691b6c89a668e5b6b05b96))

* Merge pull request #1147 from alandtse/#1146

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`d3e803a`](https://github.com/custom-components/alexa_media_player/commit/d3e803adf29519b99506a38b716ff168d2da31e9))

* Merge pull request #1142 from alandtse/translations_move

refactor: move translation directory ([`f0f5615`](https://github.com/custom-components/alexa_media_player/commit/f0f56159f7a79a290603078c06f06d63a556c8cc))

* Merge pull request #1140 from custom-components/master

Master ([`12e84cf`](https://github.com/custom-components/alexa_media_player/commit/12e84cf5f23827f431a27c91617e77b7bc3ed834))


## v3.6.2 (2021-01-24)

### Fix

* fix: add delay on consecutive service updates
Apparently register_service spawns threads to update the service list.
This can result in situations where services cannot fully unload in time
before the next call. ([`7ec02a8`](https://github.com/custom-components/alexa_media_player/commit/7ec02a8761bf5361eaef70a347acdacac62119d7))

* fix: fix missing target devices
Fix bug where the last_called media player would exit the target
loop early. This would result in missing devices.
closes #1138 ([`a2fff11`](https://github.com/custom-components/alexa_media_player/commit/a2fff116448427fe8074899fff28f15364448b9a))

### Unknown

* Merge pull request #1139 from alandtse/#1138

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`510c4d1`](https://github.com/custom-components/alexa_media_player/commit/510c4d1273b45ce64e21451be706ed52678c55a5))

* Add device information to notification event

Currently it is difficult to understand which device triggered a notification event. This adds the device name which triggered the event ([`785ad71`](https://github.com/custom-components/alexa_media_player/commit/785ad712797be8b960b9df176d3713c08ba17029))

* Merge pull request #1136 from custom-components/master

Master ([`3c80187`](https://github.com/custom-components/alexa_media_player/commit/3c8018749fc871d491533769566555d2d2cade07))


## v3.6.1 (2021-01-24)

### Fix

* fix: fix announce for second account
closes #1116
closes #1133 ([`14c9a12`](https://github.com/custom-components/alexa_media_player/commit/14c9a1263a90f2ed73e8dd284e6b10150ffda533))

### Unknown

* Merge pull request #1135 from alandtse/#1116

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`5833ed3`](https://github.com/custom-components/alexa_media_player/commit/5833ed3e8d6d7971c24fbc6fa6f903771ef68fb6))

* Merge pull request #1134 from custom-components/master

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`333a8f1`](https://github.com/custom-components/alexa_media_player/commit/333a8f145deac4c53017f868ecfcc361aa9c3c6d))


## v3.6.0 (2021-01-24)

### Feature

* feat: add last_called notify service target
This requires HA to allow dynamic targets.
closes #1104 ([`d3e35c2`](https://github.com/custom-components/alexa_media_player/commit/d3e35c24d2a6fd017ba1b53d3f7ce468f67c5f6c))

### Fix

* fix: fix deregistration for duplicate HA uuids
This would occur if more than one HA instance shared a uuid. This is a rare
occurence and would happen if you copied the complete config between
servers. However, this means the registered device name will change.
You can safely remove the older ones.
closes #1130 ([`556d771`](https://github.com/custom-components/alexa_media_player/commit/556d77109d451e81aefba961bd1a8ac31be132de))

* fix: update last_called only if changed ([`545783a`](https://github.com/custom-components/alexa_media_player/commit/545783a42e88e54479587ff22bccac3b439f879b))

### Unknown

* Merge pull request #1132 from custom-components/dev

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`402c1e1`](https://github.com/custom-components/alexa_media_player/commit/402c1e143adbb5bbd5d53d0a2cdc234a7d6035cb))

* Merge pull request #1131 from alandtse/#1130

fix: fix deregistration for duplicate HA uuids ([`0cc83a6`](https://github.com/custom-components/alexa_media_player/commit/0cc83a6ff1c25e8b04ecd6b52b3d04e518fef4ae))

* Merge pull request #1113 from alandtse/#1104

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`05d09e2`](https://github.com/custom-components/alexa_media_player/commit/05d09e268d897baa7fd1e915bd0ff0c8337d408e))

* Merge pull request #1128 from custom-components/master

Master ([`77fc818`](https://github.com/custom-components/alexa_media_player/commit/77fc8184c206dd937cffb3e615e7b3efcb0f7852))


## v3.5.2 (2021-01-23)

### Fix

* fix: bump alexapy to 1.22.2
closes #1118 ([`fe97afe`](https://github.com/custom-components/alexa_media_player/commit/fe97afe43972acdbffe8d5ce47effc9e82a0b337))

* fix: fix abort message on login failure ([`c367a6e`](https://github.com/custom-components/alexa_media_player/commit/c367a6e7224f58496658f6232d972f66693a80f8))

* fix: fix config flow abort with failed proxy login
Config flow only allows async abort after async_external_step_done. ([`07c0868`](https://github.com/custom-components/alexa_media_player/commit/07c08685d062f1c92ffea5426feba998bbb18990))

### Unknown

* Merge pull request #1127 from custom-components/dev

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`7b347a2`](https://github.com/custom-components/alexa_media_player/commit/7b347a2bda5288f66e7a6b95868442a0099e0757))

* Merge pull request #1126 from alandtse/#1118

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`41452db`](https://github.com/custom-components/alexa_media_player/commit/41452db84d2163c57daaf6362b3e5a79186b428e))

* Merge pull request #1125 from alandtse/notify_unload

revert: fix: fix entity name for unload ([`8648cb5`](https://github.com/custom-components/alexa_media_player/commit/8648cb52f2e18d5f01b4d0eb9f7e9c2df84013f8))

* Merge pull request #1124 from custom-components/master

Master ([`a9f6114`](https://github.com/custom-components/alexa_media_player/commit/a9f611443bf448c6834245a17f70cb5e0bb37393))

* revert: fix: fix entity name for unload

This reverts commit 717b7f7fea9a6cd8a990b750e35d76a5220a17ac. ([`f280c40`](https://github.com/custom-components/alexa_media_player/commit/f280c40e42b61d2098e37a5becb872b3de3b029f))


## v3.5.1 (2021-01-23)

### Documentation

* docs: update localization ([`617d03e`](https://github.com/custom-components/alexa_media_player/commit/617d03e6093feadfb508a019f1b1067adb40d44b))

### Fix

* fix: handle amazon malformed activities output
Addresses case where update_last_called returns an empty json result and
could break refreshing of data.
closes #1117 ([`62c3180`](https://github.com/custom-components/alexa_media_player/commit/62c3180f7673a6de10f1da5548c9e2e9ecf81181))

* fix: fix target matching for secondary accounts
Secondary accounts have a different unique_id so would fail to match
during convert. Add match on device_serial_number.
closes #1116 ([`2e66fbd`](https://github.com/custom-components/alexa_media_player/commit/2e66fbd73d601bec850ae212fa09b927a9999688))

### Refactor

* refactor: remove unused random dependency ([`2729ca6`](https://github.com/custom-components/alexa_media_player/commit/2729ca6de8fb23ec00458746161e3851b18ba9b5))

### Unknown

* Merge pull request #1123 from custom-components/dev

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`d67d3aa`](https://github.com/custom-components/alexa_media_player/commit/d67d3aaa0b27553d8980dffb9c3a4a50bd8aefd8))

* Merge pull request #1122 from alandtse/#1117

#1117 ([`604330f`](https://github.com/custom-components/alexa_media_player/commit/604330f83432ed2c9015ce26e39256529b9468a8))

* Merge pull request #1121 from alandtse/#1116

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`25b90da`](https://github.com/custom-components/alexa_media_player/commit/25b90da168f86e2c15209875dd6ad4929489a2e2))

* Merge pull request #1119 from custom-components/lokalise-2021-01-23_01-40-46

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`18643ec`](https://github.com/custom-components/alexa_media_player/commit/18643ec3966bd945095c40182a00f97a14996e54))

* Merge pull request #1114 from custom-components/master

Master ([`0ed2c91`](https://github.com/custom-components/alexa_media_player/commit/0ed2c91232ada1f47b6b75000048fa2ed3c64f23))


## v3.5.0 (2021-01-18)

### Feature

* feat: add ability to select non-oauth login
This allows a user to fall back to the old webapp based login mechanism
instead of the oauth token method. This is useful for logging in using
the method from 3.4.1 and below. ([`8f78709`](https://github.com/custom-components/alexa_media_player/commit/8f78709b0d0511f4f0c99c9e8c5f27cd9b476c0a))

* feat: add last_called_summary attribute
Add the last called summary text as an attribute to media_players.
closes #1105 ([`79f23f7`](https://github.com/custom-components/alexa_media_player/commit/79f23f7f80e591d52b508d152049f056b6ae7427))

* feat: enable proxy logins
This replaces the legacy login and should address any changes to the
Amazon login pages. 2FA may not need to be enabled anymore. This also
allows switching to proxy at any time during legacy login. ([`80114ee`](https://github.com/custom-components/alexa_media_player/commit/80114eee7a137fe904448fc34ef8e8fcf4c597f6))

### Fix

* fix: change to single notify service
Previously, every Login had it&#39;s own service which resulted in
multiple services clobbering each other. ([`2298d51`](https://github.com/custom-components/alexa_media_player/commit/2298d5127791312220d7f3306e293e3769215e09))

* fix: add auto submit limit for valid email error ([`18558aa`](https://github.com/custom-components/alexa_media_player/commit/18558aa5989a32c73d79a2b46fa0c37ab3605e83))

* fix: register events after initial setup ([`4a8fa41`](https://github.com/custom-components/alexa_media_player/commit/4a8fa41eb7e21269dcdb2464c6261224bf184bbb))

* fix: fix oauth processing for login ([`43d5432`](https://github.com/custom-components/alexa_media_player/commit/43d5432483a3512eaefac5e3049064e6c636876a))

* fix: iterate uuid for multiple accounts
Amazon does not allow two accounts with oauth tokens and the same
registered serial to stay connected. The uuid should be incremented
as more accounts are added.
closes #1098 ([`16d7acf`](https://github.com/custom-components/alexa_media_player/commit/16d7acf95c99fc487b291488c4d32386ee08672a))

* fix: fix entity name for unload ([`717b7f7`](https://github.com/custom-components/alexa_media_player/commit/717b7f7fea9a6cd8a990b750e35d76a5220a17ac))

* fix: fix unbound alexa_client use case ([`9c0a686`](https://github.com/custom-components/alexa_media_player/commit/9c0a6864ff054b508ada390b00a4d49091f5eff8))

* fix: fix key errors from unloading ([`bf6e613`](https://github.com/custom-components/alexa_media_player/commit/bf6e6130d4745d4f27e0bd3eb869d9a373c13f62))

* fix: add changing unique_id for secondary accounts
This resolves the error of two accounts sharing devices where shared
devices would result in a HA error for lack of unique ids. ([`fbd1e12`](https://github.com/custom-components/alexa_media_player/commit/fbd1e127b1db6a6dd812be514df23f7efe86b447))

* fix: check for existence of data before unload ([`5001e94`](https://github.com/custom-components/alexa_media_player/commit/5001e94cba0d45bc4e69b2c5d428ce693476bb0a))

* fix: fix type error for solo components ([`3c99f03`](https://github.com/custom-components/alexa_media_player/commit/3c99f03cbecb1194433d24678b5f6ae348998f60))

* fix: add lock entry ([`dad2a17`](https://github.com/custom-components/alexa_media_player/commit/dad2a178ce68d5abf74a0011c5d90d60bfdbcf27))

* fix: add logic to avoid reloading config entry
closes #866 ([`5f7cb1d`](https://github.com/custom-components/alexa_media_player/commit/5f7cb1dc79cfb1ecf38ff022c5d784e0db9fad36))

* fix: allow resuming of login session after testing ([`252e133`](https://github.com/custom-components/alexa_media_player/commit/252e13309c7599c41b8f089992be30629793897b))

* fix: fix detection of action required page ([`c082938`](https://github.com/custom-components/alexa_media_player/commit/c0829382bdaced90a19ba8b889340df4221540da))

* fix: allow proxy for action_required ([`6bd1c64`](https://github.com/custom-components/alexa_media_player/commit/6bd1c64467b2eb1acc6dcd11e060f41bdd70f27b))

* fix: pop hass_url ([`d671288`](https://github.com/custom-components/alexa_media_player/commit/d671288429783a867414c85e911c7356c4950a06))

* fix: add http prerequisite ([`e513187`](https://github.com/custom-components/alexa_media_player/commit/e513187d72d2f90316402acb0ce117f3c075a7b9))

* fix: fix otp registration to require confirmation
Previous version did not require confirmation to continue. ([`0a001f1`](https://github.com/custom-components/alexa_media_player/commit/0a001f1a25b0ad8ae44bfd9e993b0f84c4b7da79))

* fix: use lock to stagger account loading
This addresses a potential rate limit issue causing Amazon to return
401s and thus cause a logout for multiple accounts.
closes #1098 ([`8320df8`](https://github.com/custom-components/alexa_media_player/commit/8320df8eafae2d718348a701058848bc15949f73))

### Performance

* perf: remove extraneous notification call ([`b47988f`](https://github.com/custom-components/alexa_media_player/commit/b47988f86efbaf86b694c13f56e25545733fc92b))

### Refactor

* refactor: update debug statements for consistency ([`7b88105`](https://github.com/custom-components/alexa_media_player/commit/7b88105e7b0b77e8df528fb787de825a2246bb23))

* refactor: add debug for alarm_control_panel start ([`56671e3`](https://github.com/custom-components/alexa_media_player/commit/56671e36269b9426d049549f90c38e6190b4454a))

* refactor: add more debugging to unload ([`173807f`](https://github.com/custom-components/alexa_media_player/commit/173807f1af766baed5c71c80694d3245fab20e25))

* refactor: reduce number of startup log display ([`5c63951`](https://github.com/custom-components/alexa_media_player/commit/5c63951855c1fc09072e7ed9f2d462a407730423))

### Style

* style: fix pylint errors ([`3102118`](https://github.com/custom-components/alexa_media_player/commit/31021183b22b5a20ba80de1db8128e76bd93f365))

### Unknown

* Merge pull request #1112 from custom-components/dev

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`bf5a2af`](https://github.com/custom-components/alexa_media_player/commit/bf5a2afd9581ec1c4b4930aaf203ad62b5fcb164))

* Merge pull request #1099 from alandtse/proxy

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`e58c7f9`](https://github.com/custom-components/alexa_media_player/commit/e58c7f913ba38c6a41efe4b0f5098407d6d9f446))

* Merge pull request #1100 from alandtse/#1098

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`19476e7`](https://github.com/custom-components/alexa_media_player/commit/19476e7ab569d10ecfa97d028b41715eb974013e))

* Merge pull request #1095 from custom-components/master

Master ([`5ee0bf6`](https://github.com/custom-components/alexa_media_player/commit/5ee0bf64f3ab91b8801e03c5a471515553c1ad07))


## v3.4.8 (2021-01-08)

### Fix

* fix: fix registration with amazon.com.au
closes #1092 ([`7fff067`](https://github.com/custom-components/alexa_media_player/commit/7fff067392f66e107ab810c8b1b25fec3e6dd9bb))

### Unknown

* Merge pull request #1094 from alandtse/#1092

#1092 ([`0b3cf71`](https://github.com/custom-components/alexa_media_player/commit/0b3cf71b9b22e1a6bcca5ef5e3af7daf95ea32ce))

* Merge pull request #1093 from custom-components/master

Master ([`771b734`](https://github.com/custom-components/alexa_media_player/commit/771b734b94ae0186eea77706e6801c2865ce4ed8))


## v3.4.7 (2021-01-06)

### Fix

* fix: change coordinator update to null operation
Investigating a potential freeze ([`dfc53cc`](https://github.com/custom-components/alexa_media_player/commit/dfc53cc50376e1a480cace18cd0abf776cb1d3fd))

### Unknown

* Merge pull request #1090 from alandtse/#1082

fix: change coordinator update to null operation ([`29fab51`](https://github.com/custom-components/alexa_media_player/commit/29fab515bc68207f588835ec2a42dc6a58505b31))

* Merge pull request #1089 from custom-components/master

Master ([`c6f4f3f`](https://github.com/custom-components/alexa_media_player/commit/c6f4f3f3129418a23f3f03a550da4d96b19749e2))


## v3.4.6 (2021-01-06)

### Fix

* fix: fix cookie exchange during oauth refresh
Fix logic so cookies are exchanged during a token refresh ([`d508a0c`](https://github.com/custom-components/alexa_media_player/commit/d508a0caa60073d6ce78ce1887b0f78c7176c6e0))

* fix: allow devices with notification capability
Added capability check for TIMERS_AND_ALARMS and REMINDERS.
Include_devices will also override the capability check.
closes #1085 ([`0b88157`](https://github.com/custom-components/alexa_media_player/commit/0b88157d367f015073a9dae52e58aa2fea4ae911))

* fix: use sync callback for update coordinator ([`2185a86`](https://github.com/custom-components/alexa_media_player/commit/2185a86ff0bb278609993e8f00092e5c389f6634))

* fix: create login if login session closed ([`47bbfc4`](https://github.com/custom-components/alexa_media_player/commit/47bbfc4dfb793ea1fc8cc7e94003105ba3144e22))

* fix: catch login error on guard init ([`d8c5399`](https://github.com/custom-components/alexa_media_player/commit/d8c5399f8906f30e963646a408fb96444687025b))

* fix: fix keyerror unloading config_flows ([`23f5aff`](https://github.com/custom-components/alexa_media_player/commit/23f5aff1f4e99c4cd5b2076b099c4dfb148080d2))

* fix: fix multie account reauth notification ([`af9aaae`](https://github.com/custom-components/alexa_media_player/commit/af9aaae3f3914629cba37e68609720c4b8f000b6))

* fix: fix events processing to be account specific
Any event was being fired and processed by every account
instance which would result in multiple login attempts and would disconnect each other.
closes #1082 ([`81a87c4`](https://github.com/custom-components/alexa_media_player/commit/81a87c453402e678b02c26b288cd9d3c4cb2c374))

* fix: fix erroneous available on websocket event
Add check that event serial number matches before changing available
state
closes #1042 ([`5860905`](https://github.com/custom-components/alexa_media_player/commit/5860905f9acab231cb5b9e0f5adf5932ca7bdaa7))

### Unknown

* Merge pull request #1088 from custom-components/dev

2021-01-05 ([`680da9f`](https://github.com/custom-components/alexa_media_player/commit/680da9f7c261cade7571f6fb27a7afc784f7c29b))

* Merge pull request #1087 from alandtse/#1082

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`4f0b154`](https://github.com/custom-components/alexa_media_player/commit/4f0b1541abd8673478d2b2d33f877d40f2ab9aff))

* Merge branch &#39;dev&#39; of github.com:custom-components/alexa_media_player into #1082 ([`01d1b6c`](https://github.com/custom-components/alexa_media_player/commit/01d1b6c28b76bec8152d6ab3696d628e894f51bf))

* Merge pull request #1086 from alandtse/#1085

fix: allow devices with notification capability ([`b5a99ab`](https://github.com/custom-components/alexa_media_player/commit/b5a99abeee664fc3a3b30ce2b3071df552d0146c))

* Merge pull request #1080 from alandtse/#1042a

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`5dc85fd`](https://github.com/custom-components/alexa_media_player/commit/5dc85fd2752f44f3b59dfa49ed7751c7e97687ec))

* Merge pull request #1079 from custom-components/master

Master ([`d1e2911`](https://github.com/custom-components/alexa_media_player/commit/d1e2911523ba154f07b84f5aa924fd45e1e3d01e))


## v3.4.5 (2021-01-02)

### Fix

* fix: fix generation of deviceid for oauth signin
Incorrect device id could result in strange login failures unrelated to
submitted data.
closes #1075 ([`1e3a362`](https://github.com/custom-components/alexa_media_player/commit/1e3a3623f79f05be0a3518bf4b112032a326c968))

* fix: show login failure with error page detection
Error page was incorrectly going to action required page. ([`4574e00`](https://github.com/custom-components/alexa_media_player/commit/4574e0058dac31f0377a5f7fc4024b9592cdba19))

### Refactor

* refactor: reduce number of automatic otp retries ([`d8a63f8`](https://github.com/custom-components/alexa_media_player/commit/d8a63f808d4c77bf7870cceca23d9ce77943557b))

### Unknown

* Merge pull request #1078 from custom-components/dev

2020-01-02 ([`0574d35`](https://github.com/custom-components/alexa_media_player/commit/0574d353a53f5d812284103fdddcafcfe5b670e1))

* Merge pull request #1077 from alandtse/#1075

fix: fix oauth issues login issues ([`2948fb5`](https://github.com/custom-components/alexa_media_player/commit/2948fb518fc198db739a22ab1843229aa045fc0d))

* Merge pull request #1074 from custom-components/master

Master ([`1f15e96`](https://github.com/custom-components/alexa_media_player/commit/1f15e964423b2a3fad7ddf7c9b5ea824abf9bff3))


## v3.4.4 (2021-01-01)

### Fix

* fix: ensure string type for configflow
closes #1072 ([`71b26a6`](https://github.com/custom-components/alexa_media_player/commit/71b26a6fa6c8fb8b36aaa19eeb9729702d377597))

### Unknown

* Merge pull request #1073 from alandtse/#1005a

fix: ensure string type for configflow ([`8a87d39`](https://github.com/custom-components/alexa_media_player/commit/8a87d39b8e961683b35d37e90d19f57b33c6eb62))

* Merge pull request #1070 from custom-components/master

Master ([`0d617e9`](https://github.com/custom-components/alexa_media_player/commit/0d617e939e1bf559be92292b0e281205b4dc496d))


## v3.4.3 (2021-01-01)

### Fix

* fix: fix oauth for non-.com domains
closes #1067 ([`c1e5176`](https://github.com/custom-components/alexa_media_player/commit/c1e51763458f24e42082f76c4a5224146f2bb47b))

* fix: fix key error ([`1b2b060`](https://github.com/custom-components/alexa_media_player/commit/1b2b0602438a107c34e84a130c5f042d63b76a12))

* fix: allow registration in multiple HA instances
If more than instance of HA was running using the same account, the
different instances would register the same media player with Amazon resetting
each token. This now ties the registration serial number to HA uuid
Older Alexa Media Players can be removed from Amazon. ([`0a35cde`](https://github.com/custom-components/alexa_media_player/commit/0a35cde62afd14682fa5c4a7b148236d7531b0c0))

* fix: ignore devices without music capability
closes #1011 ([`b9df09d`](https://github.com/custom-components/alexa_media_player/commit/b9df09d34b7c6c20686bc4e68b4b651a88dd6943))

* fix: check flow existence prior to unload ([`be6ab00`](https://github.com/custom-components/alexa_media_player/commit/be6ab009165937ce97704e966be1eaa1cac61b05))

* fix: address empty filter list for switch ([`2c10744`](https://github.com/custom-components/alexa_media_player/commit/2c107441c84d8768c5faf987b1400fa0db700e20))

### Style

* style: address lint error for unnecessary elseif ([`457e268`](https://github.com/custom-components/alexa_media_player/commit/457e26883e61ed6f7b021227ced4d5a143233928))

### Unknown

* Merge pull request #1069 from custom-components/dev

2020-12-31 ([`0e791fd`](https://github.com/custom-components/alexa_media_player/commit/0e791fd1a50ea1f318b37f536b73dac8f4e1708b))

* Merge pull request #1068 from alandtse/#1005a

fix: fix oauth for non-.com domain ([`b44971d`](https://github.com/custom-components/alexa_media_player/commit/b44971ddf3cc91f11d203027920b485be27c0c64))

* Merge pull request #1065 from alandtse/#1005a

fix: address empty filter list for switch ([`f466ed9`](https://github.com/custom-components/alexa_media_player/commit/f466ed9c383d96337ce17aac73d1d4dcf5ae2586))

* Merge pull request #1064 from custom-components/master

Master ([`1ae1a98`](https://github.com/custom-components/alexa_media_player/commit/1ae1a98c3f4a65fc7502fdf6ccfabc7c934e0b3c))


## v3.4.2 (2020-12-31)

### Documentation

* docs: update localization ([`ab8f4c4`](https://github.com/custom-components/alexa_media_player/commit/ab8f4c4782ba918cfbc47e1afd918f2527e10a99))

### Fix

* fix: add oauth token refresh
This should avoid expiration of cookies since we refresh it every sixty
minutes. Please force logout and relogin to enable oauth refresh.
closes #1005 ([`77e9d6c`](https://github.com/custom-components/alexa_media_player/commit/77e9d6c5d5f5ae5e2612e728fb704db18ddb772c))

* fix: fix handling of lack of bluetooth_state ([`980b530`](https://github.com/custom-components/alexa_media_player/commit/980b530a5fb97c9d93610225e51edd4eaa89c049))

### Style

* style: add typing hints for AlexaLogin ([`e9ee26f`](https://github.com/custom-components/alexa_media_player/commit/e9ee26f5556dcb437ace5e73607bef20a1065182))

### Unknown

* Merge pull request #1063 from custom-components/dev

The oauth refresh will only impact new logins. Please force logout with alexa_media.force_logout or delete your cookie file and restart.
closes #1005 ([`b727c71`](https://github.com/custom-components/alexa_media_player/commit/b727c711530926e7395d824ca7b9afc3c1a4c049))

* Merge pull request #1062 from custom-components/lokalise-2020-12-31_03-44-05

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`4167680`](https://github.com/custom-components/alexa_media_player/commit/4167680f339e5a8f547664f3237e43230b5e4a11))

* Merge pull request #1061 from alandtse/#1005a

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`75bd9b9`](https://github.com/custom-components/alexa_media_player/commit/75bd9b9c133b1f480a98b02742a5363a2e077494))

* Merge pull request #1044 from custom-components/master

Master ([`b81966a`](https://github.com/custom-components/alexa_media_player/commit/b81966a62b38caa47a5ba8878cd1168257d40374))


## v3.4.1 (2020-12-12)

### Fix

* fix: bump alexapy to 1.17.2
This should avoid additional API calls if a bad login is detected. ([`a1606b7`](https://github.com/custom-components/alexa_media_player/commit/a1606b79227fe57ca1b9c181bade9767077c234a))

* fix: prevent websocket reconnection on login error ([`8c5f7bc`](https://github.com/custom-components/alexa_media_player/commit/8c5f7bc00ce1b29a04752fb8cf3ace8f286307e0))

* fix: fix saving of otp_secret during relogin ([`efb2e37`](https://github.com/custom-components/alexa_media_player/commit/efb2e3785ab17f4eff1529d01cc43d3d32b4bed6))

* fix: fix ui update of unavailable devices
UI updates were not being processed for unavailable devices resulting
in media players unable to go offline
closes #1042 ([`2041c77`](https://github.com/custom-components/alexa_media_player/commit/2041c774c9c376a65c35abf074735b574cbbfb60))

* fix: add 2fa key error checking ([`c3cb200`](https://github.com/custom-components/alexa_media_player/commit/c3cb200df1c2f2a69109c46f0e631cfa40aa5ed9))

* fix: bump alexapy to 1.17.1
closes #1033
closes #1037 ([`62231e1`](https://github.com/custom-components/alexa_media_player/commit/62231e18fed9b8f150a38d840f782e4e71118ccd))

### Refactor

* refactor: refactor test for login status success ([`7f4da8a`](https://github.com/custom-components/alexa_media_player/commit/7f4da8a452d9d07a5d40069ca749f5c6777f8e12))

### Style

* style: update debug to show state ([`9d1d22f`](https://github.com/custom-components/alexa_media_player/commit/9d1d22f920049d553596368353f6cdf925b7de6b))

### Unknown

* Merge pull request #1043 from custom-components/dev

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`c9d179a`](https://github.com/custom-components/alexa_media_player/commit/c9d179aa7e0364773e90fe18a0d790435496b8fd))

* Merge pull request #1041 from alandtse/pyotp_check

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`4eaa4b3`](https://github.com/custom-components/alexa_media_player/commit/4eaa4b37192bfda148b76196201673d056b8dab3))

* Merge pull request #1032 from custom-components/master

Master ([`262ee5d`](https://github.com/custom-components/alexa_media_player/commit/262ee5dc0919544315b9ccf5f28c79df06bfd0f3))


## v3.4.0 (2020-12-05)

### Feature

* feat: add custom command support
This allows issuing commands to devices directly.
https://github.com/custom-components/alexa_media_player/wiki#run-custom-command ([`9394143`](https://github.com/custom-components/alexa_media_player/commit/93941432acce6f2915e53aff212049e540a513a2))

### Unknown

* Merge pull request #1031 from custom-components/dev

2020-10-05 ([`3b91a31`](https://github.com/custom-components/alexa_media_player/commit/3b91a317c1924396e534adf91b235a9ee07f0c96))

* Merge pull request #1030 from alandtse/custom_command

feat: add custom command support ([`591b8a9`](https://github.com/custom-components/alexa_media_player/commit/591b8a9a40d7a1b9243eaf60274c6f042c2da584))

* Merge pull request #1027 from custom-components/master

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`aa400e3`](https://github.com/custom-components/alexa_media_player/commit/aa400e3730c704e738165096f8514ea52a40eebb))


## v3.3.1 (2020-11-29)

### Fix

* fix: fix key error on otp_secret
closes #1025 ([`b07a722`](https://github.com/custom-components/alexa_media_player/commit/b07a722776d7a0b288e2b84636f644119ca5da1c))

### Unknown

* Merge pull request #1026 from alandtse/pyotp

fix: fix key error on otp_secret ([`8ad7d32`](https://github.com/custom-components/alexa_media_player/commit/8ad7d32345bb59fca6e76c45158469f1e0f84d4d))

* Merge pull request #1021 from custom-components/master

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`697f1fe`](https://github.com/custom-components/alexa_media_player/commit/697f1fe71a779d135982d09f4008f497c6b88f9e))


## v3.3.0 (2020-11-27)

### Ci

* ci: use an Python 3.8 to fix flake8 (#1017) ([`41cd46f`](https://github.com/custom-components/alexa_media_player/commit/41cd46fce1faf8652bca5e645a7cbe6d7148b238))

* ci: fix validate ci name

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`61b4902`](https://github.com/custom-components/alexa_media_player/commit/61b49028116e2c3e6434fc2f82177183fab0c27e))

* ci: switch to HACS Action for hacs validation ([`2b52853`](https://github.com/custom-components/alexa_media_player/commit/2b52853685d9dcd161aee49e7f20c787ce19e1b1))

* ci: fix release_version

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`ffe2ea1`](https://github.com/custom-components/alexa_media_player/commit/ffe2ea15f16f36a98fd4d8d5554f6ff7a8cd719a))

* ci: update release_version tag

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`3574fde`](https://github.com/custom-components/alexa_media_player/commit/3574fde68c11992cdf399bc7e976bad53a7dfad2))

* ci: fix release version setting

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`60dc886`](https://github.com/custom-components/alexa_media_player/commit/60dc8861266bf5dd6787d343353eea42c619560d))

* ci: update release variable

https://github.blog/changelog/2020-10-01-github-actions-deprecating-set-env-and-add-path-commands/
Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`f2258aa`](https://github.com/custom-components/alexa_media_player/commit/f2258aa06254c7849340f707f2e1fee621b686f7))

### Documentation

* docs: update localization ([`d07176a`](https://github.com/custom-components/alexa_media_player/commit/d07176acf39f3ddace45908e97b69597684b2628))

### Feature

* feat: add automatic relogin
Requires built-in 2FA to be used
https://github.com/custom-components/alexa_media_player/wiki/Configuration#built-in-2fa-app ([`23c44c3`](https://github.com/custom-components/alexa_media_player/commit/23c44c3b2b6f60b936a368a1fde2c9c6e4511d59))

* feat: add built-in 2FA generator
This allows the component to generate 2FA codes as needed.
https://github.com/custom-components/alexa_media_player/wiki/Configuration#built-in-2fa-app ([`a025774`](https://github.com/custom-components/alexa_media_player/commit/a025774801aee5ba15a522246f269a12a2eda335))

### Fix

* fix: clean up cookie file input handling
Fix various issues with cookie file input including ignoring empty
entries and not adding the header repeatedly. ([`b04274f`](https://github.com/custom-components/alexa_media_player/commit/b04274fc5556a1e99dd0de6fb524e98404a76478))

### Unknown

* Merge pull request #1019 from custom-components/dev

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`3bafb59`](https://github.com/custom-components/alexa_media_player/commit/3bafb5937e2ab5a05fabbdfcd5f3f4ac9bdf66b5))

* Merge pull request #1020 from custom-components/lokalise-2020-11-27_04-53-55

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`6283bcd`](https://github.com/custom-components/alexa_media_player/commit/6283bcdca043e68d14c83aa04c0d071b7537f164))

* Merge pull request #1018 from alandtse/pyotp

Pyotp ([`09f53f6`](https://github.com/custom-components/alexa_media_player/commit/09f53f6491ef7fb7a19a91b00c06099389122223))

* Merge pull request #983 from KTibow/patch-2

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`98f6c92`](https://github.com/custom-components/alexa_media_player/commit/98f6c929cd067522c3af97439bb412ada49c09a7))

* Merge branch &#39;dev&#39; into patch-2 ([`59608a5`](https://github.com/custom-components/alexa_media_player/commit/59608a5227db2ccb6cf55aba069f5eba9cbd8aab))

* Update .github/workflows/validate.yaml ([`f7174bb`](https://github.com/custom-components/alexa_media_player/commit/f7174bb9bc64d05915622d9980399642ca63a9c2))

* Update .github/workflows/validate.yaml ([`c32364f`](https://github.com/custom-components/alexa_media_player/commit/c32364fa53c52a0feebef86109589f6ea7b004fa))

* Merge pull request #1010 from custom-components/master

Master ([`1aadff6`](https://github.com/custom-components/alexa_media_player/commit/1aadff6a7e16b53fe3601ecf3ed89f2cb2f81e22))

* Merge pull request #1009 from custom-components/dev

ci: update release variable ([`454d43f`](https://github.com/custom-components/alexa_media_player/commit/454d43f953009430eff7d0e8cc1a557c4ab6a58b))


## v3.2.3 (2020-11-21)

### Ci

* ci: update stale messaging

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`5fdc344`](https://github.com/custom-components/alexa_media_player/commit/5fdc34484d2eb31aa12a653273df4ca3a30ff8cb))

* ci: add stale action

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`29bc04f`](https://github.com/custom-components/alexa_media_player/commit/29bc04f32d2f8756e8232f9713f3ecbeca18bce6))

* ci: restore lokalise download

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`90a6463`](https://github.com/custom-components/alexa_media_player/commit/90a646315e711cacebb6dc192871d6ff9b1a207e))

### Documentation

* docs: fix wiki link in README.md (#995)

fix a link to the wiki that did not go anywhere ([`96435b9`](https://github.com/custom-components/alexa_media_player/commit/96435b96b351a137f10aea31a548041902bb169e))

* docs: update localization ([`9702cfb`](https://github.com/custom-components/alexa_media_player/commit/9702cfbc67e2f65d4c44b88b2a73e08018d72647))

### Fix

* fix: convert reminder alarmTime when float
closes #826 ([`da8b724`](https://github.com/custom-components/alexa_media_player/commit/da8b724aa8c5d494854575103005320159702d10))

### Unknown

* Merge pull request #1008 from custom-components/dev

2020-10-20 ([`de88ea7`](https://github.com/custom-components/alexa_media_player/commit/de88ea7a084e96ce94e95599b2f854f92b11ade9))

* Merge pull request #1007 from alandtse/#826

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`bf59022`](https://github.com/custom-components/alexa_media_player/commit/bf590224bc0f21f7e32d3210260f2447861b263e))

* Use ha-blueprint ([`fd2e914`](https://github.com/custom-components/alexa_media_player/commit/fd2e914c79e3b7f3a8e7f66e1faaf0a37ba80fdd))

* Merge pull request #980 from custom-components/master

Master ([`b312cfc`](https://github.com/custom-components/alexa_media_player/commit/b312cfc5bca861f635fcfefa91bf531096743acf))

* Merge pull request #979 from custom-components/lokalise-2020-10-12_07-41-11

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`99c8afe`](https://github.com/custom-components/alexa_media_player/commit/99c8afe4636b841a2ba15260395867f38f563eaa))


## v3.2.2 (2020-10-11)

### Fix

* fix: stop refresh on disabled entities
closes #975 ([`db3fa9c`](https://github.com/custom-components/alexa_media_player/commit/db3fa9c3d8afd55be2d094667110c8ac825a227f))

### Style

* style: black sensor.py ([`0d03776`](https://github.com/custom-components/alexa_media_player/commit/0d0377693c28d1ec1740100ccf4368608ce5ca47))

### Unknown

* Merge pull request #978 from custom-components/dev

2020-10-10 ([`274e492`](https://github.com/custom-components/alexa_media_player/commit/274e492a1aa9cf93fff9c1a925531b0db147f995))

* Merge pull request #977 from alandtse/#975

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`a05c289`](https://github.com/custom-components/alexa_media_player/commit/a05c28986b0d1ecd2262f24210608432a27d32fa))

* Merge pull request #971 from custom-components/master

Master ([`ed97fcd`](https://github.com/custom-components/alexa_media_player/commit/ed97fcdf4050a296d6f84bc9f1e441b211483150))


## v3.2.1 (2020-10-02)

### Fix

* fix: delay processing until added to hass ([`235e718`](https://github.com/custom-components/alexa_media_player/commit/235e7189480bd2813734e8c7e060ae5d2033778f))

### Unknown

* Merge pull request #970 from alandtse/#964

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`e95e583`](https://github.com/custom-components/alexa_media_player/commit/e95e583ac1cbb41fc7463d6945336918b911673f))


## v3.2.0 (2020-10-02)

### Ci

* ci: enable codeql scanning ([`196e41e`](https://github.com/custom-components/alexa_media_player/commit/196e41ee79a1aac632c87ec3f05bbae763514687))

### Feature

* feat: add notification events ([`6332750`](https://github.com/custom-components/alexa_media_player/commit/63327507e9bbfe9a313b16ed868924da64ad7322))

* feat: add process_timestamp attribute to notification sensors (#966)

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`c4a6df5`](https://github.com/custom-components/alexa_media_player/commit/c4a6df597831ae472d5d086d6ebc6ae4ed0258f7))

* feat: add timer for play_music ([`801bb80`](https://github.com/custom-components/alexa_media_player/commit/801bb80f11dc8ca05d2886e717431a1bbcabbbf8))

### Fix

* fix: improve dnd sync
This should drastically improve DND status updates to match external
changes.
closes #950 ([`5805a0b`](https://github.com/custom-components/alexa_media_player/commit/5805a0b14293300c584b4a18322befa1cfecf0fe))

* fix: allow switches to poll to sync
Switches derive info from the media player so this increases sync rate ([`3304726`](https://github.com/custom-components/alexa_media_player/commit/330472620fd8b80707716d9eb2830354ddb4c1d0))

* fix: update ha state even if skip_api called ([`9ea414b`](https://github.com/custom-components/alexa_media_player/commit/9ea414bad449796b68109d822b1a7cc084e9e6d8))

* fix: refresh media players with main update
The __init__ updater was not properly refreshing media player info ([`d28213a`](https://github.com/custom-components/alexa_media_player/commit/d28213a59201b11d1684d3368087ce3000ba062c))

* fix: save cookies_txt into configuration ([`c74824e`](https://github.com/custom-components/alexa_media_player/commit/c74824eaf5f5caaf0635b99929964b6c36378e96))

* fix: ignore PUSH_DEVICE_SETUP_STATE_CHANGE
closes #959 ([`56e020f`](https://github.com/custom-components/alexa_media_player/commit/56e020f35cba4e845ce5a5b881d18916f990bb2d))

### Performance

* perf: memoize notification state ([`4b71769`](https://github.com/custom-components/alexa_media_player/commit/4b71769e58dc47f5466d18060e8aece7bd6d9f98))

### Refactor

* refactor: reduce false positive for dnd changes ([`079b554`](https://github.com/custom-components/alexa_media_player/commit/079b55436c9dae4ff1a83bfacd958cc7f1cd5380))

* refactor: update logs to be more clear
Switch logs will differentiate state changes when HA action vs non-HA ([`9bfb96e`](https://github.com/custom-components/alexa_media_player/commit/9bfb96ee3554b46e5652e4a4cf5305a653771a7d))

* refactor: remove unused _state variable ([`26c5ac3`](https://github.com/custom-components/alexa_media_player/commit/26c5ac3aff9e276d30d3f9edbdc680b7c792ca25))

* refactor: switch to self.async_write_ha_state() ([`634a7a9`](https://github.com/custom-components/alexa_media_player/commit/634a7a917ea0dabd043bd2c8465c94b9e80669f2))

### Style

* style: add additional typing ([`7fc687d`](https://github.com/custom-components/alexa_media_player/commit/7fc687d4135d87edc4991ec5db1ea01519a2c18a))

### Unknown

* Merge pull request #968 from custom-components/dev

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`797515c`](https://github.com/custom-components/alexa_media_player/commit/797515cda553db7ccba5d6344d26a41a46d6238d))

* Merge pull request #967 from alandtse/#964

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`41607ff`](https://github.com/custom-components/alexa_media_player/commit/41607ffb25244fa166066036ce2632b37784468a))

* Merge pull request #962 from alandtse/#950

#950 ([`0dfddd9`](https://github.com/custom-components/alexa_media_player/commit/0dfddd9f524adf8242e56dafbeb50b006d47bdd2))

* Merge pull request #960 from custom-components/timer

feat: add timer for play_music ([`955b5db`](https://github.com/custom-components/alexa_media_player/commit/955b5db4a5626150a1a51b1a9137698fa257f9c8))


## v3.1.2 (2020-09-28)

### Fix

* fix: bump to alexapy 1.15.2

closes #957 ([`c384110`](https://github.com/custom-components/alexa_media_player/commit/c384110acdef9d708c00e9c5c78d1177f4b59d93))

### Unknown

* Merge pull request #958 from custom-components/dev

 fix: bump to alexapy 1.15.2 ([`35aa14f`](https://github.com/custom-components/alexa_media_player/commit/35aa14f22154afbd053cdee61122cd72850cd12c))

* Merge pull request #956 from custom-components/master

Master ([`edeef5b`](https://github.com/custom-components/alexa_media_player/commit/edeef5beb6c124a18cc4cdde56780b6a129bc5e6))


## v3.1.1 (2020-09-28)

### Fix

* fix: detect login changes with alarm/switches
Upon relogin, alarm control panel and switches could cause an immediate relogin request because
of use of an outdated session. ([`c567d40`](https://github.com/custom-components/alexa_media_player/commit/c567d4088374cb226780fc9020424e8d94823a09))

### Style

* style: remove redundant comments ([`5a0268b`](https://github.com/custom-components/alexa_media_player/commit/5a0268be11dc9b6c25500d923a361391f366e9fd))

### Unknown

* Merge pull request #955 from alandtse/cookies.txt

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`7988fca`](https://github.com/custom-components/alexa_media_player/commit/7988fca914b6ee7e65088986ca64bde90d277272))

* Merge pull request #954 from custom-components/master

Master ([`0114e3b`](https://github.com/custom-components/alexa_media_player/commit/0114e3bd133e592d50138dcde02cf1274907d9d0))


## v3.1.0 (2020-09-27)

### Documentation

* docs: update localization ([`94e4e09`](https://github.com/custom-components/alexa_media_player/commit/94e4e09257a267343497c2ae53319f2cbfebd822))

### Feature

* feat: add parameter loading of cookies.txt
Input available in Integrations page. Currently testing for stability ([`5d69175`](https://github.com/custom-components/alexa_media_player/commit/5d6917571752f3d20e855975a10aab9beae007b5))

### Fix

* fix: update to alexapy 1.15.1 ([`f18fe6e`](https://github.com/custom-components/alexa_media_player/commit/f18fe6ee2daa0210e683db9f89a2d1583afb141c))

* fix: catch login errors for bluetooth/lastcalled ([`51ec251`](https://github.com/custom-components/alexa_media_player/commit/51ec2517ff283944b6eda438b238d0d168dfde9b))

* fix: await sleep calls ([`0423bd8`](https://github.com/custom-components/alexa_media_player/commit/0423bd89ffd5a5e8c5f09c63b447b4ad52d2e331))

### Style

* style: clean up logging for switch ([`2a0496c`](https://github.com/custom-components/alexa_media_player/commit/2a0496c8843efcee61079b5e3e97acfd6fc02607))

* style: use constant for securitycode ([`1e34e8d`](https://github.com/custom-components/alexa_media_player/commit/1e34e8d0bfed93466b911e4bfc7a15d99199c8e3))

### Unknown

* Merge pull request #953 from custom-components/dev

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`d574974`](https://github.com/custom-components/alexa_media_player/commit/d574974078ff68213f4201a6dadc385f92857846))

* Merge pull request #952 from custom-components/lokalise-2020-09-27_23-36-38

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`e678f4f`](https://github.com/custom-components/alexa_media_player/commit/e678f4f988a89c0d2b3f3d436031e26f30832dc9))

* Merge pull request #951 from alandtse/cookies.txt

feat: allow Cookies.txt importing ([`cac80ec`](https://github.com/custom-components/alexa_media_player/commit/cac80ecc69c21c43690dff051b8f63995020bbc5))

* Merge pull request #949 from custom-components/master

Master ([`989c157`](https://github.com/custom-components/alexa_media_player/commit/989c157761e4642463d024bcdcdd545958f27a40))


## v3.0.1 (2020-09-27)

### Ci

* ci: disable lokalise autodownload

Lokalise appears to be adding an extra `\` before `\n` which breaks things ([`1ffc9ef`](https://github.com/custom-components/alexa_media_player/commit/1ffc9efeedb45e7d27cd9a86a37c0e0a855c822e))

* ci: use consolidated GH actions (#947) ([`8e086ea`](https://github.com/custom-components/alexa_media_player/commit/8e086ea680cca858b2de94b49ba98b6c9fb65394))

### Documentation

* docs: add Norwegian (#945) ([`1519b59`](https://github.com/custom-components/alexa_media_player/commit/1519b59a305f20350273a51a5dca39066a81704e))

* docs: update localization ([`31d26ec`](https://github.com/custom-components/alexa_media_player/commit/31d26ec89aaeea6490634aca912106758cb71277))

### Fix

* fix: rebuild translations (#948)

closes #944 ([`ebcc245`](https://github.com/custom-components/alexa_media_player/commit/ebcc2454ebf4e5e92d82ee0d8614ade6fa9f4e46))

* fix: fix errors in nb.json ([`0ec8b53`](https://github.com/custom-components/alexa_media_player/commit/0ec8b535c1c53542d407238826e6422df9cd8446))

* fix: really fix strings.json syntax ([`3d0a330`](https://github.com/custom-components/alexa_media_player/commit/3d0a330afb64ddca2e6d612a76e940cadec77b47))

* fix: fix string.json syntax ([`ac128eb`](https://github.com/custom-components/alexa_media_player/commit/ac128eb52b43d8ca6972b8e2c605fc5e36376bbc))

* fix: update strings.json to remove title key (#946)

got this warrning `Warning: G] [TRANSLATIONS] config.title key has been moved out of config and into the root of strings.json. Starting Home Assistant 0.109 you only need to define this key in the root if the title needs to be different than the name of your integration in the manifest.` ([`2488126`](https://github.com/custom-components/alexa_media_player/commit/24881261d0e40796ce5d31bc2ed1d2c79361f69a))

### Unknown

* Merge pull request #933 from custom-components/lokalise-2020-09-14_04-56-04

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`1d7f66f`](https://github.com/custom-components/alexa_media_player/commit/1d7f66f032b1e0025c994eef1ca2223a2b7fbb48))


## v3.0.0 (2020-09-14)

### Breaking

* fix: shorten event names

Shorten events to remove _player to avoid overruning events type length.
Closes #926

BREAKING CHANGE:  Events have had their names shortened. Please check the wiki for details. ([`0d04560`](https://github.com/custom-components/alexa_media_player/commit/0d04560d49013f49d5029f794e3012c8a9bca16e))

### Ci

* ci: add additiona lokalise options ([`263c2ab`](https://github.com/custom-components/alexa_media_player/commit/263c2ab13e415fe3c6c63b1496ef970d36867e3f))

* ci: add more changelog sections ([`715b49e`](https://github.com/custom-components/alexa_media_player/commit/715b49e64921b6a2516173ee6eced292a558c200))

### Documentation

* docs: update localization ([`1bdef28`](https://github.com/custom-components/alexa_media_player/commit/1bdef28613659efc96ec9fdd06e6dbb9b5de9950))

### Fix

* fix: replace html with double space ([`bbd166b`](https://github.com/custom-components/alexa_media_player/commit/bbd166b9dfc2c1e402926644ec500925e2bbb2ae))

* fix: replace `\n` with `&lt;br /&gt;`
closes #909 ([`f82982c`](https://github.com/custom-components/alexa_media_player/commit/f82982c672dd893488cab495776fb2262cbbd61a))

* fix: provide blank message for errors ([`b1647ef`](https://github.com/custom-components/alexa_media_player/commit/b1647efdc4b5faf2e176f65dcd7090d087f9aef2))

### Unknown

* Merge pull request #931 from custom-components/dev

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`5397e6f`](https://github.com/custom-components/alexa_media_player/commit/5397e6fec12d62a858b25f649e03dc7880359d4b))

* Merge pull request #932 from alandtse/#926

fix: replace html with double space ([`5aec659`](https://github.com/custom-components/alexa_media_player/commit/5aec659d940ac6bb02a5902719a758e678e08aa2))

* Merge pull request #930 from custom-components/lokalise-2020-09-13_05-42-42

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`50e3de1`](https://github.com/custom-components/alexa_media_player/commit/50e3de1feeba34bfe830f079357d1a322f819e5c))

* Merge pull request #928 from alandtse/#926

fix: replace `\n` with `&lt;br /&gt;` ([`bbc2510`](https://github.com/custom-components/alexa_media_player/commit/bbc251014974a0ce5df1e0741fc89e52d27f61b1))

* Merge pull request #927 from alandtse/#926 ([`405dc10`](https://github.com/custom-components/alexa_media_player/commit/405dc10e19c5fe36b97f2f583797b21dd818c68d))

* Merge pull request #923 from custom-components/master

Master ([`78acbc3`](https://github.com/custom-components/alexa_media_player/commit/78acbc397d519014061167670df84bce6d969733))


## v2.11.2 (2020-09-08)

### Fix

* fix: add packaging dependency
closes #920 ([`22db07c`](https://github.com/custom-components/alexa_media_player/commit/22db07c0946a50951db39217a2e4fd05f6ef7bad))

### Unknown

* Merge pull request #922 from custom-components/dev

fix: add packaging dependency ([`14d4a15`](https://github.com/custom-components/alexa_media_player/commit/14d4a155eebbd36acf518d0c5a4999d295441fea))

* Merge pull request #921 from alandtse/#915

fix: add packaging dependency ([`e6f2a47`](https://github.com/custom-components/alexa_media_player/commit/e6f2a47a8bcf17864acae6941e84e077a9b69228))

* Merge pull request #918 from custom-components/master

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`ba2f2a5`](https://github.com/custom-components/alexa_media_player/commit/ba2f2a56351abf8ada8de8e574c3508ee955ef83))


## v2.11.1 (2020-09-08)

### Ci

* ci: add todo configuration ([`eaa7a6d`](https://github.com/custom-components/alexa_media_player/commit/eaa7a6d0477274424ca247c4207bfcec72bfde63))

### Documentation

* docs: update localization ([`d2e076a`](https://github.com/custom-components/alexa_media_player/commit/d2e076a82bbaea3b82033d2b44c08b7ed843ff9e))

* docs: fix typo ([`af55319`](https://github.com/custom-components/alexa_media_player/commit/af55319f5c2a77460cc48f4804c80e2590f54c14))

* docs: update bug report template for 2FA ([`e0306d0`](https://github.com/custom-components/alexa_media_player/commit/e0306d04353a1919ac37eca4dbc28bc4b6396a73))

### Fix

* fix: remove use of semver
HA apparently does not use semver.
closes #915 ([`61f0f52`](https://github.com/custom-components/alexa_media_player/commit/61f0f5219cc82da45d8febf4061a1b1de7633c76))

### Unknown

* Merge pull request #917 from custom-components/dev

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`a6a0a1c`](https://github.com/custom-components/alexa_media_player/commit/a6a0a1c46d05bc22c944ef5bc0c2c0dfca82ecbd))

* Merge pull request #916 from alandtse/#915

fix: remove use of semver ([`3f9ddf0`](https://github.com/custom-components/alexa_media_player/commit/3f9ddf0248469a49f65f2b5dcb6bb3d6e2b3ae50))

* Merge pull request #914 from custom-components/lokalise-2020-09-06_21-33-14

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`b6b4cbd`](https://github.com/custom-components/alexa_media_player/commit/b6b4cbd6f072bf26ac0972f04602cdd16584f73d))

* Merge pull request #907 from custom-components/master

Master ([`20a1800`](https://github.com/custom-components/alexa_media_player/commit/20a18008d88972175d1497271da7ab8574e1cd7f))


## v2.11.0 (2020-09-06)

### Feature

* feat: add force_logout service
This is intended for debugging use but can be used to simulate a
Amazon disconnect. This will delete any .pickle files as a side effect. ([`fe057fb`](https://github.com/custom-components/alexa_media_player/commit/fe057fbfd6e96c2429e2455b96a491c7ebb32349))

### Fix

* fix: fix multiple discovered integrations
The component will only spawn a single config_flow on disconnect and
will wait for user interaction before starting the login process. This
should eliminate the expired captcha bug.  This includes multiple config_flow fixes to
ease data entry and address corner cases.
closes #903 ([`793ee06`](https://github.com/custom-components/alexa_media_player/commit/793ee061e0619664c18ba353b7f19964a416ff51))

* fix: fix lint error on media_image_url ([`e0b10a4`](https://github.com/custom-components/alexa_media_player/commit/e0b10a4afc5b4961b9cf287e14e5c5826cac513b))

* fix: add resilience to websocket_enabled check
Addresses case where email may have been removed ([`3b6ed97`](https://github.com/custom-components/alexa_media_player/commit/3b6ed97d8980d00203063ed165ff0be2f83f6417))

* fix: delay login attempt until user interaction
This should fix the expired captcha problem ([`0e59865`](https://github.com/custom-components/alexa_media_player/commit/0e59865a2fda4c43547c15bf8a6da1c977bceb09))

* fix: update options data only if new ([`e7840f5`](https://github.com/custom-components/alexa_media_player/commit/e7840f52757577de4f02652d0bcd9d7bcea04d71))

### Refactor

* refactor: add alexa_media base class
This will allow simpler login change detection ([`c1ce7d1`](https://github.com/custom-components/alexa_media_player/commit/c1ce7d1c642004f910c4379ae44aba57f9101500))

* refactor: add debug logging on play_media ([`6d8a2a5`](https://github.com/custom-components/alexa_media_player/commit/6d8a2a588b250e6c3d0af9afa10f94b8f7baa16a))

### Unknown

* Merge pull request #906 from custom-components/dev

2020-09-06 ([`bfd86a1`](https://github.com/custom-components/alexa_media_player/commit/bfd86a152331abecf51027cd2243e39fe2c5c14e))

* Merge pull request #905 from alandtse/#903

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`a3fc6e7`](https://github.com/custom-components/alexa_media_player/commit/a3fc6e764cc5a478b5391d91789ef032c1a4ce5a))

* Merge pull request #900 from custom-components/master

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`bc39a0f`](https://github.com/custom-components/alexa_media_player/commit/bc39a0f9e3ce361453bea607fa52f2fe7edc11a7))


## v2.10.6 (2020-08-29)

### Fix

* fix: add wrapt dependency ([`10f6238`](https://github.com/custom-components/alexa_media_player/commit/10f6238735db593c218bc7374a984439c4dbab9a))

### Unknown

* Merge pull request #899 from custom-components/dev

2020-08-29 ([`b70b11a`](https://github.com/custom-components/alexa_media_player/commit/b70b11a285b6c4cf3f2a79665b363baafbcc44e7))

* Merge pull request #898 from alandtse/no_configurator

fix: add wrapt dependency ([`1629119`](https://github.com/custom-components/alexa_media_player/commit/162911939bc90bb90698561ad264d4d8fe5b0492))

* Merge pull request #895 from custom-components/master

Master ([`790af91`](https://github.com/custom-components/alexa_media_player/commit/790af912cc019d085ee685626318189c42c87357))


## v2.10.5 (2020-08-29)

### Fix

* fix: allow passing of 2FA during config_flow
This is necessary to avoid Amazon&#39;s error about
&#34;Need valid email or phone number&#34;
closes custom-components/alexa_media_player#892 ([`b6aa47e`](https://github.com/custom-components/alexa_media_player/commit/b6aa47e228e8509436baa34b23eead85eb33afdc))

### Refactor

* refactor: convert to config_flow for relogin ([`483a6be`](https://github.com/custom-components/alexa_media_player/commit/483a6bed0ec1624bef9041b33a7badc68aeee352))

### Unknown

* Merge pull request #894 from custom-components/dev

2020-08-28 ([`97f09ac`](https://github.com/custom-components/alexa_media_player/commit/97f09ac3d19edc838f0bab3c9ff2262d69495311))

* Merge pull request #893 from alandtse/no_configurator

No configurator ([`5feb940`](https://github.com/custom-components/alexa_media_player/commit/5feb940efa4ed590a855e2291cb342b823c5f42f))

* Merge pull request #884 from custom-components/master

Master ([`f7ff701`](https://github.com/custom-components/alexa_media_player/commit/f7ff70172ed5589a0ca65572726ff80cffe78073))


## v2.10.4 (2020-08-26)

### Fix

* fix: bump alexapy to 1.13.0
This fixes an issue where we were using the ownerId for permissions.
This could result in permission errors if the logged in user was
different from the deviceOwner. We are now only using the logged
in user.  While my testing didn&#39;t see anything wrong, this was an
extensive update so please report if any features may have broken.
closes #848 ([`879f3f8`](https://github.com/custom-components/alexa_media_player/commit/879f3f8928105bfdac923185c9f8296855cb1d53))

### Unknown

* Merge pull request #883 from custom-components/dev

2020-08-25 ([`45b2269`](https://github.com/custom-components/alexa_media_player/commit/45b2269d0e7deba15533b59358bdf97dfb794849))

* Merge pull request #882 from alandtse/#848

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`6b52713`](https://github.com/custom-components/alexa_media_player/commit/6b527135b93cfe273ba7199737a94191d29d01d4))


## v2.10.3 (2020-08-23)

### Fix

* fix: add semver dependency ([`231fbfd`](https://github.com/custom-components/alexa_media_player/commit/231fbfdd81f9d3ec0d2aaf3c6672d42237d2bf7e))

### Unknown

* Merge pull request #879 from custom-components/dev

08/23/2020 ([`e19f4e4`](https://github.com/custom-components/alexa_media_player/commit/e19f4e46aaa093ad20d26fbd62dc97b875a2107c))

* Merge pull request #877 from custom-components/master

Master ([`ce1cf2e`](https://github.com/custom-components/alexa_media_player/commit/ce1cf2e24dfde1c86e8580d7b77c160fb628b229))


## v2.10.2 (2020-08-23)

### Fix

* fix(sensor): add version aware icon changes ([`ee059a2`](https://github.com/custom-components/alexa_media_player/commit/ee059a274e6822c42bc7fa8bf9fc884b4914ed11))

* fix: handle forgot password page
This happens if Amazon detects too many bad logins. Further action may
be required from the user before trying to login again. ([`ab51a0f`](https://github.com/custom-components/alexa_media_player/commit/ab51a0f8d35ae0667a5313fdb86f19d222b9c630))

* fix: swap icon from timer-off to timer-off-outline ([`b2e774e`](https://github.com/custom-components/alexa_media_player/commit/b2e774e874fbc117371888b97b6fe719659ea304))

* fix: fix TypeError on use of async_fire
async_fire is not a coroutine and would cause a TypeError when a relogin
was required
closes #867 ([`5d11757`](https://github.com/custom-components/alexa_media_player/commit/5d117570186635b05b74ace8b277efcb0396988d))

* fix: fire `alexa_media_player_relogin_required`
This is intended to eventually replace alexa_media_player/relogin_required
which appears to cause issues in testing through the HA UI ([`7bdf08e`](https://github.com/custom-components/alexa_media_player/commit/7bdf08e13c17c15f5470a68c18f03e0f518fcf3a))

### Unknown

* Merge pull request #876 from custom-components/dev

2020-08-22 ([`d0dd3b0`](https://github.com/custom-components/alexa_media_player/commit/d0dd3b065bbd9850fb4c745431f1eba7e8fa99fd))

* Merge pull request #852 from alandtse/#851

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`590070c`](https://github.com/custom-components/alexa_media_player/commit/590070cc1c31fa4690f8c4a92848f5d820e8de14))

* Merge pull request #875 from alandtse/#870

fix: handle forgot password page ([`7f7046e`](https://github.com/custom-components/alexa_media_player/commit/7f7046e2d3f373618613938e2cef495f466a37cb))

* Merge pull request #871 from alandtse/#867

fix: fix TypeError on use of async_fire ([`5463c72`](https://github.com/custom-components/alexa_media_player/commit/5463c72ec99e6206bafd531758d312b7e29c2579))

* Merge pull request #858 from alandtse/alexapy1.12.1

fix: fire `alexa_media_player_relogin_required` ([`03bed50`](https://github.com/custom-components/alexa_media_player/commit/03bed50ff54b9c1c06612190de8baaf8b8669ab6))

* Merge pull request #857 from custom-components/master

Master ([`0a4eabe`](https://github.com/custom-components/alexa_media_player/commit/0a4eabe766085161a7853fa297ca041cd90af7d6))


## v2.10.1 (2020-07-28)

### Fix

* fix: bump alexapy to 1.12.1
closes #849
closes #850 ([`fccb457`](https://github.com/custom-components/alexa_media_player/commit/fccb45724a50883dbe165596bfbcb0aa9876b71e))

* fix: update deprecated mdi:timer
This requires HA 0.113.0
closes #851 ([`1c31f76`](https://github.com/custom-components/alexa_media_player/commit/1c31f76aae9f8a6ceb7f925079f58f716af53ac5))

### Unknown

* Merge pull request #856 from custom-components/dev

2020-07-27 ([`2c8f3c3`](https://github.com/custom-components/alexa_media_player/commit/2c8f3c3ec085e820597434654d72cb9126b8eed4))

* Merge pull request #855 from alandtse/alexapy1.12.1

fix: bump alexapy to 1.12.1 ([`4ea6dd3`](https://github.com/custom-components/alexa_media_player/commit/4ea6dd32de2c6105a8a81f004b2dfbb30f58cb4a))


## v2.10.0 (2020-07-16)

### Build

* build(deps): bump alexapy to alexapy 1.11.0 ([`ff9828e`](https://github.com/custom-components/alexa_media_player/commit/ff9828eb61f799b77dddeab8b3ad32c2680f7fed))

### Documentation

* docs: add issue tracker link ([`f6fb04e`](https://github.com/custom-components/alexa_media_player/commit/f6fb04e1d9869f8e8bf057ab363f3858275b2615))

### Feature

* feat: add ability to set Echo show background
https://github.com/custom-components/alexa_media_player/wiki#set-echo-show-background-versions--2100 ([`6814b2b`](https://github.com/custom-components/alexa_media_player/commit/6814b2b8bb2e666f995cdba29712b3eee7a53c32))

* feat: add dropin notification support
https://github.com/custom-components/alexa_media_player/wiki/Configuration:-Notification-Component#dropin-notification ([`103be00`](https://github.com/custom-components/alexa_media_player/commit/103be009d4d6f219909747d6f3c08bee3f60f1d7))

### Unknown

* Merge pull request #844 from custom-components/dev

2020-07-15 ([`10af4df`](https://github.com/custom-components/alexa_media_player/commit/10af4dfc8050f0ea98dd8402470012f570a2cf70))

* Merge pull request #843 from alandtse/set_background

feat: add ability to set Echo show background ([`298b92d`](https://github.com/custom-components/alexa_media_player/commit/298b92da21ff55d1331211ed014af452fda72647))

* Merge pull request #841 from alandtse/notification_drop_in

Notification drop in ([`bf8212b`](https://github.com/custom-components/alexa_media_player/commit/bf8212b2443a052ac2140eabdbef955aa0a37fba))

* Merge pull request #834 from custom-components/master

Master ([`864117e`](https://github.com/custom-components/alexa_media_player/commit/864117ecc81eca30adba479df68226f6a5bc67b1))


## v2.9.2 (2020-07-06)

### Fix

* fix: update_coordinator polling on websocket
Polling would get set to scanning_interval on a reconnect and was
not properly updated on websocket_connect. ([`10ceed5`](https://github.com/custom-components/alexa_media_player/commit/10ceed5b4944939d1b97e1954eaa90c7c08b049e))

### Unknown

* Merge pull request #833 from alandtse/#819

fix: update_coordinator polling on websocket ([`41d6ca6`](https://github.com/custom-components/alexa_media_player/commit/41d6ca6a1630187a6a59a449a11b2048e11a6ea9))

* Merge pull request #831 from custom-components/master

Master ([`998668a`](https://github.com/custom-components/alexa_media_player/commit/998668a2e46fb268955b0c0167d733212331ceda))


## v2.9.1 (2020-07-04)

### Fix

* fix: track HA shutdown requests
The component will now distinguish between a HA shutdown where the session
is closed voluntarily versus an error. This will avoid deleting a good
.pickle file forcing a relogin request. This will also prevent attempts
to use the API after a requested close.
closes #819 ([`5b626ae`](https://github.com/custom-components/alexa_media_player/commit/5b626ae5bac4abb7556d87f05bdff05dfed93258))

* fix: provide  timedelta to coordinator
closes #828 ([`7879fd0`](https://github.com/custom-components/alexa_media_player/commit/7879fd07672e8ebdc15ed58c185ca03fe7381d8b))

### Style

* style: address typing errors ([`4411d1a`](https://github.com/custom-components/alexa_media_player/commit/4411d1a95ff5d805d8a454d850ddab1d93d7fdd9))

### Unknown

* Merge pull request #830 from custom-components/dev

2020-07-04 ([`f694f2b`](https://github.com/custom-components/alexa_media_player/commit/f694f2b56733a84254931c7d72c56a18f4d93b89))

* Merge pull request #829 from alandtse/#819

#819 ([`6ce5204`](https://github.com/custom-components/alexa_media_player/commit/6ce5204e9e2c1007c4f7f68b2044eb0173b404e5))

* Merge pull request #824 from custom-components/master

Sync dev with Master ([`ba3c009`](https://github.com/custom-components/alexa_media_player/commit/ba3c009fa3e3838a48b9a77fd02a6ec7d20255c4))


## v2.9.0 (2020-07-03)

### Feature

* feat: add event for relogin required
This should now provide an event `alexa_media_player/relogin_required`
when relogin required. The event_data will contain email/url. ([`79baa40`](https://github.com/custom-components/alexa_media_player/commit/79baa409de7d58afedfe8a4caf85d7da0ae7d40a))

### Fix

* fix: handle ebook which returns no progress info
closes #820 ([`3fde629`](https://github.com/custom-components/alexa_media_player/commit/3fde629a510742f9eca7598422529900eafb7b9b))

* fix: fix availability and assumed_state update ([`1d064a3`](https://github.com/custom-components/alexa_media_player/commit/1d064a34566ad14e288a32f1278cbdd550d9738e))

* fix: add subscriber to allow polling refresh
A dummy callback is used so the datacoordinator will poll ([`c218941`](https://github.com/custom-components/alexa_media_player/commit/c2189419c6a5a370a6423f973b71198109b9e622))

* fix: increase timeout for updating from amazon
closes #764 ([`fbdd2c8`](https://github.com/custom-components/alexa_media_player/commit/fbdd2c884e2dcbc2177f65b0c8b651bb84325430))

### Unknown

* Merge pull request #823 from custom-components/dev

2020-07-02 ([`3411468`](https://github.com/custom-components/alexa_media_player/commit/341146851d4b279b1d3d24b04ae50ebd121423c5))

* Merge pull request #821 from alandtse/event_cookie_expired

Event cookie expired ([`238d04e`](https://github.com/custom-components/alexa_media_player/commit/238d04e9809f91d5fe7a9628d11200a9ff6f5f43))


## v2.8.9 (2020-06-28)

### Ci

* ci: add lokalise download ([`80a4c91`](https://github.com/custom-components/alexa_media_player/commit/80a4c915d49d9c70ff3a5f74fb0ffef67bdcac7b))

### Fix

* fix: bump alexapy to 1.10.7
closes #809
closes #805 ([`4b0162f`](https://github.com/custom-components/alexa_media_player/commit/4b0162f6f0a2e693199264273a14926ec819da9e))

### Unknown

* Merge pull request #817 from custom-components/dev

2020-06-27 ([`13da850`](https://github.com/custom-components/alexa_media_player/commit/13da8509459623d3af986b611ec02c168f1e8b33))

* Delete test

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`e0577ef`](https://github.com/custom-components/alexa_media_player/commit/e0577ef3e696d8293e2b4da3bb6dcc8e1169bfd0))

* Merge pull request #816 from alandtse/lokalise

ci: add lokalise download ([`7291563`](https://github.com/custom-components/alexa_media_player/commit/729156356abc699abe652ff71c3abfc8da42c784))

* Merge pull request #815 from custom-components/test

Create test.yml ([`1fc4d3f`](https://github.com/custom-components/alexa_media_player/commit/1fc4d3f3eae14f7bb5233978801fe31ac1584fed))

* Create test

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`7579eea`](https://github.com/custom-components/alexa_media_player/commit/7579eeab21be0b6ce86a4dd3049fcacb0cc245fc))

* Create test.yml

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`faa733b`](https://github.com/custom-components/alexa_media_player/commit/faa733bc34f55ed2a8301ee6490cb7e357d152f9))

* Merge pull request #814 from custom-components/master

Sync dev to Master ([`d3ad403`](https://github.com/custom-components/alexa_media_player/commit/d3ad403edd619af0a39c1b2d5e5be7bcc02dca97))


## v2.8.8 (2020-06-27)

### Documentation

* docs: add Spanish translation (#804)

Translation to Spanish ([`44a1826`](https://github.com/custom-components/alexa_media_player/commit/44a1826bb3b93bc4e412ee9bc3035a30fdf6d431))

### Fix

* fix: process authentication required page
Amazon has a page that will send a push message and have the user confirm
when complete. This page uses Javascript so the fix may be incomplete.
closes #807 ([`dfb08b0`](https://github.com/custom-components/alexa_media_player/commit/dfb08b0689856ab4fef6f92e1125955912a72532))

### Refactor

* refactor: simplify code logic ([`f397aaa`](https://github.com/custom-components/alexa_media_player/commit/f397aaa1b323a659373bfc9c78b2712e800950ff))

* refactor: remove unnecessary debug ([`b5f81f5`](https://github.com/custom-components/alexa_media_player/commit/b5f81f5f7144fdc74aa8a2159316431d9746ad54))

### Unknown

* Merge pull request #811 from custom-components/dev

2020-06-27 ([`d35860d`](https://github.com/custom-components/alexa_media_player/commit/d35860d34c7656a5b8b3ff627abf8df36f854818))

* Merge pull request #810 from alandtse/javascript_auth_page

Javascript auth page ([`d4ea84d`](https://github.com/custom-components/alexa_media_player/commit/d4ea84d22be6c563866cdec1c2bcf1c5bc6426b4))


## v2.8.7 (2020-06-24)

### Documentation

* docs: update readme and reference translations ([`b48f80d`](https://github.com/custom-components/alexa_media_player/commit/b48f80dc65e15b197a704df10e4144971be127b2))

* docs: add French translation (#789) ([`79a837e`](https://github.com/custom-components/alexa_media_player/commit/79a837e43ce323081d6c20f6c8c9ccc4b4b0e9a0))

### Fix

* fix: bump alexapy to 1.10.5
closes #788
closes #783 ([`f7df9ea`](https://github.com/custom-components/alexa_media_player/commit/f7df9ea71d8ded8178b3f872994f0a1d6f1cf430))

* fix: check for login object changes
This will handle the case where a new login was required and the devices are
using the old login information to connect. This happens when the
cookies expires.
closes #796 ([`b53e292`](https://github.com/custom-components/alexa_media_player/commit/b53e292111b62aecbb49e24d3eb2ab63592a1f36))

### Refactor

* refactor: move check_login_changes to decorator ([`84f2abf`](https://github.com/custom-components/alexa_media_player/commit/84f2abf6d498b1cdd2ce9086e4c5ac9e655bdc4e))

### Style

* style: fix doclint error ([`04fe69d`](https://github.com/custom-components/alexa_media_player/commit/04fe69d0765c199cb41b0f42905746fa4865c598))

### Unknown

* Merge pull request #802 from custom-components/dev

2020-06-23 ([`015f92d`](https://github.com/custom-components/alexa_media_player/commit/015f92dd463f31f7544a44fca85198b132ab493d))

* Merge pull request #801 from alandtse/#796

#796 ([`62a5c1f`](https://github.com/custom-components/alexa_media_player/commit/62a5c1f2d05bf6c1babb0845ec159a67e9e45fd8))

* Merge pull request #798 from alandtse/#796

fix: check for login object changes ([`b4c5f9d`](https://github.com/custom-components/alexa_media_player/commit/b4c5f9ddfebb55afbe626d0c73cb9ffb87e79db6))


## v2.8.6 (2020-06-16)

### Fix

* fix: bump to alexapy 1.10.4 ([`1cc2d75`](https://github.com/custom-components/alexa_media_player/commit/1cc2d75dbfaa59799d8489ffac4998a2aee303b8))


## v2.8.5 (2020-06-16)

### Fix

* fix: bump alexapy to 1.10.3
closes #774
closes #763 ([`ae4e232`](https://github.com/custom-components/alexa_media_player/commit/ae4e232daeccf23bfe604165296db112077a8d69))

* fix: add checks for queue_delay
closes #779 ([`8779b3d`](https://github.com/custom-components/alexa_media_player/commit/8779b3db60b0e0de23b6aef63626e8360d4b39d9))

### Unknown

* Merge pull request #786 from custom-components/dev

2020-06-15 ([`dacbe0e`](https://github.com/custom-components/alexa_media_player/commit/dacbe0ed36136a41ca9b4b358b0d911071d5cf0e))

* Merge pull request #785 from alandtse/#774

fix: bump alexapy to 1.10.3 ([`079bf12`](https://github.com/custom-components/alexa_media_player/commit/079bf128a22a098eb072a852757a20c69b6d8a13))

* Merge pull request #784 from alandtse/#779

#779 ([`145c175`](https://github.com/custom-components/alexa_media_player/commit/145c175adaa19a84798b73385ea3f0cd847f6339))


## v2.8.4 (2020-06-07)

### Fix

* fix: handle CancelledError ([`a5d1d3c`](https://github.com/custom-components/alexa_media_player/commit/a5d1d3c913a78124dfd2881cd6c4173f68e3da63))

* fix: process targets from template
YAML templates will only pass string. This will attempt to process a
target as a potential json and then as a comma separated string.
Closes #761 ([`91095c1`](https://github.com/custom-components/alexa_media_player/commit/91095c122f5f9e5465d104410dbf551ad4a94a5b))

* fix: load notify targets as json
closes #761 ([`59f4842`](https://github.com/custom-components/alexa_media_player/commit/59f4842cea044022a539eac4194cb056d9afcf60))

### Refactor

* refactor: remove extraneous AlexapyLoginError ([`dc87e3c`](https://github.com/custom-components/alexa_media_player/commit/dc87e3cf628aee73e612ffb50760f1e2b1ea527e))

* refactor: use proper get default ([`51718eb`](https://github.com/custom-components/alexa_media_player/commit/51718eb6c21ec3f316c714824691852ad8926c16))

* refactor: remove extraneous raise ([`d99d81c`](https://github.com/custom-components/alexa_media_player/commit/d99d81cd62c3b77639384c83542d769032843aea))

### Unknown

* Merge pull request #769 from custom-components/dev

2020-06-07 ([`e76773b`](https://github.com/custom-components/alexa_media_player/commit/e76773b887e8df58e6d3dac5c7b5b9543fb4d75c))

* Merge pull request #766 from alandtse/#761

fix: load notify targets as json ([`f47f74b`](https://github.com/custom-components/alexa_media_player/commit/f47f74b3b13dcc202fe65cbe6f60ad9e82369642))

* Merge pull request #768 from alandtse/#764

fix: handle CancelledError ([`0b237cd`](https://github.com/custom-components/alexa_media_player/commit/0b237cde549d1192bcb6a4d01600d065c7b6622e))


## v2.8.3 (2020-05-31)

### Fix

* fix: fix test for resetting login for relogin
closes #756 ([`2388345`](https://github.com/custom-components/alexa_media_player/commit/23883451ffe4f8d7225fb2a73a613cbdf17ec8cd))

### Unknown

* Merge pull request #759 from custom-components/dev

 fix: fix test for resetting login for relogin ([`52f30d7`](https://github.com/custom-components/alexa_media_player/commit/52f30d78afada64ff72d123e7bedcf3f265c1524))

* Merge pull request #758 from alandtse/#756

fix: fix test for resetting login for relogin ([`8edbad5`](https://github.com/custom-components/alexa_media_player/commit/8edbad515724680a5f876d64c4062fea10e8ee6b))


## v2.8.2 (2020-05-25)

### Fix

* fix: initialize config_id in configurator
closes #750 ([`ed7c21a`](https://github.com/custom-components/alexa_media_player/commit/ed7c21a665c762805b834f6dca981c41225500d7))

### Unknown

* Merge pull request #752 from custom-components/dev

 fix: initialize config_id in configurator ([`53347d0`](https://github.com/custom-components/alexa_media_player/commit/53347d082489d4e12f73592382eca928aef989dd))

* Merge pull request #751 from alandtse/#750

fix: initialize config_id in configurator ([`1483e65`](https://github.com/custom-components/alexa_media_player/commit/1483e6560b2639c8d937dc7fdb09e1ee2a40e090))


## v2.8.1 (2020-05-24)

### Ci

* ci: remove HACS validation on PR ([`4067ae3`](https://github.com/custom-components/alexa_media_player/commit/4067ae328e9629e10033affb9b1b8a8c7e9ac436))

### Documentation

* docs: fix typo in parameter ([`0321908`](https://github.com/custom-components/alexa_media_player/commit/03219085cfc5a5f1d5c99476dc1198a5ad9590a7))

### Fix

* fix: set prior_value based on prior_value status ([`cf500da`](https://github.com/custom-components/alexa_media_player/commit/cf500da7b73841cca35c1d8dfe76b7d4579ea7f2))

* fix: bump alexapy to 1.10.1 ([`1f2bc03`](https://github.com/custom-components/alexa_media_player/commit/1f2bc0385710cce31ec005b840c4684362356dcf))

* fix: delete bad cookies on failed login
This will reset the session and clear the old cookies. This may be
necessary to avoid a bad login state.
fixes #699 ([`162a572`](https://github.com/custom-components/alexa_media_player/commit/162a572fd1e9ca740d079276a1b9c8d473d50881))

* fix: add checks to avoid updates if session closed ([`ff3c9ed`](https://github.com/custom-components/alexa_media_player/commit/ff3c9ed7804287c3f1f68ca31bd48e5a2e1c5eff))

* fix: handle case where no configurator spawned ([`7b2d666`](https://github.com/custom-components/alexa_media_player/commit/7b2d6662619dc5784936ab0e7da6cd3bfe32e026))

* fix: fix HA warning re deprecated classes
Fixes per https://developers.home-assistant.io/blog/2020/05/14/entity-class-names/
closes #699 ([`db8c055`](https://github.com/custom-components/alexa_media_player/commit/db8c055bee577300fd9c036c6fa08ce3541d8bb9))

### Performance

* perf: remove unnecessary async calls ([`11bd6fa`](https://github.com/custom-components/alexa_media_player/commit/11bd6fa4a7d13998cb245d72761df4d6fc5b4932))

### Refactor

* refactor: relocate constants to const ([`f543d66`](https://github.com/custom-components/alexa_media_player/commit/f543d66afb7e8e338a7322d9184ae785defad356))

* refactor: simplify _show_form ([`dec310d`](https://github.com/custom-components/alexa_media_player/commit/dec310dc44f6a70f39be091cc69cb8afcb2930c8))

### Unknown

* Merge pull request #747 from custom-components/dev

2020-05-23 ([`cb7b40c`](https://github.com/custom-components/alexa_media_player/commit/cb7b40c26fd6e9cdee00782b53722f817299891a))

* Merge pull request #746 from alandtse/#637

fix: set prior_value based on prior_value status ([`bafabcb`](https://github.com/custom-components/alexa_media_player/commit/bafabcb085c5c45f61390f2d76f364b8f6185b15))

* Merge pull request #744 from alandtse/#733

#733 ([`9e5aaef`](https://github.com/custom-components/alexa_media_player/commit/9e5aaefb77a28a6b79263ae40df63225546b0e0b))

* Merge pull request #742 from alandtse/#699

fix: fix HA warning re deprecated classes ([`b522020`](https://github.com/custom-components/alexa_media_player/commit/b522020ce546d30ccdc192d478cc07cb3b0c1416))

* Merge pull request #743 from custom-components/master

Sync dev with master ([`66d3bd4`](https://github.com/custom-components/alexa_media_player/commit/66d3bd4f574d238b29e41efdf11b980f375a4889))


## v2.8.0 (2020-05-19)

### Feature

* feat: add support for canned_tts
Canned TTS must begin with `alexa.cannedtts.speak` using the tts notify
mode. This is discovered using [sequence discovery.
closes #573 ([`89778e3`](https://github.com/custom-components/alexa_media_player/commit/89778e35d3978f2e0c9aac8d8c32e907fd555db7))

* feat: add media_stop command
This is the routine Stop Audio command which should stop all audio
including skills and is queueable. Use with `media_player.media_stop`
closes #692 ([`2bafef8`](https://github.com/custom-components/alexa_media_player/commit/2bafef8d279e799dab23786db925e66748d85fbf))

* feat: add previous_value attrib for notifications
closes #637 ([`2a43ffd`](https://github.com/custom-components/alexa_media_player/commit/2a43ffd57f3a26994704d640218087bdacebe64a))

* feat: add attributes for bluetooth devices
closes #718 ([`6cf69fa`](https://github.com/custom-components/alexa_media_player/commit/6cf69fa8129d9cef4b24e077867f224a4f7a1284))

### Fix

* fix: fix bug for null mainArt
closes #714 ([`5842af1`](https://github.com/custom-components/alexa_media_player/commit/5842af1c5a929e30a851f011f4b454c931e4acef))

### Performance

* perf: convert bluetooth gets to sync ([`b0907ce`](https://github.com/custom-components/alexa_media_player/commit/b0907ceee618790f132f34df3040db19e3fef2fe))

### Unknown

* Merge pull request #732 from custom-components/dev

2020-05-18 ([`205996c`](https://github.com/custom-components/alexa_media_player/commit/205996ccabb24c683e03efa3a960d86641f1f143))

* Merge pull request #722 from alandtse/#714

fix: fix bug for null mainArt ([`d528c93`](https://github.com/custom-components/alexa_media_player/commit/d528c93af184baac7fe4e0bd86234d83581e8e9e))

* Merge pull request #727 from alandtse/#637

feat: add previous_value attrib for notifications ([`3c21722`](https://github.com/custom-components/alexa_media_player/commit/3c2172257c9e5b305ac6fbf7e666407e9ba7b627))

* Merge pull request #731 from alandtse/#573

feat: add support for canned_tts ([`d75ef4f`](https://github.com/custom-components/alexa_media_player/commit/d75ef4fafb4f736c74bfaec72fb020c9b2d8b2f9))

* Merge pull request #729 from alandtse/#692

feat: add media_stop command ([`131a3fb`](https://github.com/custom-components/alexa_media_player/commit/131a3fba0b81cf6cab119df073fa86d1ca553ea8))

* Merge pull request #726 from alandtse/#718

 feat: add attributes for bluetooth devices ([`b74f9f2`](https://github.com/custom-components/alexa_media_player/commit/b74f9f2dd6b886db5d4d2a4b24de6237ced9a519))

* Merge pull request #721 from custom-components/master

Sync dev with master ([`7560637`](https://github.com/custom-components/alexa_media_player/commit/7560637ed3039d72817ba985928879b8c5469d5f))


## v2.7.5 (2020-05-12)

### Fix

* fix: add further session closed checks ([`118f644`](https://github.com/custom-components/alexa_media_player/commit/118f644c34101d38dd3d5e83e376eb4ad156ce46))

### Unknown

* Merge pull request #717 from alandtse/#705

fix: add further session closed checks ([`1101d9a`](https://github.com/custom-components/alexa_media_player/commit/1101d9ac9ef7d0db5c57830f43e0f1789428335b))


## v2.7.4 (2020-05-12)

### Fix

* fix: fix helper login loop ([`7bf4139`](https://github.com/custom-components/alexa_media_player/commit/7bf41398e4133bcd9cc8e74632815687326c0775))

### Unknown

* Merge pull request #715 from alandtse/#705

fix: fix helper login loop ([`579494d`](https://github.com/custom-components/alexa_media_player/commit/579494d2ff6c6cae999dab142467de4708285d63))


## v2.7.3 (2020-05-12)

### Fix

* fix: disable relogin on runtime error ([`6d21212`](https://github.com/custom-components/alexa_media_player/commit/6d212123d8e2137c667517a9be8c8248497ed0a7))

### Unknown

* Merge pull request #713 from alandtse/#705

fix: disable relogin on runtime error ([`dd70deb`](https://github.com/custom-components/alexa_media_player/commit/dd70deba82aa3392a8a32072f32330abc2bb843d))

* Merge pull request #710 from custom-components/master

Sync dev with master ([`450f22f`](https://github.com/custom-components/alexa_media_player/commit/450f22f3e536af101828c1d4255d15a9f147f3c4))


## v2.7.2 (2020-05-12)

### Fix

* fix: bump alexapy to 1.8.4
closes #705 ([`8180d1b`](https://github.com/custom-components/alexa_media_player/commit/8180d1b62f3dce60b76d380fc5efa3e9d4ea5ca3))

* fix: add check for relogin loop ([`5a1fa88`](https://github.com/custom-components/alexa_media_player/commit/5a1fa889582be1b7ca514aaec97e665bbfe489e6))

### Unknown

* Merge pull request #709 from custom-components/dev

2020-05-11 ([`84183f3`](https://github.com/custom-components/alexa_media_player/commit/84183f38a7214f299316e6cc44a7b122e78dc4dc))

* Merge pull request #708 from alandtse/#705

#705 ([`6e8aebf`](https://github.com/custom-components/alexa_media_player/commit/6e8aebf905b0a9261ed1af5c5222e39875cac87e))

* Merge pull request #703 from custom-components/master

Sync dev with master ([`66a2fbe`](https://github.com/custom-components/alexa_media_player/commit/66a2fbeee0849fe9ac3be808bd0ce75558bcc8f7))


## v2.7.1 (2020-05-11)

### Fix

* fix: bump alexapy to 1.8.3
closes #700 ([`6d94adf`](https://github.com/custom-components/alexa_media_player/commit/6d94adf783ab52e203fad899adfa6e7622ec4ce5))

### Unknown

* Merge pull request #702 from custom-components/dev

fix: bump alexapy to 1.8.3 ([`aefd732`](https://github.com/custom-components/alexa_media_player/commit/aefd732ec66a50f3233095d39fd69fd415c2b39f))

* Merge pull request #701 from alandtse/#700

fix: bump alexapy to 1.8.3 ([`7c50883`](https://github.com/custom-components/alexa_media_player/commit/7c508832e327d1e9a823116d71cad197051057c0))


## v2.7.0 (2020-05-08)

### Feature

* feat: triggering a skill with alexa media player

Final code for triggering a skill with alexa media player ([`7aeac34`](https://github.com/custom-components/alexa_media_player/commit/7aeac34c89afc0f91b68a9a241dc709064d4820d))

### Fix

* fix: bump alexapy to 1.8.2
This removes an extraneous volume call to try to fix too many requests.
closes #688 ([`86476e4`](https://github.com/custom-components/alexa_media_player/commit/86476e47aac3ffaaf640a45e14b5f2c703a0f836))

### Unknown

*  feat: add ability to trigger a skill ([`5969e0f`](https://github.com/custom-components/alexa_media_player/commit/5969e0fbf2d6f114fec45f233364a09a2e63f42c))

* Merge pull request #690 from alandtse/#688

fix: bump alexapy to 1.8.2 ([`1e1ded2`](https://github.com/custom-components/alexa_media_player/commit/1e1ded24eb89a7eb5b34cfb7e3ed4551830fb17e))

* bumping to 1.8.1 ([`aec32b8`](https://github.com/custom-components/alexa_media_player/commit/aec32b8997e85c074ddc954e15810888c5f99417))

* add running a skill ([`4b29956`](https://github.com/custom-components/alexa_media_player/commit/4b29956a15f85c365bf968c83116fcb01cd0e982))

* Merge pull request #677 from custom-components/master

Sync dev with master ([`7285188`](https://github.com/custom-components/alexa_media_player/commit/72851880e81d4bbe732e06d91e7eae0006859dc5))


## v2.6.1 (2020-05-02)

### Fix

* fix(notify): fix use of wrong email variable
closes #674 ([`5d030c0`](https://github.com/custom-components/alexa_media_player/commit/5d030c021d4fe8cac0f32225604301964be41a36))

### Unknown

* Merge pull request #676 from alandtse/#674

fix(notify): fix use of wrong email variable ([`321a259`](https://github.com/custom-components/alexa_media_player/commit/321a259ff9faf43067ce96c1955fa5c6c41d7be9))


## v2.6.0 (2020-05-02)

### Ci

* ci: update debug flag for semantic-release ([`f523a72`](https://github.com/custom-components/alexa_media_player/commit/f523a721380c27699030f3f04427487506597a84))

* ci: update hacs validate name ([`7b017f6`](https://github.com/custom-components/alexa_media_player/commit/7b017f6c91c8298790abb01ea4e2e82d0c98d99b))

* ci: add hacs validation ([`62ea87b`](https://github.com/custom-components/alexa_media_player/commit/62ea87b4be67b2c085772c08065396cbf1e899de))

### Feature

* feat: add option for queue_delay
Queue delay controls how long each command will wait to queue up other
commands. This will help reduce too many requests errors but will delay
running the command. The default is 1.5 seconds. 0 seconds will result in no
queuing behavior. ([`1e8881c`](https://github.com/custom-components/alexa_media_player/commit/1e8881cfebf561dc4954d11f9a4003977936d380))

### Fix

* fix: bump alexapy to 1.7.1
closes #568
closes #670 ([`63de6ef`](https://github.com/custom-components/alexa_media_player/commit/63de6ef2f27f950a4fa26c8460e9870845e0e470))

* fix: fix configuration.yaml import code
The import will now search config entries by data values instead of by title which
can be change in HA 109. The code also properly creates a new entry
after failing a search.
closes #665 ([`fc6b97e`](https://github.com/custom-components/alexa_media_player/commit/fc6b97eba0e21a13de4f1b08a653387a952f79ac))

### Unknown

* Merge pull request #673 from custom-components/dev

2020-05-02 ([`e42a7cd`](https://github.com/custom-components/alexa_media_player/commit/e42a7cd5f5d2b26c95b12215409995bd0ff49601))

* Merge pull request #668 from alandtse/#665

fix: fix configuration.yaml import code ([`bf12b3f`](https://github.com/custom-components/alexa_media_player/commit/bf12b3f5ce23be378164f9c212f1c54d812bb559))

* Merge pull request #672 from alandtse/#568

fix: bump alexapy to 1.7.1 ([`0caa815`](https://github.com/custom-components/alexa_media_player/commit/0caa81569b7e4e69746ac3f34b35f692a32dc3c7))

* Revert &#34;ci: update debug flag for semantic-release&#34;

This reverts commit f523a721380c27699030f3f04427487506597a84. ([`6ead6d8`](https://github.com/custom-components/alexa_media_player/commit/6ead6d823bccbce9d7f9089151cfa0f43b7cea42))

* Merge pull request #669 from custom-components/master

Sync dev with master ([`042586b`](https://github.com/custom-components/alexa_media_player/commit/042586b1982efd68b97bb0d4023094f7188083ae))

* Merge pull request #662 from alandtse/options

feat: add option for queue_delay ([`1700397`](https://github.com/custom-components/alexa_media_player/commit/17003977a96d9a1f3a80fb0ddf90a1d0990e73fd))

*  docs: switch to smaller hacs badge ([`55d4941`](https://github.com/custom-components/alexa_media_player/commit/55d4941703af586c15e39ce6272bb07898738770))


## v2.5.15 (2020-04-23)

### Fix

* fix: change to numerical input for claimspicker ([`529896c`](https://github.com/custom-components/alexa_media_player/commit/529896cbe8cf3282f733f09a06440a16c22f6d44))

* fix: future proof translation directory for HA 111 ([`5e9cd1a`](https://github.com/custom-components/alexa_media_player/commit/5e9cd1a494420c4e5e1214a27bc5d97eb7fe8419))

* fix: catch missing key for switches dictionary
closes #657 ([`b01e42f`](https://github.com/custom-components/alexa_media_player/commit/b01e42f06d7762f99eef3f6c584d0e4489c14832))

### Style

* style: remove unnecessary parantheses ([`51f3979`](https://github.com/custom-components/alexa_media_player/commit/51f39799729aae20bff896287bf278992e20c325))

### Unknown

* Merge pull request #661 from custom-components/dev

2020-04-22 ([`17e910b`](https://github.com/custom-components/alexa_media_player/commit/17e910b1b656c4c0fb05652bf0ca5b031ce8d09a))

* Merge pull request #660 from alandtse/numerical_claimspicker

fix: change to numerical input for claimspicker ([`854e29a`](https://github.com/custom-components/alexa_media_player/commit/854e29a76870d0277a6bbbc9217050f3075e214e))

* Merge pull request #659 from alandtse/#657

fix: catch missing key for switches dictionary ([`9d2e891`](https://github.com/custom-components/alexa_media_player/commit/9d2e891a92095b3fb14a2347b6f0c745470e8757))

* Merge pull request #658 from custom-components/master

Sync dev with master ([`57bced2`](https://github.com/custom-components/alexa_media_player/commit/57bced25c6648c488a64bad82c039f8e22b24eec))


## v2.5.14 (2020-04-20)

### Ci

* ci: add recommended lint for HA

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`e1dcbbb`](https://github.com/custom-components/alexa_media_player/commit/e1dcbbbb40659d588af5f1a147a73aa4234539c9))

### Documentation

* docs: add hacs badge ([`88ee4ad`](https://github.com/custom-components/alexa_media_player/commit/88ee4ad01775ee96b1efb131e3a7a036adfa5e43))

* docs: Add debugging to show config import ([`497b132`](https://github.com/custom-components/alexa_media_player/commit/497b13256831d3b9318c0b0fa51ddeb0fca9d85c))

* docs: update readme with badges ([`687dc54`](https://github.com/custom-components/alexa_media_player/commit/687dc5442510e530f01e6bab2f817cb607b1f1dc))

### Fix

* fix: switch to queueable set_guard_state
This will use the same command as the Alexa app&#39;s routine. ([`e7d5f04`](https://github.com/custom-components/alexa_media_player/commit/e7d5f0458113f5b167e35b5d227f585da9c57a9f))

* fix: stagger loading of components ([`0ddda71`](https://github.com/custom-components/alexa_media_player/commit/0ddda71c3cac266750cbe05f2f65dab15240f99b))

* fix: add checks for configurator use ([`75faa7f`](https://github.com/custom-components/alexa_media_player/commit/75faa7f2f71fe045ede1c50295df0a50179e12c0))

* fix: remove redudant alexa_setup ([`e0a29ab`](https://github.com/custom-components/alexa_media_player/commit/e0a29ab0af0d68a9fd98b47b793c382f2e146fd9))

* fix: fix json syntax error ([`edb9fff`](https://github.com/custom-components/alexa_media_player/commit/edb9fff67c06d4c24d02b34194788801ac4a1772))

* fix: fix hassfest lint issues ([`511a1a2`](https://github.com/custom-components/alexa_media_player/commit/511a1a2087618add1d7ddc8f8d7eb97fe90375f1))

### Refactor

* refactor: change to dispatcher instead of bus ([`94cd97b`](https://github.com/custom-components/alexa_media_player/commit/94cd97ba4f87cb3fcbd4a6ea4579ead149c02b9a))

* refactor: migrate to DataUpdateCoordinator ([`1873a19`](https://github.com/custom-components/alexa_media_player/commit/1873a1974452bcb9178f7ab707f2b2c9c088b64b))

### Style

* style: remove unused code ([`0b077ec`](https://github.com/custom-components/alexa_media_player/commit/0b077ec77182cbab313cdd06ee933f0ee015ac29))

### Unknown

* Merge pull request #654 from custom-components/dev

2.5.14 ([`268366a`](https://github.com/custom-components/alexa_media_player/commit/268366a1f50cf53b4ad0f9d68acc70dab8f5a54b))

* Merge pull request #652 from alandtse/data_coordinator

Data coordinator ([`ce69151`](https://github.com/custom-components/alexa_media_player/commit/ce691511e5c026b735bf6961c5de9b5ba244be81))

* Merge pull request #653 from custom-components/master

Sync dev with master ([`d176f97`](https://github.com/custom-components/alexa_media_player/commit/d176f97c8c4feca34c8286b02f45ff9e73c4358a))


## v2.5.13 (2020-04-11)

### Documentation

* docs: update wiki links ([`b238def`](https://github.com/custom-components/alexa_media_player/commit/b238def65d772ce6442e365d323b8d36718c6d13))

### Fix

* fix: add additional checks to notifications setup
This is to address changes to Alexa&#39;s API and the retirement of keys.
Closes #641 ([`565ab66`](https://github.com/custom-components/alexa_media_player/commit/565ab666c34180970d726708edbcd7c3bc6e11d0))

### Unknown

* Merge pull request #644 from custom-components/dev

2.5.13 ([`ca56c8f`](https://github.com/custom-components/alexa_media_player/commit/ca56c8f391b283df06accff94454c5010ceb1b66))

* Merge pull request #643 from alandtse/#641

fix: add additional checks to notifications setup ([`423deb2`](https://github.com/custom-components/alexa_media_player/commit/423deb22fc3ae88c2523b7b1de00b68e9dba9b67))

* Merge pull request #640 from custom-components/master

Sync dev with master ([`6d7d8ec`](https://github.com/custom-components/alexa_media_player/commit/6d7d8ec16b747b10e362e89f5145e39dfa9d1ab2))

* Merge pull request #639 from alandtse/fix_wiki_links

docs: update wiki links ([`5a3af9a`](https://github.com/custom-components/alexa_media_player/commit/5a3af9a82d897ce1ce1f33f091f8187833cf2bef))


## v2.5.12 (2020-04-08)

### Fix

* fix: ignore unassociated notifications ([`e0233e5`](https://github.com/custom-components/alexa_media_player/commit/e0233e56fe7fef3e8a4981f686d67a675cbc4c33))

* fix: handle exception for recurringPattern
Alexa notifications API only uses recurringPattern when set. ([`1dfb3be`](https://github.com/custom-components/alexa_media_player/commit/1dfb3be28c9d72786800543080adcd878ac552c2))

* fix: handle exception on originalDate/originalTime
Alexa notifications API no longer returns originalDate or originalTime
for timers.
closes #633 ([`e47274c`](https://github.com/custom-components/alexa_media_player/commit/e47274ce2b74c4fa2895595c3ee3d63116b79b1d))

### Unknown

* Merge pull request #636 from custom-components/dev

2.5.12 ([`ff2c73b`](https://github.com/custom-components/alexa_media_player/commit/ff2c73b84450b021fb40fa7138a5ebec4322ab99))

* Merge pull request #634 from alandtse/#633

fix: address changes to notifications api ([`ebf2a51`](https://github.com/custom-components/alexa_media_player/commit/ebf2a512af1a0fa446c421a65e14078afcbb876a))

* Merge pull request #624 from custom-components/master

Sync dev to master ([`31908ee`](https://github.com/custom-components/alexa_media_player/commit/31908eebfe3081ce57e8eb9cc3b85cb58fbc4216))


## v2.5.11 (2020-04-02)

### Fix

* fix: force refresh on active media players on push
Certain push activities will clear the media state so must be checked.
closes #617 ([`3556360`](https://github.com/custom-components/alexa_media_player/commit/35563606725c7ed822ca978ec36a0e7af1fdb355))

### Unknown

* Merge pull request #623 from custom-components/dev

2.5.11 ([`851ab7c`](https://github.com/custom-components/alexa_media_player/commit/851ab7c8030794dc206af17701f6f78bc6606bae))

* Merge pull request #622 from alandtse/#617

fix: force refresh on active media players on push ([`97ac148`](https://github.com/custom-components/alexa_media_player/commit/97ac148abb068fbb3935ff01bbc6e035dcbd53bc))

* Merge pull request #620 from custom-components/master

Sync dev to master ([`af48de6`](https://github.com/custom-components/alexa_media_player/commit/af48de66497987e530fc28509e006fd023ceddb7))


## v2.5.10 (2020-03-30)

### Fix

* fix: fix overwrite of websocket error ([`71173b8`](https://github.com/custom-components/alexa_media_player/commit/71173b8de0e1fb19742cc2517727eae4161377e1))

### Unknown

* Merge pull request #619 from custom-components/dev

fix: handle websocket eofstream errors ([`6db8590`](https://github.com/custom-components/alexa_media_player/commit/6db85905816f65511f0314f9183cf048d7def44c))

* Merge pull request #605 from alandtse/#579

fix: abort websocket connections on EofStream ([`9784399`](https://github.com/custom-components/alexa_media_player/commit/9784399aaaea91ab05b4f0d8efbbd07d83f48811))


## v2.5.9 (2020-03-30)

### Fix

* fix: update check for number of websocket errors
Because the error counter can be changed asynchronously, the local
variable needs to be refreshed after regaining control. ([`bc2677d`](https://github.com/custom-components/alexa_media_player/commit/bc2677d34cefec15d881e28aa65a2fd33d520619))

* fix: abort websocket on eofstream error ([`6107134`](https://github.com/custom-components/alexa_media_player/commit/610713484bfd50bf91934130515de37563543a56))

* fix: fix malformed input bug for entry 0 ([`166c0de`](https://github.com/custom-components/alexa_media_player/commit/166c0de1e1bd1336584363971b4e1a705d3c2a03))

* fix: handle recurring reminders
fixes #602 ([`9241a07`](https://github.com/custom-components/alexa_media_player/commit/9241a075823d8eafe4a58fb22ac14b6f6718bba1))

### Style

* style: black ([`034e91d`](https://github.com/custom-components/alexa_media_player/commit/034e91d44f8d7ef9627ed46f679968a7320ad974))

* style: rename sensor class ([`752007a`](https://github.com/custom-components/alexa_media_player/commit/752007a458f211bd2ff1de0916d82b183df4bf32))

### Unknown

* Merge pull request #618 from custom-components/dev

fix: handle recurring reminders ([`3d38b3e`](https://github.com/custom-components/alexa_media_player/commit/3d38b3e755fd0b69ee815a25573c17a1fb979166))

* Merge pull request #603 from alandtse/#602

fix: handle recurring reminders ([`76f7823`](https://github.com/custom-components/alexa_media_player/commit/76f7823a1bd6810670bf6176ef5da61a3cf9f1d7))

* Merge pull request #604 from custom-components/master

Sync dev with master ([`6ac1dd0`](https://github.com/custom-components/alexa_media_player/commit/6ac1dd06f8f1cac28bee0bf17e0e648e471133b2))


## v2.5.8 (2020-03-22)

### Fix

* fix: fix handling of weekly recurringPattern alarm
Change RECURRING_PATTERN_ISO_SET to dict and also prevent unnecessary
loops if alarm is off.
fixes #596 ([`88ea37a`](https://github.com/custom-components/alexa_media_player/commit/88ea37a78d59733e1fe6928dfc2083757aea2bf1))

### Unknown

* Merge pull request #601 from custom-components/dev

2.5.8 ([`6f38427`](https://github.com/custom-components/alexa_media_player/commit/6f3842727284c63e8f6eaa1e7f56dcee40638d64))

* Merge pull request #600 from alandtse/#596

fix: fix handling of weekly recurringPattern alarm ([`cd06c5f`](https://github.com/custom-components/alexa_media_player/commit/cd06c5f8f99e554781f04a9fe09a27690bfeaff8))

* Merge pull request #599 from custom-components/master

Sync dev with master ([`965b4f0`](https://github.com/custom-components/alexa_media_player/commit/965b4f0d5091c5a29755a2e1299986dd9652cb4a))


## v2.5.7 (2020-03-21)

### Ci

* ci: disable upload_to_release

This currently requires a setup.py to create the /dist content which breaks for alexa_media.
Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`5b07987`](https://github.com/custom-components/alexa_media_player/commit/5b079875e62ee4ec7efefc178d9698f4a3d5b04c))

### Documentation

* docs: update feature request form ([`11f6c34`](https://github.com/custom-components/alexa_media_player/commit/11f6c341deea0e3ef3ebb773f0f5339e581076ac))

### Fix

* fix: bump alexapy to 1.5.2
closes #587
closes #586
closes #544 ([`a72571c`](https://github.com/custom-components/alexa_media_player/commit/a72571cdc50580c4c5d32d1b3f1bc58cd6e2e127))

* fix: fix next timer for recurrence alarms
The Alexa API apparently does not change the timer date but instead
relies on the client app to figure out the next alarm based on the
recurrence pattern. This adds that logic.
fixes #566 ([`605e168`](https://github.com/custom-components/alexa_media_player/commit/605e168fc4607dce4fe5c0b16107b6ab122c569a))

* fix: quote pandora media urls
closes #582 ([`2ff9e9a`](https://github.com/custom-components/alexa_media_player/commit/2ff9e9a25320caba3c1d82e087b8ce42dd5a4826))

### Unknown

* Merge pull request #595 from custom-components/dev

2.5.7 ([`0434e79`](https://github.com/custom-components/alexa_media_player/commit/0434e7909e3ff33a5394fd5d2aecd2a21d2b2d33))

* Merge pull request #594 from alandtse/alexapy1.5.2

fix: bump alexapy to 1.5.2 ([`d14510f`](https://github.com/custom-components/alexa_media_player/commit/d14510f6a062e1420345024594b9591dbd880dd7))

* Merge pull request #591 from alandtse/#566

fix: fix next timer for recurrence alarms ([`6241466`](https://github.com/custom-components/alexa_media_player/commit/6241466c54af3c23e949e39e67321b6371b682c1))

* Merge pull request #590 from custom-components/master

docs: update feature request form ([`0d2c72b`](https://github.com/custom-components/alexa_media_player/commit/0d2c72b45474ba8bcab541eb764921af510f544c))

* Merge pull request #589 from alandtse/#582

fix: quote pandora media urls ([`30da4be`](https://github.com/custom-components/alexa_media_player/commit/30da4bea472316b613d7eb29ca435b816cd12315))

* Merge pull request #578 from custom-components/master

Sync dev to master ([`ab34e44`](https://github.com/custom-components/alexa_media_player/commit/ab34e44775cd6b578956ce5613ec023d8d76f550))


## v2.5.6 (2020-03-01)

### Fix

* fix: bump alexapy to 1.5.1
closes #572 ([`adc5aeb`](https://github.com/custom-components/alexa_media_player/commit/adc5aebe48fb5f9554998403089fb63c264c98d0))

### Unknown

* Merge pull request #577 from custom-components/dev

v2.5.6 ([`0938c01`](https://github.com/custom-components/alexa_media_player/commit/0938c017e92b906055ea329b46e0bda8ddd87a03))

* Merge pull request #576 from alandtse/#572

fix: bump alexapy to 1.5.1 ([`52cad49`](https://github.com/custom-components/alexa_media_player/commit/52cad49bfdfd3d923f817f9cd559a6e5340250b5))

* Merge pull request #575 from custom-components/master

Sync dev with master ([`5aaa10e`](https://github.com/custom-components/alexa_media_player/commit/5aaa10e3649cc25b3f2be6190f37eed297e6224e))


## v2.5.5 (2020-02-18)

### Documentation

* docs: simplify readme ([`f676828`](https://github.com/custom-components/alexa_media_player/commit/f6768283bfc6ce3243b88e9a584ec350b4e87a1b))

### Fix

* fix: bump alexapy to 1.5.0 ([`d7155bb`](https://github.com/custom-components/alexa_media_player/commit/d7155bba404577c4cbfa210e32412059f1850193))

* fix: ignore PUSH_CONTENT_FOCUS_CHANGE
closes #536 ([`48cfc2c`](https://github.com/custom-components/alexa_media_player/commit/48cfc2c947cbea25f7534b1e3a80c79f12be77f9))

* fix: allow passing of kwargs for async_send_tts ([`1dc1e77`](https://github.com/custom-components/alexa_media_player/commit/1dc1e773bf407201eb523137501545f1fb532429))

* fix: load found devices when load delay required
fixes #552 ([`0157ebe`](https://github.com/custom-components/alexa_media_player/commit/0157ebeeef3c36dd23cc14b02347e00fe4ab2106))

### Performance

* perf: use asyncio.gather instead of for loop ([`9218756`](https://github.com/custom-components/alexa_media_player/commit/9218756f6e0c553cdb11ce4cbfd27addeef02005))

* perf: change convert to sync ([`a55d309`](https://github.com/custom-components/alexa_media_player/commit/a55d3099d2c4606992e41b2ee546994d561a1c5b))

### Unknown

* Merge pull request #565 from custom-components/dev

2.5.5 ([`1588ee5`](https://github.com/custom-components/alexa_media_player/commit/1588ee5a3dee6edad83c68e9cae0a07e2f23f2c0))

* Merge pull request #564 from alandtse/#551

fix: allow tts requests to be sent in parallel ([`135b04f`](https://github.com/custom-components/alexa_media_player/commit/135b04f8913ccfb09ec00c33d6ce3cb3e95b7257))

* Merge pull request #563 from alandtse/#536

fix: ignore PUSH_CONTENT_FOCUS_CHANGE ([`3f585d2`](https://github.com/custom-components/alexa_media_player/commit/3f585d262acd5662d63f7efa5a38f7f51b0f4446))

* Merge pull request #559 from alandtse/#552

fix: load found devices when load delay required ([`c7f9cd0`](https://github.com/custom-components/alexa_media_player/commit/c7f9cd0e371babc64b8aad6e50e719177a7bb834))

* Merge pull request #558 from custom-components/master

Sync dev with master ([`ee6be08`](https://github.com/custom-components/alexa_media_player/commit/ee6be08e727aad3b0846fad73a5f9342821d6164))


## v2.5.4 (2020-01-24)

### Fix

* fix: properly localize timers ([`b6fbdff`](https://github.com/custom-components/alexa_media_player/commit/b6fbdff471eb65b0869de751d8fd987c76948efe))

### Refactor

* refactor: add warning about old alarm format ([`4e284a3`](https://github.com/custom-components/alexa_media_player/commit/4e284a300922abee5a6914cdba0e844b160c47e7))

### Unknown

* Merge pull request #542 from custom-components/dev

fix: fix localization of timers ([`5c4a9fc`](https://github.com/custom-components/alexa_media_player/commit/5c4a9fc34bbdf13c96f4bf2f050ea62d5c60da5e))

* Merge pull request #541 from alandtse/#530

fix: fix localization of timers ([`0b7cbc2`](https://github.com/custom-components/alexa_media_player/commit/0b7cbc2ca72a44fddabfc318d98192f9c27c74af))

* Merge pull request #539 from custom-components/master

Sync dev with master ([`013edfa`](https://github.com/custom-components/alexa_media_player/commit/013edfa72052c39556ef75c1aee477fb2d91c3f0))


## v2.5.3 (2020-01-22)

### Fix

* fix: fix timer drifting ([`37c8f68`](https://github.com/custom-components/alexa_media_player/commit/37c8f6891c23b92b5bd958da5d54a4bf43e09cb9))

* fix: address push for shopping list changes
Closes #534 ([`3325fa1`](https://github.com/custom-components/alexa_media_player/commit/3325fa1a16996cf468688ffa1380f21296eac6a8))

* fix: handle older alarm format
Amazon previously used alarmTime to store alarms but now sets it to 0.
Add logic to try new format first and then old format.
Closes #530 ([`a88c746`](https://github.com/custom-components/alexa_media_player/commit/a88c746a5d11e350152730d46658e0cccfc490e4))

* fix: round timers and reminders to nearest second ([`1671c8b`](https://github.com/custom-components/alexa_media_player/commit/1671c8b625659aa880d2847f2bf7f9a3ba39906d))

* fix: fix function documentation ([`d3538f2`](https://github.com/custom-components/alexa_media_player/commit/d3538f2b9776c13cb88117c8e7c40dbc3d5b0d47))

* fix: hide entities from UI ([`d290039`](https://github.com/custom-components/alexa_media_player/commit/d290039fbd43cc601325225a1db2f91e9fa8c618))

* fix(switch): add device_class ([`016c22e`](https://github.com/custom-components/alexa_media_player/commit/016c22e52cd66ead661c680eae008de352b0eb4c))

* fix: avoid creation of unusable switches
Users will need to remove orphaned entities from HA ([`cd27bb9`](https://github.com/custom-components/alexa_media_player/commit/cd27bb975d982f0212c9f5c4551c0b76b8fa83c9))

* fix: enable DND updates on proper websocket ([`16e4b2c`](https://github.com/custom-components/alexa_media_player/commit/16e4b2ca96c7a7a72992ad2780475bd6715398db))

* fix: enable polling on update_devices changes
This will propagate changes from the centralized polling to individual
media players.
Closes #529 ([`dfe07f2`](https://github.com/custom-components/alexa_media_player/commit/dfe07f201f3c578e1666f91f8facf1e4a08e6b14))

* fix: address PUSH_DELETE_DOPPLER_ACTIVITIES
This is a command to delete recordings from Alexa.
Closes #527 ([`8788ff3`](https://github.com/custom-components/alexa_media_player/commit/8788ff3669ea0f6f8ca37fe2ab1edfd999802b47))

### Refactor

* refactor: remove use of _device json
To avoid duplication of state the device json will not be saved within
the class. The device json is only used as an blanket input. ([`3b14325`](https://github.com/custom-components/alexa_media_player/commit/3b14325e37907f11a84725720ed6efe90bf5def8))

* refactor: improve readability of code ([`bc1c0c9`](https://github.com/custom-components/alexa_media_player/commit/bc1c0c9e2fd97a653284f36fd03eea5a70d43bbf))

### Unknown

* Merge pull request #538 from custom-components/dev

2.5.3 ([`2b015ce`](https://github.com/custom-components/alexa_media_player/commit/2b015ce81436256157acc77d5a7970aecf0ea72a))

* Merge pull request #535 from alandtse/#530

fix: handle older alarm format and round timers to nearest second ([`fd240fc`](https://github.com/custom-components/alexa_media_player/commit/fd240fc94e0fae97c49d763e68931210d31ec3ae))

* Merge pull request #532 from alandtse/#529

fix: enable polling on update_devices changes ([`3c92842`](https://github.com/custom-components/alexa_media_player/commit/3c92842b38ef1bea18f7f005726713467e73fd8a))

* Merge pull request #537 from alandtse/#534

fix: address push for shopping list changes ([`3c9bd2f`](https://github.com/custom-components/alexa_media_player/commit/3c9bd2f4d47075fd5d52e87b7bd8e648ca62e228))

* Merge pull request #528 from alandtse/#527

fix: address PUSH_DELETE_DOPPLER_ACTIVITIES ([`31db58f`](https://github.com/custom-components/alexa_media_player/commit/31db58ff0aa1e82286f3c59506699d0f8d30b2dc))

* Merge pull request #525 from custom-components/master

Sync dev to master ([`5e175dc`](https://github.com/custom-components/alexa_media_player/commit/5e175dcc0e432e38583c0ed0b61ee32505471ffa))


## v2.5.2 (2020-01-17)

### Ci

* ci: add delay to upload ([`6a2f6ef`](https://github.com/custom-components/alexa_media_player/commit/6a2f6efc04ceb818075cba7d7db4f96600fab569))

### Fix

* fix(media_player): fix last_called not set false
Closes #516 ([`4703697`](https://github.com/custom-components/alexa_media_player/commit/47036970e4d36b3a505139f6daac75b87e23a387))

### Unknown

* Merge pull request #524 from alandtse/ci_work

fix(media_player): fix last_called not set false ([`8d46c26`](https://github.com/custom-components/alexa_media_player/commit/8d46c26b7358ab4bf2eff22658ec257c290893e3))

* Merge pull request #523 from alandtse/ci_work

ci: add delay to upload ([`4e5f35a`](https://github.com/custom-components/alexa_media_player/commit/4e5f35a9b7b4935fbd0e455b603bff880f0ad0f1))

* Merge pull request #522 from custom-components/master

Sync dev with master ([`38476d2`](https://github.com/custom-components/alexa_media_player/commit/38476d22c1ef815aa902225910a96bb85e74d033))


## v2.5.1 (2020-01-16)

### Ci

* ci: fix syntax for real

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`ed0d9b9`](https://github.com/custom-components/alexa_media_player/commit/ed0d9b94043c947eb080f5233cc92d526f092fd2))

* ci: fix release variable syntax

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`e10ff3b`](https://github.com/custom-components/alexa_media_player/commit/e10ff3bc2215477104ccc9ab36c2a144d6c05983))

* ci: add release variable

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`f1c6027`](https://github.com/custom-components/alexa_media_player/commit/f1c60270b78a8f1ab5f20de9fb3d39ab7b827496))

* ci: fix directory

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`093f8a3`](https://github.com/custom-components/alexa_media_player/commit/093f8a39b5478c413142781a2302d09f2941fd92))

* ci: add zip to release

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`a29c20e`](https://github.com/custom-components/alexa_media_player/commit/a29c20eccfc3267c6f0b9401dd492ba9108c838c))

### Fix

* fix: bump to alexapy 1.4.2
Closes #512 ([`cd9c199`](https://github.com/custom-components/alexa_media_player/commit/cd9c1996706b89c37f0f467987c2abf033af7df7))

* fix: fix unload of notify ([`ca49772`](https://github.com/custom-components/alexa_media_player/commit/ca497728d2fade8fe72f975a370ceaa79a33ed87))

### Unknown

* Merge pull request #520 from custom-components/dev

fix: address issues with 2.5.0 ([`d9ce7ba`](https://github.com/custom-components/alexa_media_player/commit/d9ce7ba1ffb76df786c5a09d2d5204ed5c156b8e))

* Merge pull request #519 from alandtse/#513

fix: bump to alexapy 1.4.2 ([`4615b87`](https://github.com/custom-components/alexa_media_player/commit/4615b87cd225d6b121703462fde6815b403e4876))

* Merge pull request #518 from custom-components/master

Sync dev with master ([`9724cc7`](https://github.com/custom-components/alexa_media_player/commit/9724cc7f74cb5a848eb189cda0f7ceaadf714e8a))

* Merge pull request #517 from custom-components/ludeeus-patch-2

Fix HACS installation/update with zip_release ([`a158b6f`](https://github.com/custom-components/alexa_media_player/commit/a158b6f3b70d05708ff35734b698a25b4f957e3c))

* Fix HACS installation/update with zip_release ([`e00f997`](https://github.com/custom-components/alexa_media_player/commit/e00f99732df6f308163e5431c2181c2e3ca0872b))


## v2.5.0 (2020-01-15)

### Feature

* feat(media_player): expose last_called time stamp ([`99cd21a`](https://github.com/custom-components/alexa_media_player/commit/99cd21a3dea5586b54a1b9260f0dcd4e0827dda3))

### Fix

* fix: bump alexapy to 1.4.1
Closes #454 ([`bcd8bb5`](https://github.com/custom-components/alexa_media_player/commit/bcd8bb59a70896c32d90d47227d857296d4b98f9))

* fix(media_player): fix clearing of data on state change
This increases the delay before a refresh of player state based on
change detection. This also agressively clears player data if Amazon
ever returns null data.
Closes #475 ([`4f05988`](https://github.com/custom-components/alexa_media_player/commit/4f059880ee8a39c1af9c38af3891e4a65a3494db))

* fix: enable detection of offline devices
This enables a slow poll even if websocket is enabled. Detection is
still determined by when Amazon notices a device goes offline which can take
up to half an hour in testing.
Closes #443 ([`3bd8045`](https://github.com/custom-components/alexa_media_player/commit/3bd804580343f5329cf90745bad32da74c9f7573))

* fix(media_player): fix refresh handling based on websocket commands ([`f795e78`](https://github.com/custom-components/alexa_media_player/commit/f795e782b86cb5de7a6768855e0441a377db4333))

* fix(media_player): allow volume set regardless of play_state ([`1ff35cf`](https://github.com/custom-components/alexa_media_player/commit/1ff35cfc137ec424c5c9d5799c825489a7a30e8c))

* fix(media_player): set proper last_update on init ([`69e7d80`](https://github.com/custom-components/alexa_media_player/commit/69e7d804e192ac865f68c6121125c82c0a6078f1))

* fix(media_player): fix repeat update ([`658773d`](https://github.com/custom-components/alexa_media_player/commit/658773d985e2f307cf86d9a84a5919cbef0e577c))

* fix(media_player): fix shuffle state update ([`26b1966`](https://github.com/custom-components/alexa_media_player/commit/26b19664d4c8a9f56c3deae22a5b56560a3a6246))

* fix(media_player): fix early refresh on play_state
This adds a slight delay to refresh play state so Amazon servers have
to update. ([`15e58d1`](https://github.com/custom-components/alexa_media_player/commit/15e58d123f8eae1a437b5898a02f6ad46e926089))

* fix(sensor): check for AttributeError timezone
Closes #501 ([`84b4c61`](https://github.com/custom-components/alexa_media_player/commit/84b4c61a36710bff6bb38cfe12416995f441ee10))

* fix: fix bluetooth discovery logs ([`804e1c2`](https://github.com/custom-components/alexa_media_player/commit/804e1c28aaeda3c9f94234e1d1fe522562acac92))

* fix(alarm): force state update on init
This fixes the unknown state on startup. ([`499f8ed`](https://github.com/custom-components/alexa_media_player/commit/499f8edeb242ff99b5cb4e8e446bfa1f1f5dddeb))

* fix(media_player): fix WHA where volume null ([`330895c`](https://github.com/custom-components/alexa_media_player/commit/330895c639d8bbf9b70adfe60f218bd5345ae33d))

* fix(media_player): fix offline child ([`41c9ba4`](https://github.com/custom-components/alexa_media_player/commit/41c9ba45dd505a591770e7bada1de82d8c4e8ad2))

* fix(media_player): fix refresh of WHA children
Change the var trigger for children refreshing to be isPlayingInLemur ([`e0f7df1`](https://github.com/custom-components/alexa_media_player/commit/e0f7df15421bf80e8b0b1f484bec885e0f477d7f))

### Performance

* perf: only update auth on new_devices ([`37cafaf`](https://github.com/custom-components/alexa_media_player/commit/37cafaf7fe7f32a7e9826bc40adcf66c865b3a3a))

* perf(media_player): stop unnecessary event processing ([`6c8d52e`](https://github.com/custom-components/alexa_media_player/commit/6c8d52e375b365afa3738f61e19f00db17d83cd3))

* perf: add break to for loops once item discovered ([`82f8af2`](https://github.com/custom-components/alexa_media_player/commit/82f8af2fa2dca4ed656452e080c1e08421ff1fdb))

### Refactor

* refactor: track last ws_activity ([`cca517a`](https://github.com/custom-components/alexa_media_player/commit/cca517a7ebce3570ec093488a7d405d0543baa4f))

* refactor: address linting errors ([`899695d`](https://github.com/custom-components/alexa_media_player/commit/899695df37634da51445cc5399ffd3dac7d96f84))

* refactor(media_player): clean up logging ([`3c459ca`](https://github.com/custom-components/alexa_media_player/commit/3c459ca42a2f8871fc9d6de9bf684e135a1356c6))

* refactor(media_player): update availability logic ([`b16a2fe`](https://github.com/custom-components/alexa_media_player/commit/b16a2fe8202614c06a9130e86052d0808e332990))

* refactor(media_player): add log warning for TTS UI use ([`64d214d`](https://github.com/custom-components/alexa_media_player/commit/64d214de20ad72ff0953a4034ce92cb42254c7f6))

* refactor: add log request for unhandled commands ([`101efd6`](https://github.com/custom-components/alexa_media_player/commit/101efd652c65b46a7d568f2dfd179b0cb8f1e278))

* refactor: consolidate initialization of HA dict ([`149f4b6`](https://github.com/custom-components/alexa_media_player/commit/149f4b669d6e9c514d2536829ce31ad1036ea9b4))

### Style

* style: black reformat ([`4a29e63`](https://github.com/custom-components/alexa_media_player/commit/4a29e63ff85532ae057dcfbfc62bd8a3e22aa05e))

* style(media_player): simplify dict checks
Use dict.get instead of other key checks ([`08f57ae`](https://github.com/custom-components/alexa_media_player/commit/08f57ae23245c6a866406a3420ca1c35f0decb16))

### Unknown

* Merge pull request #511 from custom-components/dev

2.5.0 ([`7a532da`](https://github.com/custom-components/alexa_media_player/commit/7a532da10657f14afe719eb8d0a2afebdaa243de))

* Merge pull request #510 from alandtse/#alexapy1.4.1

fix: bump alexapy to 1.4.1 ([`0cd47f0`](https://github.com/custom-components/alexa_media_player/commit/0cd47f094588d0cfc9bad226414202f8ca1852cc))

* Merge pull request #509 from alandtse/#475

fix(media_player): fix clearing of data on state change ([`9fe40d9`](https://github.com/custom-components/alexa_media_player/commit/9fe40d9ffa3d4f24ef2d808de2633cdd9f048e66))

* Merge pull request #508 from alandtse/offline_detect

feat: add offline device detection ([`1ee9556`](https://github.com/custom-components/alexa_media_player/commit/1ee95563c4facd328ab7accefb9a335177e04913))

* Merge pull request #504 from alandtse/spotify_wha

fix(media_player): fix refresh of WHA children ([`7ed8fbe`](https://github.com/custom-components/alexa_media_player/commit/7ed8fbef83cfcc51486325cd20b733f70151cc7a))

* Merge pull request #503 from alandtse/#501

fix (sensor): add checks for timer values ([`1f86996`](https://github.com/custom-components/alexa_media_player/commit/1f869960887c18d7edbeb6e15f4fa09c26086e13))

* Merge pull request #502 from custom-components/master

Sync dev with master ([`d5b139a`](https://github.com/custom-components/alexa_media_player/commit/d5b139a926992908e9d2c40ce1099e1b1e707641))

* fix (sensor): add checks for timer values
Closes #501 ([`ead4cb2`](https://github.com/custom-components/alexa_media_player/commit/ead4cb26388c5bd0e7e0ec98ec79fcd4e22c4a72))


## v2.4.1 (2020-01-02)

### Build

* build: add black related configuration files ([`848b51a`](https://github.com/custom-components/alexa_media_player/commit/848b51a45497265fada75ee51c928435ba398569))

### Fix

* fix: add check for loaded parent
This addresses a case where the parent group has not been loaded prior to an
update of a child media player.
Closes #496 ([`951230d`](https://github.com/custom-components/alexa_media_player/commit/951230dbf6b9bbe535d8a9ad85d6dad4ba0d127a))

### Style

* style: apply black ([`f5f1841`](https://github.com/custom-components/alexa_media_player/commit/f5f18411a87e8d2a761cf3fb63bf94e12849caa8))

### Unknown

* Merge pull request #499 from custom-components/dev

2.4.1 ([`7649b1a`](https://github.com/custom-components/alexa_media_player/commit/7649b1a7ac31d133f431cc991367eafe9c1e472f))

* Merge branch &#39;master&#39; into dev ([`f13f502`](https://github.com/custom-components/alexa_media_player/commit/f13f50258a7a64776b496fee4d38cf86395e780d))

* Merge pull request #498 from alandtse/#496

fix: add check for loaded parent ([`2abfc76`](https://github.com/custom-components/alexa_media_player/commit/2abfc76ea7ba85a280fd541b1cdc194f7e328e37))

* Merge pull request #495 from alandtse/black

style: apply black ([`281c383`](https://github.com/custom-components/alexa_media_player/commit/281c383e8ce919282d6f8aad2aac034527d92066))


## v2.4.0 (2019-12-31)

### Build

* build: bump alexapy to 1.4.0 ([`5b637ab`](https://github.com/custom-components/alexa_media_player/commit/5b637ab332f7c295cdaaff47e5a692cc95585838))

### Chore

* chore: correct documentation ([`0abc8ce`](https://github.com/custom-components/alexa_media_player/commit/0abc8ce2e12438f2e296142b00dd609fae7e9f7a))

### Feature

* feat: add alexa sound to play_media
Closes #466 ([`3dc51f8`](https://github.com/custom-components/alexa_media_player/commit/3dc51f8ebadd1498e3f08e494d29432418944293))

### Fix

* fix(media_player): handle media without lemurVolume
Certain services like Spotify do not report any lemurVolume and resulted
in a key error. ([`de3a05d`](https://github.com/custom-components/alexa_media_player/commit/de3a05d989c07cfd94bbdfb1ff2c1ceb5324f84f))

* fix(media_player): remove unncecessary refresh ([`35bc743`](https://github.com/custom-components/alexa_media_player/commit/35bc743183a330edbdffebfe19597eea1816fd4b))

* fix(media_player): fix propagation of whole audio groups
Closes #444 ([`9677d27`](https://github.com/custom-components/alexa_media_player/commit/9677d27f4066c12d665d5711b3e1a25943d72eb0))

* fix: add PUSH_MEDIA_CHANGE to disable refresh ([`3b5c5f1`](https://github.com/custom-components/alexa_media_player/commit/3b5c5f13c3cc6aa48ad803015233071f9cf539a5))

* fix: add additional catches for login errors
Closes #461 ([`89a057b`](https://github.com/custom-components/alexa_media_player/commit/89a057b322d1e50849fbef5379c96c6842750646))

### Unknown

* Merge pull request #493 from custom-components/dev

2.4.0 ([`b5f3c8a`](https://github.com/custom-components/alexa_media_player/commit/b5f3c8a1cefc314571e862c4bce1f0b1de3e27e4))

* Merge pull request #491 from alandtse/#444

fix(media_player): fix propagation of whole audio groups ([`7a95bf4`](https://github.com/custom-components/alexa_media_player/commit/7a95bf4fa522a365119ff95a821086ec22dc2719))

* Merge pull request #486 from alandtse/#461

fix: add additional catches for login errors ([`723b941`](https://github.com/custom-components/alexa_media_player/commit/723b9415d3a659e81aa11e2e46dfb740449474f3))

* Merge pull request #482 from alandtse/#466

feat: add alexa sound to play_media ([`1b3019f`](https://github.com/custom-components/alexa_media_player/commit/1b3019f65c2100cf70f33c4e7d56f10867b3476d))

* Merge pull request #485 from custom-components/master

Sync dev with master ([`d3d334d`](https://github.com/custom-components/alexa_media_player/commit/d3d334dc040c403666d9125dab77787af9480e3c))


## v2.3.6 (2019-12-15)

### Chore

* chore: set minimum HA version

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`99d9262`](https://github.com/custom-components/alexa_media_player/commit/99d92624718250c1e65b81711ed374ab8ae0eb7a))

* chore: set minimum HA requirement

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`08c0d64`](https://github.com/custom-components/alexa_media_player/commit/08c0d641c5f9e71395f3ec8e90e7e4b58edb3345))

### Fix

* fix: add compatibility for older HA versions ([`7d03a93`](https://github.com/custom-components/alexa_media_player/commit/7d03a936c007a7e9337cb8ea88c6cf6210f796bb))

### Unknown

* Merge pull request #481 from alandtse/#474

fix: restore compatibility for older HA versions ([`75a783a`](https://github.com/custom-components/alexa_media_player/commit/75a783a081bbe1252010f49277e6786cc60d67c4))


## v2.3.5 (2019-12-13)

### Fix

* fix(alarm_control_panel): add supported_features ([`ceedd8b`](https://github.com/custom-components/alexa_media_player/commit/ceedd8ba7fac8e6c63c462f37f504bbef546d962))

### Unknown

* Merge pull request #479 from custom-components/dev

 fix(alarm_control_panel): add supported_features ([`92dda68`](https://github.com/custom-components/alexa_media_player/commit/92dda689f238de81b68256968e1b3e3ca044913e))

* Merge pull request #476 from alandtse/#474

fix(alarm_control_panel): add supported_features ([`f7de006`](https://github.com/custom-components/alexa_media_player/commit/f7de0069588bc2d6c6185854077dff93fdb7b228))


## v2.3.4 (2019-10-25)

### Fix

* fix(sensor): handle devices without timezone settings
Closes #440 ([`37434e3`](https://github.com/custom-components/alexa_media_player/commit/37434e39ed5c0f12cc97eada180e9edf871f61fc))

* fix: use correct HA state ([`db20537`](https://github.com/custom-components/alexa_media_player/commit/db2053736155c85269a52f67a2ec29fbd3ec4b32))

* fix: use HA STATE_UNKNOWN for empty sensors
Closes #419 ([`c72fb25`](https://github.com/custom-components/alexa_media_player/commit/c72fb25c75d753abd5c96f0cd21feb34470ae993))

### Unknown

* Merge pull request #448 from custom-components/dev

fix: fix next_alarm parsing ([`18a4cd3`](https://github.com/custom-components/alexa_media_player/commit/18a4cd383f1ad4b7acbed8f11d4b82bc2de0c98c))

* Merge pull request #447 from mikeage/fix_446

fix(sensor): return all sensor states as isoformat strings ([`b5857fc`](https://github.com/custom-components/alexa_media_player/commit/b5857fcb51837fd6a0311d680c95dc6589b1f041))

* Return all sensor states as isoformat()&#39;ed strings

This resolves issue #446, which had Safari displaying &#34;Invalid Date&#34;
instead of a proper countdown. The strings were being rendered using
Python&#39;s default datetime renderer, which did not put a &#34;T&#34; in between
the day and the hour, as required by ISO-8601 (and Safari&#39;s Date()
parser, but not Chrome&#39;s) ([`3e25d8f`](https://github.com/custom-components/alexa_media_player/commit/3e25d8f508e562b082cd923a8e05e90f055cda51))

* Merge pull request #442 from alandtse/#440

 fix(sensor): handle devices without timezone settings ([`169ed64`](https://github.com/custom-components/alexa_media_player/commit/169ed648fd47bcfc525f02cda40a4af4a4eb99f5))


## v2.3.3 (2019-10-13)

### Chore

* chore: remove redundant assignment

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`e9aebed`](https://github.com/custom-components/alexa_media_player/commit/e9aebed7f988254a3109e3dbd1a54e6476bd3bed))

* chore(media_player): change already_refreshed to param ([`028f3fb`](https://github.com/custom-components/alexa_media_player/commit/028f3fbfb2cd49a282bf6f749c5ac79824b3bb3d))

### Fix

* fix(media_player): remove unnecessary refresh ([`a3fec94`](https://github.com/custom-components/alexa_media_player/commit/a3fec94daec037b40f9b94194a6ccff1cdcd1c90))

* fix: account for apps in existing_serials ([`e9b3ec9`](https://github.com/custom-components/alexa_media_player/commit/e9b3ec994a2748dbcc454f70813e246ec6249579))

* fix: enable refresh polling if no PUSH_AUDIO_PLAYER_STATE ([`e3795b6`](https://github.com/custom-components/alexa_media_player/commit/e3795b65fc7925e49408d468e2587dce8e8f1f1f))

* fix: add processing of PUSH_MEDIA_PROGRESS_CHANGE ([`2b4a9bb`](https://github.com/custom-components/alexa_media_player/commit/2b4a9bb434043079a2b58654c657e589aea5210e))

* fix: add processing of PUSH_EQUALIZER_STATE_CHANGE ([`c123226`](https://github.com/custom-components/alexa_media_player/commit/c123226deacc91ea4bba337551d4d15adb59371d))

* fix: change availability when websocket detected
Closes #420 ([`9ee9f87`](https://github.com/custom-components/alexa_media_player/commit/9ee9f87edec138327be168742a3ea9dc5317402b))

* fix: fix seen_command testing for manual refresh ([`d4ce25a`](https://github.com/custom-components/alexa_media_player/commit/d4ce25adb70a7119276d346ad150791ca6cabf4b))

* fix: replace non-async configurator call
Closes #428 ([`9e53465`](https://github.com/custom-components/alexa_media_player/commit/9e534652e904b2aadb63b043643bf488c90b7dce))

### Style

* style: obfuscate email in logs ([`19ed157`](https://github.com/custom-components/alexa_media_player/commit/19ed157d062c2fa242abc8569ad7b9bf07beaaa0))

### Unknown

* Merge pull request #434 from custom-components/dev

fix: address websocket changes for other providers ([`55573e4`](https://github.com/custom-components/alexa_media_player/commit/55573e481e9de5d68a2b08c49276029ad30aea25))

* Merge pull request #435 from alandtse/#420

chore(media_player): change already_refreshed to param ([`8a4027e`](https://github.com/custom-components/alexa_media_player/commit/8a4027ebfea0f6a81082cb6e4edcdae78113648b))

* Merge pull request #433 from alandtse/#420

fix(media_player): remove unnecessary refresh ([`1a6b840`](https://github.com/custom-components/alexa_media_player/commit/1a6b840ae36f9ac8e6853e146737fd035af079b6))

* Merge pull request #432 from alandtse/#397a

fix: fix seen_command testing for manual refresh ([`2a52e1e`](https://github.com/custom-components/alexa_media_player/commit/2a52e1e785057b3111820948fa51654f2af4f2ea))

* Merge pull request #431 from alandtse/#420

fix: change availability when websocket detected ([`d1785bc`](https://github.com/custom-components/alexa_media_player/commit/d1785bc8eb680a76c3b9b61e2350226a2d80d81e))

* Merge pull request #429 from alandtse/#428

fix: replace non-async configurator call ([`f6a7205`](https://github.com/custom-components/alexa_media_player/commit/f6a7205a6400261be7f6dbcd3a5c2b38b6c09d25))


## v2.3.2 (2019-10-12)

### Fix

* fix: change return state to avoid Invalid Date
Closes #419 ([`0744d7d`](https://github.com/custom-components/alexa_media_player/commit/0744d7da88a889f86d17ff9e9c6d275eccafd8bb))

* fix: add fallback for media refresh

German users reported that updates were failing and investigation
determined that websockets was missing push information on audio
changes. This adds logic to use other websocket push events to try to
compensate.
However, this is a degraded functionality and results in additional
refresh calls.

Closes #397 ([`8238300`](https://github.com/custom-components/alexa_media_player/commit/823830011b5bf5cf12eb4320c799748f88f640a2))

* fix(helpers): fix key error during login exception
Closes #423 ([`ebda699`](https://github.com/custom-components/alexa_media_player/commit/ebda6996fd17f5fbaea96dbe19b53fd936b70003))

### Unknown

* Merge pull request #427 from custom-components/dev

2.3.2 ([`b537787`](https://github.com/custom-components/alexa_media_player/commit/b5377871472175eeb20df35f16f89efe7cf97315))

* Merge pull request #425 from alandtse/#397a

fix: add fallback for media refresh ([`3198192`](https://github.com/custom-components/alexa_media_player/commit/31981924353faec1b67b6b5d92a8bcc36121a92e))

* Merge pull request #426 from alandtse/#419

fix: change return state to avoid Invalid Date ([`87efdc6`](https://github.com/custom-components/alexa_media_player/commit/87efdc6d8095d4ff2ab012011d000a9158048e74))

* Merge pull request #424 from alandtse/#423

fix(helpers): fix key error during login exception ([`00c6c22`](https://github.com/custom-components/alexa_media_player/commit/00c6c22fef6921625b648815dd6399165f7c8564))


## v2.3.1 (2019-10-09)

### Chore

* chore: remove extraneous debug logging ([`998552e`](https://github.com/custom-components/alexa_media_player/commit/998552e251dbfcb73104783a438cc7411b4b9a46))

### Ci

* ci: revert to pypi semantic-release ([`a0db989`](https://github.com/custom-components/alexa_media_player/commit/a0db989fb84e2d8cbabe32acc35683ac78869580))

### Fix

* fix: fix indentation error ([`d7f2e6c`](https://github.com/custom-components/alexa_media_player/commit/d7f2e6c964e69200341d30539a0cbe56895f8fc3))

* fix(config_flow): display claimspicker_message correctly
Closes #401 ([`d91de03`](https://github.com/custom-components/alexa_media_player/commit/d91de037fe46056e0f8b43e0805f745ab6c6dffd))

* fix(sensor): set timezone of naive date_time alarms

Closes #409 ([`60d4618`](https://github.com/custom-components/alexa_media_player/commit/60d46182d616719919e376268b7fa21f0e0cc7ce))

* fix(sensor): fix missing music alarms

Closes #402 ([`c475421`](https://github.com/custom-components/alexa_media_player/commit/c47542161aa68872354527e92a8ac230ad244af7))

* fix(websocket): fix reconnect on disconnect

Closes #397 ([`91a6b57`](https://github.com/custom-components/alexa_media_player/commit/91a6b57d299f89efd636b696cde964c9612a4676))

### Style

* style: fix line length lint errors ([`829333f`](https://github.com/custom-components/alexa_media_player/commit/829333f9921db53b7d82abdd348ed0ae77eebd4e))

* style: remove unnecessary logging ([`d89491a`](https://github.com/custom-components/alexa_media_player/commit/d89491a7d9e1aca2711736013f188a93302f817e))

### Unknown

* Merge pull request #418 from custom-components/dev

2.3.1 ([`5641b5d`](https://github.com/custom-components/alexa_media_player/commit/5641b5db7635aa089735fd66913683c32dcd115a))

* Merge pull request #417 from alandtse/2.3.1

2.3.1 ([`2485b24`](https://github.com/custom-components/alexa_media_player/commit/2485b24781735a0fbde4edd94c794e59d4d6e04a))

* Merge pull request #415 from alandtse/#401

fix(config_flow): display claimspicker_message correctly ([`3bcee8f`](https://github.com/custom-components/alexa_media_player/commit/3bcee8f2b7b508bb336994cf952308ce8df33f70))

* Merge pull request #413 from alandtse/#397

fix(websocket): fix reconnect on disconnect ([`6fb1ad6`](https://github.com/custom-components/alexa_media_player/commit/6fb1ad634eb61b504c4540bbe96016fc18d6756f))

* Merge pull request #416 from alandtse/ci

ci: revert to pypi semantic-release ([`e60d0f3`](https://github.com/custom-components/alexa_media_player/commit/e60d0f3aa362d336a395e107a88ff0d964a999d8))

* Merge pull request #411 from alandtse/#409

fix(sensor): set timezone of naive date_time alarms ([`e619401`](https://github.com/custom-components/alexa_media_player/commit/e619401a295d3af14de1150e487a79d12b2e7e79))

* Merge pull request #412 from alandtse/#402

fix(sensor): fix missing music alarms ([`458b518`](https://github.com/custom-components/alexa_media_player/commit/458b518f6c163720ad33fe774bf1e7cd32efa056))

* Merge pull request #410 from custom-components/master

Sync dev with master ([`633cdbd`](https://github.com/custom-components/alexa_media_player/commit/633cdbd1a4bd11ff6732105def398f0500a0da4c))


## v2.3.0 (2019-09-29)

### Ci

* ci: swap to GH_TOKEN secret

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`34f0170`](https://github.com/custom-components/alexa_media_player/commit/34f0170c8bd85d68f548cffb6d5b11a619077d6e))

* ci: try inclusion of GITHUB_ACTOR

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`ae1308e`](https://github.com/custom-components/alexa_media_player/commit/ae1308e37ad5c9820d34a01ba7b753f8c8ed53c0))

* ci: install specific version of semantic-release

https://github.com/relekang/python-semantic-release/issues/109
Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`4b1c568`](https://github.com/custom-components/alexa_media_player/commit/4b1c568219cc40892b84baf028df2679c61eb5c1))

* ci: checkout master instead of ref

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`d9aa940`](https://github.com/custom-components/alexa_media_player/commit/d9aa94079cecf5eeaa30f8468724e48a591a29fa))

* ci(semantic-release): remove noop

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`3029fb8`](https://github.com/custom-components/alexa_media_player/commit/3029fb832eee32002d4795e8df7c2ba2bbd4b648))

### Documentation

* docs(license): replace with canonical text ([`cdb9f13`](https://github.com/custom-components/alexa_media_player/commit/cdb9f139a0289e8afe194b5b836b35622fdbaa5e))

### Feature

* feat: add clear_history service ([`ecbc8b6`](https://github.com/custom-components/alexa_media_player/commit/ecbc8b6db8f5bf93a691d83faadee7d98ad7f53d))

* feat: add logic to catch login errors ([`6633598`](https://github.com/custom-components/alexa_media_player/commit/66335980944b14dffb9863b141f9c2a402f305dc))

* feat: add basic notifications sensors ([`465b2ca`](https://github.com/custom-components/alexa_media_player/commit/465b2ca0aaf8808a64bd1770a922756a86212e49))

### Fix

* fix: bump alexapy to 1.3.1 ([`f8ea48b`](https://github.com/custom-components/alexa_media_player/commit/f8ea48b84831dea2c4bc02fc2d3d87550e3d2955))

* fix: update to alexapy 1.3.0

Closes #387 ([`64c5d8f`](https://github.com/custom-components/alexa_media_player/commit/64c5d8f97e6847ac46a659779d6d31311cdf6f92))

* fix: update hacs.json for sensor domain ([`0396a55`](https://github.com/custom-components/alexa_media_player/commit/0396a557e308e0dfda9f68b1e355269a25fbecbb))

* fix: align shuffle property with HA ([`0b9bc3c`](https://github.com/custom-components/alexa_media_player/commit/0b9bc3cfdc596082182e325e28bc9d27237b6183))

* fix: add media_image_remotely_accessible property ([`0881046`](https://github.com/custom-components/alexa_media_player/commit/0881046e51a32b0498e9aab136ba20b4894a91cb))

* fix(sensor): catch keyerror on update ([`29e98c1`](https://github.com/custom-components/alexa_media_player/commit/29e98c1c4ec4b6a8cdf802b357dfa243cbd5b3b5))

* fix: add websocket updates for notifications ([`e0b8dc3`](https://github.com/custom-components/alexa_media_player/commit/e0b8dc37a9520a1c041ca33b7fac42169ee0d745))

* fix: catch KeyError for last_called ([`5db0706`](https://github.com/custom-components/alexa_media_player/commit/5db0706c03303d38e8a97ec44939a572a023ccb0))

* fix(config_flow): catch connection errors in config_flow and inform user ([`ef06760`](https://github.com/custom-components/alexa_media_player/commit/ef06760e61c5e0f406d4f35835e1e5958efa6d93))

* fix(update_devices): prompt for login on disconnect ([`cb3a8fb`](https://github.com/custom-components/alexa_media_player/commit/cb3a8fb90eb116edcd5be3c270c8041a8633bd23))

* fix(configurator): fix bug where unable to relogin using configurator ([`81a7127`](https://github.com/custom-components/alexa_media_player/commit/81a7127e9144c185668ecb4d23a9a21c40fd3a06))

* fix(config_flow): fix bug where import configuration not resumed ([`6579b6f`](https://github.com/custom-components/alexa_media_player/commit/6579b6f07298193ea6ba89de8bb15f9915fb9de9))

* fix(notify): fix keyerror when unloading with no loaded entities ([`d4b09ce`](https://github.com/custom-components/alexa_media_player/commit/d4b09ce9089b5c4f47288eedd2980ffab3edcdbd))

### Refactor

* refactor: add process_notifications subfunction ([`9a9d0a3`](https://github.com/custom-components/alexa_media_player/commit/9a9d0a328a67a10c1b97a3505eac2c377f501a4c))

* refactor: simplify redundant logic ([`3234749`](https://github.com/custom-components/alexa_media_player/commit/3234749723d1e510a8064985c2ae4c1d753bb9f3))

* refactor: move helpers to alexapy ([`6a40dff`](https://github.com/custom-components/alexa_media_player/commit/6a40dfff73536fc8b80dd832fddcfd82f0de40ea))

### Style

* style: use f-string for bus calls ([`e259c4a`](https://github.com/custom-components/alexa_media_player/commit/e259c4a6cbb7ceffe0a4f2654f0b03067256fcc7))

* style: fix flake errors ([`f7020fa`](https://github.com/custom-components/alexa_media_player/commit/f7020fa5c0c7d4573caef0c6047acf65508e9021))

* style: resolve flake errors ([`5e1870d`](https://github.com/custom-components/alexa_media_player/commit/5e1870d75a4da4e0a5db66f6675ae3b533de41a1))

* style: fix flake errors ([`025a3d1`](https://github.com/custom-components/alexa_media_player/commit/025a3d1c93907624f56f0f57aeee3372da470974))

### Unknown

* Merge pull request #396 from custom-components/dev

feat: add notifications sensors and clear_history service ([`b39d8c8`](https://github.com/custom-components/alexa_media_player/commit/b39d8c875f7dd64d80bd9cb0e029d8ccf16931b5))

* Merge pull request #395 from alandtse/notifications

feat: add clear_history service ([`9f0ccda`](https://github.com/custom-components/alexa_media_player/commit/9f0ccda7c0bcfcc8cf4767072a0a68ea9084e595))

* Merge branch &#39;clear_history&#39; of github.com:macbury/alexa_media_player into notifications ([`805dace`](https://github.com/custom-components/alexa_media_player/commit/805dace44311dda1fb4c3b3e3ee5b23751dac54f))

* Merge pull request #393 from alandtse/notifications

feat: add alexa notifications as sensors ([`f0353f0`](https://github.com/custom-components/alexa_media_player/commit/f0353f02a27425a720ec3c28c1efdf08fc24377a))

* Merge pull request #388 from alandtse/#387

fix: fix config_flow connection handling ([`40f7ec9`](https://github.com/custom-components/alexa_media_player/commit/40f7ec99250e0919ef94b057d9d7817860bfde85))


## v2.2.1 (2019-09-22)

### Chore

* chore: fix mypy error ([`bf3c655`](https://github.com/custom-components/alexa_media_player/commit/bf3c65537fbd1e4cd3f896153255a34fe38c9b94))

* chore: add Polish (#379)

* Create pl.json

Add polish translation

* Fix typo ([`990e379`](https://github.com/custom-components/alexa_media_player/commit/990e379f37d3ac93676be89793a14efb3d7f371a))

* chore: Add Italian

Italian Translation for the components ([`d14b3b2`](https://github.com/custom-components/alexa_media_player/commit/d14b3b259b59fa815327892f07ca66d5eebd6a7f))

* chore: Add Dutch translation ([`d802640`](https://github.com/custom-components/alexa_media_player/commit/d802640904fabba2e9ee44b4026fe3b7a7094cfe))

### Ci

* ci: fix typo

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`0d470f1`](https://github.com/custom-components/alexa_media_player/commit/0d470f1d21e9ef1ad14405698806ab008c79a678))

* ci(semantic-release): enable debugging

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`c9404a5`](https://github.com/custom-components/alexa_media_player/commit/c9404a5ff7a0f1176dc47f66bb731bd8bf5dab73))

* ci(semantic-release): separate steps for testing

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`5888447`](https://github.com/custom-components/alexa_media_player/commit/588844740f81aadd1aec8d830b08ee13e05bbfeb))

* ci: add semantic-release

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`589f64d`](https://github.com/custom-components/alexa_media_player/commit/589f64d1d820fc587f1876d83b89f1224c4fd185))

### Fix

* fix: bump alexapy to 1.2.1 ([`f6da0d0`](https://github.com/custom-components/alexa_media_player/commit/f6da0d01852397897b6e7702f864adb3a31d20e9))

* fix(init): reuse existing login if it exists ([`f4c018a`](https://github.com/custom-components/alexa_media_player/commit/f4c018a9b06eb5caad45929b96a507736840548d))

* fix(init): add retries to setup_config entries ([`0d68043`](https://github.com/custom-components/alexa_media_player/commit/0d6804302bbd0a06648ccb6701252a03f386e146))

* fix: disable update before add to avoid warning on disabled entities ([`bbede43`](https://github.com/custom-components/alexa_media_player/commit/bbede43c3eda7e566e5ec0126996b94fa918c205))

* fix: add relevant icons to switches ([`a66364d`](https://github.com/custom-components/alexa_media_player/commit/a66364dce7c031ac2ca849bcd8b1533541f15758))

* fix: add availability state to switches ([`fd44b7c`](https://github.com/custom-components/alexa_media_player/commit/fd44b7cf22199426a805101276ee24ebb5221004))

* fix(config_flow): fix handling of filter options ([`1a53b98`](https://github.com/custom-components/alexa_media_player/commit/1a53b9804d8837533e495ddeba21f29de62561c1))

### Performance

* perf(media_player): reduce auth gets by moving to init

get_auth calls were previously called for every new media_player. This
is unnecessary and only needs to happen once per account. ([`a85ce9e`](https://github.com/custom-components/alexa_media_player/commit/a85ce9e6f721b43a1bc49852f2da690293d01f1c))

### Unknown

* Merge pull request #386 from alandtse/2.2.1

2.2.1 ([`afde620`](https://github.com/custom-components/alexa_media_player/commit/afde620ef2ba116750da34f2345230ac6b5a1133))

* Merge pull request #385 from custom-components/dev

2.2.1 ([`84dcdde`](https://github.com/custom-components/alexa_media_player/commit/84dcdde5d65838a85b6430ed8055b95a343f10a1))

* Merge pull request #384 from alandtse/2.2.1

fix: bump alexapy to 1.2.1 ([`7a27a20`](https://github.com/custom-components/alexa_media_player/commit/7a27a209141031dd63afd7325088101f1bd867ff))

* Merge pull request #381 from alandtse/#362

fix: add retry logic to setup_entry ([`b08900f`](https://github.com/custom-components/alexa_media_player/commit/b08900fa8a2db4945bb02c9680b5942c9135a910))

* Some text too long - Updated (#383)

* Create nl.json

* Some text too long - updated ([`530bf43`](https://github.com/custom-components/alexa_media_player/commit/530bf43aa4b198f0d4d03a7629ec75914c156453))

* Merge pull request #382 from custom-components/semantic-release

ci: add semantic-release ([`677444c`](https://github.com/custom-components/alexa_media_player/commit/677444cba29f0fcde9d856ff22083d091c258e44))

* Merge pull request #378 from alandtse/#377

fix(config_flow): fix handling of filter options ([`2f33b1a`](https://github.com/custom-components/alexa_media_player/commit/2f33b1ad6ae894bdc7609681fe65870fca2b93b0))


## v2.2.0 (2019-09-19)

### Feature

* feat: add de.json ([`48515ba`](https://github.com/custom-components/alexa_media_player/commit/48515ba7ac003587c2709e481ebc71b06e7b567f))

* feat: add en.json for config_flow ([`52b700a`](https://github.com/custom-components/alexa_media_player/commit/52b700a9aae53816e213c08345e7522f8e0ff5ee))

* feat: add unloading of config_entry ([`ea87497`](https://github.com/custom-components/alexa_media_player/commit/ea874973debf1a845d321d0cc4cc2402f1089efd))

* feat: add device_info for integration grouping ([`3c5ff3a`](https://github.com/custom-components/alexa_media_player/commit/3c5ff3ab486fefa3f1a66171ca642e58688a57f4))

* feat: support unloading of entries ([`75a46c4`](https://github.com/custom-components/alexa_media_player/commit/75a46c4b605b222cbcc01e1bfb7627491d4e9c87))

* feat: enable config_flow from configuration ([`dfe85da`](https://github.com/custom-components/alexa_media_player/commit/dfe85da52471c855bdd05b6a2782598913b1fc99))

* feat: enable config_flow ([`312c9e9`](https://github.com/custom-components/alexa_media_player/commit/312c9e9b6b0b31b125197b779fa09b5ae2074d26))

### Fix

* fix(switch): increase delay for switch load

Closes #361 ([`2b865f4`](https://github.com/custom-components/alexa_media_player/commit/2b865f4557952f3d6dc89428e1263d6578dcaae3))

* fix: bump alexapy to 1.2.0

Closes #353, #357 ([`2eca9fe`](https://github.com/custom-components/alexa_media_player/commit/2eca9feaf6bc2d61bac1979d50a19ebf2ae3a870))

* fix(de.json): fix typo ([`c06c415`](https://github.com/custom-components/alexa_media_player/commit/c06c41513e4ae229abb21dbed8c408ee7262a15e))

* fix: fix bug where HA &lt;98.1 would be incompatible with self.enabled check ([`a19de53`](https://github.com/custom-components/alexa_media_player/commit/a19de5377f76ef30c0ad85bcb1fab007f1212d77))

* fix: show prior values in config_flow ([`77020c3`](https://github.com/custom-components/alexa_media_player/commit/77020c3432e6c24bb7fbd05d8efaf29d6ee28f82))

* fix: fix bug where default schema not schema ([`1598c52`](https://github.com/custom-components/alexa_media_player/commit/1598c52fa3ed38cfcc7cd1608755fb52bcd7dac3))

* fix: fix device_info identifiers ([`b1c8213`](https://github.com/custom-components/alexa_media_player/commit/b1c8213fa8d94719682a3681129a45d1189ea74a))

* fix: add checks for self.enabled prior to HA updates ([`28582a0`](https://github.com/custom-components/alexa_media_player/commit/28582a0b07d574a3cd4e29c9f5cc5412596cecdf))

* fix(media_player): fix bad reference to hass ([`3bf4ffb`](https://github.com/custom-components/alexa_media_player/commit/3bf4ffb8de94e220a90f3455774ae42cbdc2c95c))

* fix(configflow): fix bug where login not closed on success ([`d419b6f`](https://github.com/custom-components/alexa_media_player/commit/d419b6f1a7e83a41c76ffc6b1219694e6c4981d0))

* fix(helpers): correctly treat add_devices with empty list as non error ([`168101d`](https://github.com/custom-components/alexa_media_player/commit/168101db066cc1f7d1de4551d3f5c1118a80bf94))

### Style

* style(helpers): add additional context to debug logs ([`2cf63a3`](https://github.com/custom-components/alexa_media_player/commit/2cf63a3c3307798bad1f28076768c2f37ba6433b))

### Unknown

* Merge pull request #371 from custom-components/dev

2.2.0 ([`af55ffc`](https://github.com/custom-components/alexa_media_player/commit/af55ffc67d5149645b4937119c746499657dcfdf))

* Merge pull request #370 from alandtse/2.2.0

2.2.0 ([`da168d8`](https://github.com/custom-components/alexa_media_player/commit/da168d88100967832ead9c6de8695591a2fa03dd))

* Merge pull request #365 from alandtse/configflow

feat: add configflow ([`bfdae1f`](https://github.com/custom-components/alexa_media_player/commit/bfdae1fa53c2d7a9c4b1d28f01cfc746f74c74bb))

* Merge branch &#39;#357&#39; into configflow ([`27afe7e`](https://github.com/custom-components/alexa_media_player/commit/27afe7ef782d36c2a06e974f895cc7da5dc0b23a))


## v2.1.2 (2019-09-09)

### Fix

* fix: update to alexapy 1.1.2 ([`a41dc1b`](https://github.com/custom-components/alexa_media_player/commit/a41dc1b57bb8b571f7dcfde7cf13970e5e0fe703))

### Unknown

* Merge pull request #352 from custom-components/dev

v2.1.2 ([`568aa3c`](https://github.com/custom-components/alexa_media_player/commit/568aa3c23a567505da599fa27f439f7040c2d12b))

* Merge pull request #351 from alandtse/#346

v2.1.2 ([`2d04049`](https://github.com/custom-components/alexa_media_player/commit/2d040492eeb8ec5f571ad3974cddede0e2f7b875))


## v2.1.1 (2019-09-08)

### Chore

* chore: add log section to bug report template

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`ad9b95b`](https://github.com/custom-components/alexa_media_player/commit/ad9b95bce54a93714516bec1212a63b623c4d9a5))

### Fix

* fix: update alexapy to 1.1.1 ([`33f3247`](https://github.com/custom-components/alexa_media_player/commit/33f32470f31c36e2a32caecf3e3f80291ff15dd9))

* fix: update alexapy to 1.1.0 ([`4bc5fc8`](https://github.com/custom-components/alexa_media_player/commit/4bc5fc852d47704502001977213737f68eacb461))

* fix: add enable retry for media_player and alarm_control_panel setup ([`2f2f7a0`](https://github.com/custom-components/alexa_media_player/commit/2f2f7a029bb88525a48d5a7ad50005af21dc4981))

* fix: add retry_async wrapper to automatically retry after failures

This will allow platforms to wait for media_player to load before trying 
to load ([`2ce12f4`](https://github.com/custom-components/alexa_media_player/commit/2ce12f4d031eb1283e88b2a1f928ef1c2f91f137))

* fix: clean discovery_info of unneeded values prior to passing ([`b5e1894`](https://github.com/custom-components/alexa_media_player/commit/b5e189456cb3bfcf3f12ad2de773dec048e6849c))

### Style

* style: isort imports ([`da78421`](https://github.com/custom-components/alexa_media_player/commit/da7842196d266b1116377d00f7a101ff6267d708))

### Unknown

* Merge pull request #348 from custom-components/dev

v2.1.1 ([`9ed3e7b`](https://github.com/custom-components/alexa_media_player/commit/9ed3e7b77bbc7b526cad1c00a342807311f3a754))

* Merge pull request #347 from alandtse/#346

v2.1.1 ([`f834d18`](https://github.com/custom-components/alexa_media_player/commit/f834d18e5c99fb07fadadad126bde87d235f9188))

* Merge pull request #343 from alandtse/retry_load

fix: add retry_async wrapper to automatically retry after failures ([`3e86308`](https://github.com/custom-components/alexa_media_player/commit/3e8630866a344a94e91c1d8683517c3f04cba795))

* Merge pull request #341 from alandtse/#336

fix: clean discovery_info of unneeded values prior to passing ([`4699797`](https://github.com/custom-components/alexa_media_player/commit/4699797c9e08ab611b93e28941d018620fdcd455))

* Merge pull request #342 from custom-components/master

chore: sync master to dev ([`8108697`](https://github.com/custom-components/alexa_media_player/commit/810869765fb1b7916f0ecb54f1913ae3e02c6d13))


## v2.1.0 (2019-09-03)

### Chore

* chore: add hacs.json ([`a17fe65`](https://github.com/custom-components/alexa_media_player/commit/a17fe658bd87039bdf7bdf71b9cb10d360dcf58a))

### Feature

* feat: allow exclusions for alarm_control_panel and switches ([`169545f`](https://github.com/custom-components/alexa_media_player/commit/169545f779d036a3c9a35dd150dafc8c657e0e12))

### Fix

* fix: update to alexapy 1.0.2 ([`3e50526`](https://github.com/custom-components/alexa_media_player/commit/3e50526a14367121cbcf36b4088df8827747d6b8))

* fix: change platform loading to be account specific

Previously loading platforms would try to load all devices across all 
accounts. This could result in a race condition if multiple accounts 
loaded platforms at the same time. ([`bcc0de7`](https://github.com/custom-components/alexa_media_player/commit/bcc0de791237ed3cf2ca70e454efef194b298fc9))

* fix(notify): rename send_message with prefix async_ ([`243d485`](https://github.com/custom-components/alexa_media_player/commit/243d485e8298f9a71be0f35ff426c1e6a61fb80c))

* fix(notify): add key check for targets ([`fac356d`](https://github.com/custom-components/alexa_media_player/commit/fac356d34f1d23dfcd987ab4666081283aa8297f))

* fix: add checks for self.enabled prior to HA updates ([`6608a5f`](https://github.com/custom-components/alexa_media_player/commit/6608a5f3e6cdfbbef3099797bc66d710ccbc56ed))

* fix(update_devices): avoid throttling in case of multiple accounts ([`e21ffc8`](https://github.com/custom-components/alexa_media_player/commit/e21ffc8b65d8f520004055100d46f28b43821705))

* fix(add_devices): remove extraneous await ([`56eb0ea`](https://github.com/custom-components/alexa_media_player/commit/56eb0ea3a4e7885d8408d44bd2e8df30c8f35ac0))

* fix: add catch for HomeAssistantError when adding entities ([`43acc8b`](https://github.com/custom-components/alexa_media_player/commit/43acc8bd790e4ac2082a7e8782888521b5aa6ccd))

* fix(bluetooth): ensure source attribute is valid member of source list ([`4ebc313`](https://github.com/custom-components/alexa_media_player/commit/4ebc313a5fa2c9e3051a4d08c2f96f8b9cdb726f))

* fix: cleanup remaining sync references ([`6f71f50`](https://github.com/custom-components/alexa_media_player/commit/6f71f5044ef56f3dce174d55a3aaf7bbd91a6c9e))

* fix: provide updated message for use of HA tts UI ([`46b9d88`](https://github.com/custom-components/alexa_media_player/commit/46b9d888c05a1da5203f3e9bda51b58777644aaf))

* fix: update HA state on bluetooth change ([`fb432af`](https://github.com/custom-components/alexa_media_player/commit/fb432af6856ca67ca40781eb385f9a10f647437a))

* fix(bluetooth): bug where bluetooth state not properly updated ([`c5da965`](https://github.com/custom-components/alexa_media_player/commit/c5da965bc4eb3b1caecd7c96d60cd351aae68901))

* fix(bluetooth): add await for set_bluetooth ([`e622497`](https://github.com/custom-components/alexa_media_player/commit/e62249771b6acc91eb6577d91f9a2edaa26ddcf8))

### Refactor

* refactor(bluetooth): reduce unneeded update requests ([`f7ecbf7`](https://github.com/custom-components/alexa_media_player/commit/f7ecbf778d0f76ea139c32168911790c634c5092))

### Style

* style(notify): fix docstring for devices ([`6f4a050`](https://github.com/custom-components/alexa_media_player/commit/6f4a050908f36fca283ecf547e7a3086acc04d12))

* style(alarm_control_panel): remove extraneous None return ([`5c98a9c`](https://github.com/custom-components/alexa_media_player/commit/5c98a9c53b6bcdd038905299a89db9f857885a97))

* style(update_devices): clarify logging for include/exclude filters ([`b027fb3`](https://github.com/custom-components/alexa_media_player/commit/b027fb3ec49b38dbe5370b02804fc7964a0bd640))

* style(add_devices): add additional exception catch ([`e945c0c`](https://github.com/custom-components/alexa_media_player/commit/e945c0c79c00807b2e04781038e8813d192d5303))

* style(bluetooth): add additional debug logging ([`12e2484`](https://github.com/custom-components/alexa_media_player/commit/12e2484fb3a937477d14ee4c771d6d2a72d641bd))

* style: add additional obfuscation to logs ([`ef8d709`](https://github.com/custom-components/alexa_media_player/commit/ef8d709bb515365686c98d5a4ac60cccff13fdb5))

### Unknown

* Merge pull request #335 from custom-components/dev

2.1.0 ([`1d1f0d0`](https://github.com/custom-components/alexa_media_player/commit/1d1f0d0d316a2a98ee173a39bb582cc82f5b8436))

* Merge pull request #334 from alandtse/2.1.0

chore: bump version to 2.1.0 ([`fe16005`](https://github.com/custom-components/alexa_media_player/commit/fe160056174e3a6e9abac2795e72feac8b1a3994))

* Merge pull request #333 from alandtse/#260

feat: allow exclusions for alarm_control_panel and switches ([`56f53a5`](https://github.com/custom-components/alexa_media_player/commit/56f53a55bbafa2185d06b45741c4af9b911a5bbd))

* Merge pull request #332 from custom-components/revert-327-#317

Revert &#34;fix: add checks for self.enabled prior to HA updates&#34; ([`c38b28c`](https://github.com/custom-components/alexa_media_player/commit/c38b28c0729fba52defd46db2550b439b8ddabc4))

* Revert &#34;fix: add checks for self.enabled prior to HA updates&#34; ([`6dd333d`](https://github.com/custom-components/alexa_media_player/commit/6dd333d79729f1cadd27d9c14b7e92858366182b))

* Merge pull request #324 from alandtse/#260

fix: add catch for HomeAssistantError when adding entities ([`ae11e52`](https://github.com/custom-components/alexa_media_player/commit/ae11e526ebaeb1196dffb2dceab077e301a061fa))

* Merge pull request #327 from alandtse/#317

fix: add checks for self.enabled prior to HA updates ([`6dd1bc3`](https://github.com/custom-components/alexa_media_player/commit/6dd1bc3160c448d26eebae74230020f29a76a228))

* Merge pull request #329 from alandtse/#328

fix(notify): add key check for targets ([`06041bb`](https://github.com/custom-components/alexa_media_player/commit/06041bb4c84ff7f40cf9831fdbb6f2807041be4a))

* Merge pull request #325 from alandtse/#319

chore: add hacs.json ([`4c74ffa`](https://github.com/custom-components/alexa_media_player/commit/4c74ffad6b7abca02e80c54b4603264b9ac20c09))

* Merge pull request #321 from alandtse/#316

fix(bluetooth): resolve bluetooth update issues ([`63aaa76`](https://github.com/custom-components/alexa_media_player/commit/63aaa768fa9e4be9e185ec5883377de19586afd2))

* Merge pull request #326 from custom-components/master

Sync dev with master ([`ab83ad5`](https://github.com/custom-components/alexa_media_player/commit/ab83ad5fab85964c4601f5b5b86e3c433e08e2f7))


## v2.0.1 (2019-08-31)

### Chore

* chore(manifest): update alexapy and HA min version ([`2cdb259`](https://github.com/custom-components/alexa_media_player/commit/2cdb25913a17c2aeaffa24f7ea77bdbf7b020ec3))

### Fix

* fix(bluetooth): check for valid response from get_bluetooth ([`b1422c4`](https://github.com/custom-components/alexa_media_player/commit/b1422c43378713aee1eb31ddd708de1330633429))

* fix(media_player): remove await for async_schedule_update_ha_state ([`d801a59`](https://github.com/custom-components/alexa_media_player/commit/d801a599988fe41ec52139c6f5954bd35025fe76))

* fix(media_player): set await for async source functions ([`26d3c17`](https://github.com/custom-components/alexa_media_player/commit/26d3c1719222ec92fe7e92187c780a62c82bc0d2))

### Style

* style: update documentation for move to custom_components project ([`9eb1902`](https://github.com/custom-components/alexa_media_player/commit/9eb1902ceb6434418496890c00cc9767c7b4bdca))

* style: rephrase configurator callback debugging ([`72d2f78`](https://github.com/custom-components/alexa_media_player/commit/72d2f78ee7a6556854ceb252a3bcd2334c6b74c8))

* style(configurator): emphasize options for configurator ([`f6b14fa`](https://github.com/custom-components/alexa_media_player/commit/f6b14facd86b493ce067fffe3a8eb19f0cad0924))

### Unknown

* Merge pull request #314 from custom-components/dev

2.0.1 ([`e102848`](https://github.com/custom-components/alexa_media_player/commit/e102848db04dfde56a75b2b5ebb9b11f302a50d0))

* Merge pull request #318 from alandtse/dev

style: update documentation for move to custom_components project ([`f455772`](https://github.com/custom-components/alexa_media_player/commit/f4557720a98c7073938becd3d29d131f4fdaa361))

* Merge pull request #312 from alandtse/dev

2.0.1 ([`781e0fc`](https://github.com/custom-components/alexa_media_player/commit/781e0fcf6489092e1b42969eeac1f6e6092be14e))

* Merge pull request #311 from alandtse/#309

 fix(bluetooth): check for valid response from get_bluetooth ([`cec83fd`](https://github.com/custom-components/alexa_media_player/commit/cec83fdff76a545ac40afd1196b4f79d20b7a13d))

* Merge pull request #303 from alandtse/#302

 fix(media_player): set await for async source functions ([`dfdffe6`](https://github.com/custom-components/alexa_media_player/commit/dfdffe6deebe7eeaa84064ae6fd2e057ac59da2c))

* Merge pull request #305 from keatontaylor/master

Merge pull request #296 from keatontaylor/dev ([`4b8821e`](https://github.com/custom-components/alexa_media_player/commit/4b8821ee71b0b2142c80ec990d4f63cb77c6a4bc))


## v2.0.0 (2019-08-22)

### Chore

* chore: bump version to 2.0.0 ([`8522058`](https://github.com/custom-components/alexa_media_player/commit/85220586e497c75cc10acd3f6ca0098abd10a7cd))

* chore: add semantic-release support ([`d62e0b5`](https://github.com/custom-components/alexa_media_player/commit/d62e0b5d93622ebed84feb9c7711a42f7a77c72e))

* chore: bump alexapy to 1.0.0 ([`7bdf2f9`](https://github.com/custom-components/alexa_media_player/commit/7bdf2f9985db136f944f4bc4f3faf79ba50a96e1))

* chore(custom_updater): remove deprecated file ([`6aa9b22`](https://github.com/custom-components/alexa_media_player/commit/6aa9b229658f1d2690e8a31b4e524b8136c99bfc))

* chore(custom_components): remove deprecated file

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`2ddd0c2`](https://github.com/custom-components/alexa_media_player/commit/2ddd0c2944c35c4684cb0fb5905518652fc45ea6))

### Feature

* feat: migrate to async ([`d8f08d7`](https://github.com/custom-components/alexa_media_player/commit/d8f08d700555929ef7025b008897fcb1abc06888))

* feat: migrate to async ([`54f04f8`](https://github.com/custom-components/alexa_media_player/commit/54f04f8775ff35f7104703f8c9eea0217229203d))

### Fix

* fix(update_devices): add key existence checks ([`af0ad6b`](https://github.com/custom-components/alexa_media_player/commit/af0ad6b0a40841a26bf02e9c86b706b7494af5fc))

* fix: properly close aiohttp session on HA shutdown ([`a0fcf32`](https://github.com/custom-components/alexa_media_player/commit/a0fcf322d54d62f8056c75c1d5d18dad514d428f))

* fix: complete migration to async ([`0d2b317`](https://github.com/custom-components/alexa_media_player/commit/0d2b3174439d4d287d0606b87e0974f58fd0f0ca))

* fix: properly close aiohttp session on HA shutdown ([`33f780f`](https://github.com/custom-components/alexa_media_player/commit/33f780f4ea4557c198a2ea9a228485f4b50716e6))

* fix: complete migration to async ([`3edbea2`](https://github.com/custom-components/alexa_media_player/commit/3edbea2c8bfa0b5161ab20ba004b15ea1ddc3feb))

### Unknown

* Merge pull request #296 from keatontaylor/dev

Bump to 2.0.0

BREAKING CHANGE ([`474c30d`](https://github.com/custom-components/alexa_media_player/commit/474c30d132582862f497eadacd0f436237e99230))

* Merge pull request #294 from alandtse/async

feat: migrate to async ([`9032c00`](https://github.com/custom-components/alexa_media_player/commit/9032c007bd598b3192e92c39a444e678314683a1))

* Merge pull request #280 from keatontaylor/master

chore: sync dev to master ([`2a3c131`](https://github.com/custom-components/alexa_media_player/commit/2a3c131fc4db09e8c6f569509fb25940454ff991))


## v1.4.1 (2019-08-08)

### Chore

* chore: bump version ([`abc9d9c`](https://github.com/custom-components/alexa_media_player/commit/abc9d9c124cb94a22d0596f9c1dcc2256941dec1))

* chore(switch): add status debugging ([`30caec5`](https://github.com/custom-components/alexa_media_player/commit/30caec511534e6dd60a2ec5ed57f469431e060bd))

* chore(const): bump version ([`a8479e3`](https://github.com/custom-components/alexa_media_player/commit/a8479e31060e51050f1e59a5d47e02e9cd262b99))

* chore(alexapy): update to 0.7.1 ([`4b552f6`](https://github.com/custom-components/alexa_media_player/commit/4b552f65f8b60413640f8abab0f68d870d95cf79))

* chore(guard): obfuscate email in debug message ([`f213820`](https://github.com/custom-components/alexa_media_player/commit/f213820d4de2644a7f89876af68d6fc093688a9e))

### Feature

* feat(switches): add code to update state changes ([`54afcfd`](https://github.com/custom-components/alexa_media_player/commit/54afcfd025a222675214bfafdf924673e26fd398))

### Fix

* fix(mediaplayer): fix dnd keyerror ([`93426ac`](https://github.com/custom-components/alexa_media_player/commit/93426ac80e709e75f54f241ee335740784ef9903))

* fix(switch): add unique_id function ([`241bc1c`](https://github.com/custom-components/alexa_media_player/commit/241bc1c47c59ac6fbb3a9d0917e5a1c9a622406a))

* fix(wshandler): properly handle entryId does not contain # ([`d0d7a9b`](https://github.com/custom-components/alexa_media_player/commit/d0d7a9ba44b708aedfd286b554c9ee2eb1efe8c7))

* fix(captcha): add captcha to handle OTP selection page ([`c38a753`](https://github.com/custom-components/alexa_media_player/commit/c38a753dfddb102d7e1ba6c2a145e4001c5afb7c))

* fix(media_player): fix bug where get_last_called called before init ([`9a388f5`](https://github.com/custom-components/alexa_media_player/commit/9a388f502d47e618128aa0e79a1dc823802e078b))

* fix(guard): add additional checks for failed guard access ([`f84d2ba`](https://github.com/custom-components/alexa_media_player/commit/f84d2ba5111da73f767a04a49d75682c374e716f))

* fix(guard): schedule HA update after processing voice ([`e8ab5d1`](https://github.com/custom-components/alexa_media_player/commit/e8ab5d1693784ca315c5848d4155d29980ac8cc9))

* fix(guard): increase delay to check state on voice ([`a10d7e6`](https://github.com/custom-components/alexa_media_player/commit/a10d7e62171e16b52041b817ae7e11e09c0e3221))

* fix(guard): add 1s delay for guard state check after voice activity (#262) ([`4cc934c`](https://github.com/custom-components/alexa_media_player/commit/4cc934c073caf92ba402fa9f431a04f3dadb50fc))

* fix(media_player): alternative serial numbers not recognized for mobile app media player (#253)

* Fix last_called websocket handler to recognize appDeviceList serial numbers

* Fix last_called poll to recognize appDeviceList serial numbers ([`c560742`](https://github.com/custom-components/alexa_media_player/commit/c560742d0b9fc94b236a4c129b1b9b9b12af2a8f))

* fix(media_player): remove unused MEDIA_PLAYER_SCHEMA (#261) ([`5846371`](https://github.com/custom-components/alexa_media_player/commit/5846371b80e6b71225e5064c09fbc9913b98f41e))

### Style

* style(switch): clean up whitespace ([`021962d`](https://github.com/custom-components/alexa_media_player/commit/021962d8ba2a857226f1ddff8650943c124579cd))

* style(configurator): update messaging ([`04299d7`](https://github.com/custom-components/alexa_media_player/commit/04299d70ab51fbc81d2d94b91a1c2b7f5dbe7fe7))

### Unknown

* Merge pull request #271 from alandtse/1.4.0

Bump to 1.4.1 ([`94b5c57`](https://github.com/custom-components/alexa_media_player/commit/94b5c57929e0e2c0e0b0b39391c64dc1871273eb))

* Merge pull request #267 from alandtse/1.4.0

Update to 1.4.0 ([`5c161e6`](https://github.com/custom-components/alexa_media_player/commit/5c161e68eda3b2d6eb52b4891c284f49809617bc))

* Merge pull request #263 from alandtse/switches

 feat(switches): add switches for shuffle, dnd, and repeat ([`6b70764`](https://github.com/custom-components/alexa_media_player/commit/6b7076446c5069e068b5674bff1c6a1a9d5defdb))

* Add basic switch support (do not disturb, repeat, shuffle) ([`ff6483e`](https://github.com/custom-components/alexa_media_player/commit/ff6483e5997401cfced7afa635093ebcc87d289c))

* Fix TypeError exception for regions without Guard (#245) ([`2b26a12`](https://github.com/custom-components/alexa_media_player/commit/2b26a12d022a35c471a8b0443f26b58c968836f3))

* Sync dev with master (#252)

* Update issue templates

* Update location of version info

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`d1ed479`](https://github.com/custom-components/alexa_media_player/commit/d1ed479bcee849d4a9deabbf31397c7ec43feaa5))

* Sync dev with master (#246)

* Update issue templates

* Update location of version info

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`f0531e3`](https://github.com/custom-components/alexa_media_player/commit/f0531e35a289d22f75d75ccd22bbe624b84a0aae))


## v1.3.1 (2019-06-30)

### Unknown

* Merge pull request #237 from keatontaylor/dev

Update to 1.3.1 ([`4282211`](https://github.com/custom-components/alexa_media_player/commit/4282211e240b1faeb05db9e25efe674533fffa9a))

* Merge pull request #236 from alandtse/1.3.1

Bump version ([`b3852da`](https://github.com/custom-components/alexa_media_player/commit/b3852da91de7f90f9d9f83894cd012bd1611d306))

* Bump version ([`bac5fd4`](https://github.com/custom-components/alexa_media_player/commit/bac5fd4314aaf58cb0506a70548744cac81917e0))

* Merge pull request #235 from alandtse/#226

Update documentation and add documentation for hacs ([`c2caf5b`](https://github.com/custom-components/alexa_media_player/commit/c2caf5bbf101f2a7dfe56762e2d45ca818308c4f))

* Update documentation and add documentation for hacs ([`02808e6`](https://github.com/custom-components/alexa_media_player/commit/02808e689185deb27a2cf8104b0d949ab025a67f))

* Merge pull request #234 from alandtse/#226

Further fixes for #226 ([`f257151`](https://github.com/custom-components/alexa_media_player/commit/f257151d68dc8d4f0a1546d56206d270f01cc710))

* Fix spelling typo ([`24cba0c`](https://github.com/custom-components/alexa_media_player/commit/24cba0c90159cc0306c4c6f6ffc48ef4925e9703))

* Switch to exception catching to handle unexpected json ([`b8cbf87`](https://github.com/custom-components/alexa_media_player/commit/b8cbf87b8e405e9ae790feafc052f54bb35b3871))

* Fix bug where certain websocket messages improperly parsed ([`4b221dd`](https://github.com/custom-components/alexa_media_player/commit/4b221ddd97dc359e893574ae0a3a8a0c025ab7ab))

* Add check to skip uninitialized alarm_control_panel ([`a454856`](https://github.com/custom-components/alexa_media_player/commit/a454856ddfd0aaced48f9cd239226e5dc02920de))

* Merge pull request #227 from alandtse/#226

Add key checks for Alexa Guard to avoid errors in unsupported regions ([`a50580e`](https://github.com/custom-components/alexa_media_player/commit/a50580e22251fc9b1b013443560d2bf74e95231c))

* Add check for duplicate entity ([`f9d1d23`](https://github.com/custom-components/alexa_media_player/commit/f9d1d23f111dc7451461903cd966980f26e0f8f3))

* Add key error checks before access ([`a587e17`](https://github.com/custom-components/alexa_media_player/commit/a587e17940030d8c635bc1ec26d4409687dd90c6))

* Merge pull request #220 from keatontaylor/issue-templates

Update issue templates ([`c59d7c9`](https://github.com/custom-components/alexa_media_player/commit/c59d7c95044fa3f0fbd50b259b82b0e04c18ecf5))


## v1.3.0 (2019-06-23)

### Unknown

* Merge pull request #218 from keatontaylor/dev

Update to 1.3.0 ([`0ee204d`](https://github.com/custom-components/alexa_media_player/commit/0ee204d7000ef82e697deba13452351e74337ee3))

* Merge pull request #223 from alandtse/1.3.0

Bump alexapy to 0.7.0 ([`69e2442`](https://github.com/custom-components/alexa_media_player/commit/69e2442a9d99cd1f2ec406757744de0d2747d25d))

* Bump alexapy to 0.7.0 ([`ab10abc`](https://github.com/custom-components/alexa_media_player/commit/ab10abc04484dc9606130a6e03653d7daad4fc05))

* Update location of version info

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`03fbefa`](https://github.com/custom-components/alexa_media_player/commit/03fbefa5e4d411d159b00b2e8f8e0b2fb0ea35a8))

* Merge pull request #221 from alandtse/1.3.0

Add version info during startup logs ([`7c75daa`](https://github.com/custom-components/alexa_media_player/commit/7c75daa218abec27b2b8329f7e8e808574628b6f))

* Add version info during startup logs ([`a243ca6`](https://github.com/custom-components/alexa_media_player/commit/a243ca6f72fedd4ab6acf80261db736d5a90af65))

* Update issue templates ([`cf3c856`](https://github.com/custom-components/alexa_media_player/commit/cf3c856291ae2618d800f4a487b92c6597c50b89))

* Merge pull request #217 from alandtse/1.3.0

Update to 1.3.0 ([`79f1740`](https://github.com/custom-components/alexa_media_player/commit/79f1740c63f82506fea5b62fa54bf8b103a83c6d))

* Bump version to 1.3.0 ([`150b37e`](https://github.com/custom-components/alexa_media_player/commit/150b37e8d465710d1f4ba773d7d899d6aee97cb6))

* Add basic HACS support ([`6815bb6`](https://github.com/custom-components/alexa_media_player/commit/6815bb6ede811cf00f9848f8038ad52960800bcc))

* Merge branch &#39;master&#39; of https://github.com/xatr0z/alexa_media_player into hacs ([`9288e65`](https://github.com/custom-components/alexa_media_player/commit/9288e657324d3493e691ece9c5199927235fe15c))

* Merge pull request #216 from alandtse/remove_alexa_tts

Remove deprecated alexa_tts service ([`64820f9`](https://github.com/custom-components/alexa_media_player/commit/64820f90915cbb152758c66083bbae2b90d6deed))

* Remove deprecated alexa_tts service ([`be5477e`](https://github.com/custom-components/alexa_media_player/commit/be5477ed3bc6c0414c9b8b2352ae54a29fe01e20))

* Merge pull request #215 from alandtse/guard

Enable guard control (addresses #186) ([`5068101`](https://github.com/custom-components/alexa_media_player/commit/50681013fcc99eccf9246ccf14bfa0201e70273a))

* Bump alexapy requirement to 0.6.0 ([`55391bd`](https://github.com/custom-components/alexa_media_player/commit/55391bd5692c141379d964a83c78ce20ec1842f2))

* Merge pull request #191 from alandtse/#171

Remove references to async ([`e83781b`](https://github.com/custom-components/alexa_media_player/commit/e83781b14f1dd69b593b63bb464a9606e803ae29))

* Merge pull request #192 from alandtse/#180

Add check for existing entity ([`ade3dbb`](https://github.com/custom-components/alexa_media_player/commit/ade3dbb2de9e9a5f2d2a6b6c919137e2a8183dab))

* Merge pull request #193 from alandtse/#181

Add reconnect logic for websocket ([`e743ed9`](https://github.com/custom-components/alexa_media_player/commit/e743ed98df9a4b299f134a2138352b3cef421451))

* Move directory into custom_components ([`53e0d18`](https://github.com/custom-components/alexa_media_player/commit/53e0d1886983fead5fc2e927a67a0eb98226138e))

* Move directory into custom_components ([`9c103de`](https://github.com/custom-components/alexa_media_player/commit/9c103de138c6fb9a995b222b675e0f61414f748e))

* Missing imports ([`804aaeb`](https://github.com/custom-components/alexa_media_player/commit/804aaeba5725f347470cc61b294b2baf25d42da1))

* Clear alexa voice history ([`2042b85`](https://github.com/custom-components/alexa_media_player/commit/2042b85331d675a097809f084c599c8ce608e4d5))

* Remove unused constants ([`5fddebe`](https://github.com/custom-components/alexa_media_player/commit/5fddebea8a14cbc38c9bcd3e6d6afe044bd6fdaf))

* Clean up lint errors ([`6847fde`](https://github.com/custom-components/alexa_media_player/commit/6847fdeb79445bcd8a3a02b5cda8ce2216e43b90))

* Removing unused guard schema ([`cfe89d4`](https://github.com/custom-components/alexa_media_player/commit/cfe89d4993f33773279a72337af172925086b119))

* Remove guard services ([`8991ea4`](https://github.com/custom-components/alexa_media_player/commit/8991ea4263c052cdf2bc0c4aee1380f68e41c563))

* Add alarm_control_panel ([`e355757`](https://github.com/custom-components/alexa_media_player/commit/e355757ee68125b281a916d8e01c087390a6ecce))

* Add reconnect logic for websocket ([`4fbff19`](https://github.com/custom-components/alexa_media_player/commit/4fbff1993bd8706358565f64c48264a5323aa51f))

* Add check for existing entity ([`3940e5a`](https://github.com/custom-components/alexa_media_player/commit/3940e5a5df899c7ef308a35ef71ab34f71c6781d))

* Merge pull request #190 from keatontaylor/master

Syncing dev with master ([`6f04619`](https://github.com/custom-components/alexa_media_player/commit/6f04619009f850a75fc45d50a4cb8178065533fb))

* Fix indentation errors ([`4abf8a8`](https://github.com/custom-components/alexa_media_player/commit/4abf8a8790f1f79a0df99acfdf56d04e9b19909c))

* Remove all async calls ([`1277d76`](https://github.com/custom-components/alexa_media_player/commit/1277d7680feae04f1cf9e62c17bfb47150ddecc4))

* Add state parameter for set_guard_state description ([`68b534f`](https://github.com/custom-components/alexa_media_player/commit/68b534fde3053ae4a3ce5ae880ec67d19390410f))

* Add service descriptions ([`1274b61`](https://github.com/custom-components/alexa_media_player/commit/1274b61bd46e5b76c8020ba285669770056c73ba))

* Add initial guard mode get and set ([`915a2c3`](https://github.com/custom-components/alexa_media_player/commit/915a2c3703783eef8a6e44a8055b71ad94bc1b0d))

* Merge pull request #178 from keatontaylor/alandtse-patch-2

Add missing new files for custom_updater ([`3416df0`](https://github.com/custom-components/alexa_media_player/commit/3416df0543e66971801cb4bdbe724453a2840727))

* Add missing new files for custom_updater ([`379d3f8`](https://github.com/custom-components/alexa_media_player/commit/379d3f8738e1475876f8cbc72cbf2bf104e91b8e))


## v1.2.5 (2019-05-01)

### Unknown

* Merge pull request #176 from keatontaylor/alandtse-patch-1

Bump version for custom_components.json ([`d98bda3`](https://github.com/custom-components/alexa_media_player/commit/d98bda333b9420df5788853def26467da1c36f2b))

* Bump version for custom_components.json

Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`9d1ab25`](https://github.com/custom-components/alexa_media_player/commit/9d1ab25310620458ea0723a31f31bc7f59e15ccf))

* Merge pull request #175 from keatontaylor/dev

Update to 1.2.5 ([`27917ec`](https://github.com/custom-components/alexa_media_player/commit/27917ecea54900789fa71e45320d171c62e533b9))

* Merge pull request #174 from alandtse/dev

Update alexapy dependency to 0.5.0 ([`2bee315`](https://github.com/custom-components/alexa_media_player/commit/2bee315de5a94ac013734edc452346acb7a8f2f9))

* Update alexapy dependency to 0.5.0 ([`babdadb`](https://github.com/custom-components/alexa_media_player/commit/babdadb91d985df6493e66f320a84b98813ff139))

* Update README ([`c3d8858`](https://github.com/custom-components/alexa_media_player/commit/c3d8858afcb06babb898395211da6c34345e49f1))

* Bump version ([`3071faa`](https://github.com/custom-components/alexa_media_player/commit/3071faa0043e77f71b6ab839cecf523b8a5d0d08))

* Add feature to use devicePreference locale ([`26233f6`](https://github.com/custom-components/alexa_media_player/commit/26233f619cacbb5eca23d74b98e9dcd1453e9a45))

* Add required files for HA 0.92 ([`0a75511`](https://github.com/custom-components/alexa_media_player/commit/0a755117a73dbb8f990ee5e4037b20d2a6708675))

* Change source_list to return bluetooth profiles with A2DP-SOURCE ([`80922a0`](https://github.com/custom-components/alexa_media_player/commit/80922a0888b47e8cdf70ab2baa0919623e4b5cf6))

* Fix &#39;master&#39; custom_components.json ([`45a8ef8`](https://github.com/custom-components/alexa_media_player/commit/45a8ef870314069fbd963daecad698d855abf44c))

* Merge pull request #157 from tomhoover/master

Fix &#39;master&#39; custom_components.json ([`298a002`](https://github.com/custom-components/alexa_media_player/commit/298a002d761a3b867dbdaa717a5c88f8ac67c869))

* Fix &#39;master&#39; custom_components.json ([`29fecf3`](https://github.com/custom-components/alexa_media_player/commit/29fecf380219d0e0d58c508314ba80a3bdc9cd46))


## v1.2.4 (2019-04-08)

### Unknown

* Merge pull request #150 from keatontaylor/dev

Update master to 1.2.4 ([`a462ed7`](https://github.com/custom-components/alexa_media_player/commit/a462ed7ca0130ae2b6ccf086aade627eb891b28c))

* Update dev to 1.2.4 (#146)

* Adding bluetooth device updates from websockets.

* Add websocket checks to only trigger events for non-excluded serials

* Fix bug where new pairings were not updating source list

* Add dev info for customer_updater

* Bump alexapy dependency version and version

* Bump custom_updater version ([`af1b4c5`](https://github.com/custom-components/alexa_media_player/commit/af1b4c5beae943e464b7d600840b97fd56aed670))

* Allow autoloading of notify component (#140)

* Conform logging to avoid info per HA requirements

* Add autoloading of notify component ([`8eb0db6`](https://github.com/custom-components/alexa_media_player/commit/8eb0db6403b41bc70be3692fac2cb1272eba3f0c))

* Bluetooth Websocket  (#138)

* Adding bluetooth device updates from websockets.

* Add websocket checks to only trigger events for non-excluded serials (#139)

* Add websocket checks to only trigger events for non-excluded serials

* Fix bug where new pairings were not updating source list ([`72bb8d6`](https://github.com/custom-components/alexa_media_player/commit/72bb8d6039d26ea2bcbcf09cf18379bf8d16df6e))

* Merge alandtse/dev (#136)

* Correct typo and comment for DOPPLER

* Simplify dopplerConnectionState test

* Disable manual updates if websocket enabled

* Fix bug where disconnect would clear known devices

* Fix incorrect use of DOMAIN instead of DATA_ALEXAMEDIA

* Add code to disable update_devices polling when websockets enabled

* Update comments to reflect changes

* Update websocket to add new devices

* Add forced update_devices after detection of new device

* Fix bug where multiple reconnects would spawn multiple update_devices ([`0141758`](https://github.com/custom-components/alexa_media_player/commit/0141758815168fc40f3969c1fc4b46653eaa80cf))

* Add support for updating the players online state from websocket messages (#134) ([`3612166`](https://github.com/custom-components/alexa_media_player/commit/36121664b4023448aba176cd68215a02edc1e04c))

* Add support for updating the players online state from websocket messages.. ([`c6f8f4e`](https://github.com/custom-components/alexa_media_player/commit/c6f8f4e690196b750ba1664049f675f0e94cda3e))


## v1.2.3 (2019-03-20)

### Unknown

* Update to 1.2.3 (#131) ([`31c2cb9`](https://github.com/custom-components/alexa_media_player/commit/31c2cb95cc0e38134aadfcec4d9d8b04e6a65404))

* Update to 1.2.3 (#130)

* Add code to handle websocket error and close callbacks

* Fix bug where polling would not resume after websocket failure

* Bump custom_updater version ([`a4d001b`](https://github.com/custom-components/alexa_media_player/commit/a4d001b724be1b54d96a464979fd1e0ba25d74c3))


## v1.2.2 (2019-03-17)

### Unknown

* Update to 1.2.2 (#126) ([`bd48da1`](https://github.com/custom-components/alexa_media_player/commit/bd48da1c336e133fc5bbb084430f3c73f1de41e4))

* Bump version for custom_updater ([`04ab7db`](https://github.com/custom-components/alexa_media_player/commit/04ab7dbadc24e09e62d529a3c264fb0fd4fd4ddb))

* Update README ([`edb98f4`](https://github.com/custom-components/alexa_media_player/commit/edb98f4c0e2ba3cd16a31d83d39d93832f3cbefa))

* Remove alexapy submodule ([`2fadfd2`](https://github.com/custom-components/alexa_media_player/commit/2fadfd274e1bb2c2b4b6209d1188766a2a91e4fd))

* Add websocket support ([`32fb2d6`](https://github.com/custom-components/alexa_media_player/commit/32fb2d6db2e95d3c36e37d175fb4086cfb6a1ed2))

* Add initial websocket support ([`a1f4259`](https://github.com/custom-components/alexa_media_player/commit/a1f42596cd57f62851443c0ffee742d6cc49a263))


## v1.2.1 (2019-03-13)

### Unknown

* Update to 1.2.1 (#120) ([`8dbd8f5`](https://github.com/custom-components/alexa_media_player/commit/8dbd8f58b35b0cc4583bcc4de21ca18e647e33ed))

* Bump version ([`282bf91`](https://github.com/custom-components/alexa_media_player/commit/282bf91eb602246be112272e631ad206fe918d57))

* Fix bug where any invalid target would stop service call ([`b2ec297`](https://github.com/custom-components/alexa_media_player/commit/b2ec297e019fb2eec8485a68a022160559b6e81d))

* Improve logging statements ([`cb70a17`](https://github.com/custom-components/alexa_media_player/commit/cb70a17ecf3d5a29c117f9cbccbbd32235a538a8))

* Fix bug where announce had invalid targets ([`ae738e6`](https://github.com/custom-components/alexa_media_player/commit/ae738e628dac7e000a6e85e91e0aef70b753fee0))


## v1.2.0 (2019-03-12)

### Unknown

* Fix bug where entities would be filtered by convert ([`4b9701f`](https://github.com/custom-components/alexa_media_player/commit/4b9701f61023b3252e915f0295b2b157705fe188))

* Fix bug where entities would be filtered by convert ([`ccc830d`](https://github.com/custom-components/alexa_media_player/commit/ccc830d42c6e22318187c59ae7eef235096ce0e0))

* Fix custom_component.json ([`05a40aa`](https://github.com/custom-components/alexa_media_player/commit/05a40aae1c267ce5a3609f2ab751f0bc56dfbbec))

* Fix references for custom_updater ([`72eb0da`](https://github.com/custom-components/alexa_media_player/commit/72eb0da4b7c2560a0d02ded0fbc9d7d0803da94a))

* Update custom_components to add notify.py ([`81900d5`](https://github.com/custom-components/alexa_media_player/commit/81900d5f588c63977f6fbbcc8a1042b4002f38c1))

* Merge pull request #111 from keatontaylor/next

Update to 1.2.0 (#110) ([`4667f91`](https://github.com/custom-components/alexa_media_player/commit/4667f91428bbace6f0e2515ca14ed7034f4caa31))

* Update to 1.2.0 (#110)

* Add initial notify service with working tts

* Add announcement notify feature

* Change logging level for messages

* Add mobilepush functionality

* Bump version

* Add group support to notify

* Fix pylint errors

* Bump custom_component version ([`68c151c`](https://github.com/custom-components/alexa_media_player/commit/68c151ca3b4e0a2991934ce4fbb475cbd46cb897))


## v1.1.0 (2019-03-01)

### Unknown

* Update to 1.1.0 (#105)

* Truncate event data to 32 chars (#89)

* Fix display of media position while playing (#92)

* Add custom_updater support (#95)

* Fix multiaccount bugs (#100)

* Fix bug where configurator would fail if no options for verification method (#103)

* Update to alexapy 0.2.1 (#96) ([`8b5af65`](https://github.com/custom-components/alexa_media_player/commit/8b5af65a9ac0fc25caf08bc9579ee12cf26acb84))

* Update to breaking feature branch 1.0.0 (#73) ([`cc09f1a`](https://github.com/custom-components/alexa_media_player/commit/cc09f1a6bba0747da1445765cf8df13e346c8707))


## v0.10.2 (2019-02-21)

### Unknown

* Fix for HA 0.88.0 architecture change (#77) ([`cfa34c8`](https://github.com/custom-components/alexa_media_player/commit/cfa34c89e103a3d6528323bec38bbe873cc7fb57))

* Fix typo in last_activity call

Resolves #68 ([`3987b4d`](https://github.com/custom-components/alexa_media_player/commit/3987b4dd57e13fba2e5f9938c1cf2f48e65447e9))

* Fix typo in last_activity call

This resolves #68. 
Signed-off-by: Alan Tse &lt;alandtse@gmail.com&gt; ([`63237be`](https://github.com/custom-components/alexa_media_player/commit/63237be3632f9ed655b8ca9accfeb14d3e020001))

* Bump version (#67) ([`b5c0ef3`](https://github.com/custom-components/alexa_media_player/commit/b5c0ef34c44c20e5ad37103ae4d17e2db572f6d0))

* adding last_called attribute (#65)

This will add the ability to query whether the specific Alexa device was the last one to respond to a spoken request

* &#39;git reset --hard upstream/master&#39;; reapplied changes

* fix: ignore discarded activity records

* removed orphaned code + optimizations per @alandtse&#39;s request

* refactored get_last_device_serial() ([`fa8cfb7`](https://github.com/custom-components/alexa_media_player/commit/fa8cfb78714d4cf76d2b9d934b7d33afeedf4714))

* Use logged in customerId instead of deviceOwnerCustomerId for tts and play_music (#59) ([`b59aeba`](https://github.com/custom-components/alexa_media_player/commit/b59aeba0614ffbd803cb50b62ed4acd7394a6e59))

* Merge pull request #53 from keatontaylor/alandtse-patch-1

Bump version ([`71d8357`](https://github.com/custom-components/alexa_media_player/commit/71d8357c8d271cc46c90f39219f066d9c0d02b7e))

* Bump version ([`712a27f`](https://github.com/custom-components/alexa_media_player/commit/712a27f99a4cf877fd604a4f134d298e4e729269))

* Implement include/exclude device lists (#45) ([`cf30287`](https://github.com/custom-components/alexa_media_player/commit/cf3028728bb30775a9ba11048e291986d7ef5018))

* Change refresh to online devices only (#30) ([`4b96ec8`](https://github.com/custom-components/alexa_media_player/commit/4b96ec88c6158825e727fa932ec7cde099147b1f))

* Fix get_bluetooth to use .json exception catching in AlexaAPI (#40)

* Fix get_bluetooth to use .json exception catching in AlexaAPI

* Fix get_state to catch .json error in AlexaAPI ([`94f5c8d`](https://github.com/custom-components/alexa_media_player/commit/94f5c8d0c7ea6cb0108fcf6bfb6fd1abeb294233))

* Fix #35 (#36) ([`7e10200`](https://github.com/custom-components/alexa_media_player/commit/7e10200739581f27adf9cff13c3f5cdb7b259ee6))

* Handle Amazon verification pages (#34)

* Replacing lxml parser with html for hassio; adding require for simplejson

* Adding 2FA

* Adding existence checks for nested dictionaries to resolve #21

* Adding output files

* Updating debug files

* Change initial login to Alexa specific site

* Switch login url to alexa site

* Updating to 0.9.1 and adding proper referer

* Add checking for nested dictionaries for media state

* Add onlineonly filter option

* Add additional debugging; remove unicode string references

* Forcing unicode encoding

* Add check for verification code

* Add processing of verificationcode

* Handle verify action

* Fix verify url

* Add processing of verification code

* Add debug option; fix modal orphans ([`59ebab0`](https://github.com/custom-components/alexa_media_player/commit/59ebab08654d8c7eaa15075fa62d692f2030a465))

* Add checking for nested dictionaries for media state (#29)

* Replacing lxml parser with html for hassio; adding require for simplejson

* Adding 2FA

* Switch login url to alexa site

* Add checking for nested dictionaries for media state ([`6fe32c8`](https://github.com/custom-components/alexa_media_player/commit/6fe32c8a8f1c752afd3c35deef42941eb0f1b14c))

* Revert &#34;Move API code to the alexapy pip package and add references to objects and datasets that are needed&#34;

This reverts commit 18dd6138c6075a9aee2cfb4600091d4ea90ed4c2. ([`0c3052e`](https://github.com/custom-components/alexa_media_player/commit/0c3052ee424a3da9c1f63e60b35e3ade7272242c))

* Move API code to the alexapy pip package and add references to objects and datasets that are needed ([`18dd613`](https://github.com/custom-components/alexa_media_player/commit/18dd6138c6075a9aee2cfb4600091d4ea90ed4c2))

* Switch login site to Alexa sign-in site (#24)

* Replacing lxml parser with html for hassio; adding require for simplejson

* Adding 2FA

* Switch login url to alexa site ([`d5b561b`](https://github.com/custom-components/alexa_media_player/commit/d5b561bcadba4cb7fe1154ea8a3df10b07c4ad4c))

* Adding existence checks for nested dictionaries. (#23)

* Replacing lxml parser with html for hassio; adding require for simplejson

* Adding 2FA

* Adding existence checks for nested dictionaries to resolve #21 ([`9a6d517`](https://github.com/custom-components/alexa_media_player/commit/9a6d5174e9b6e7e5e237b98f1d05781017c1e92d))

* Adding 2FA (#22)

* Replacing lxml parser with html for hassio; adding require for simplejson

* Adding 2FA ([`912ffe3`](https://github.com/custom-components/alexa_media_player/commit/912ffe3dfedf43e142a89c846a0d2156467c191c))

* Replacing lxml parser with html for hassio; adding require for simplejson (#19) ([`8a28d62`](https://github.com/custom-components/alexa_media_player/commit/8a28d622f42f4db8a1b121cf6bf1adf8ddf61c15))

* Merge pull request #11 from alandtse/master

Fixes for JSONDecodeError and other misc issues. ([`b1314da`](https://github.com/custom-components/alexa_media_player/commit/b1314da54dfd60a4923d73e6da93432f4e20308c))

* Fix JSONDecodeError for Python version that uses simplejson and linter errors ([`09b0b81`](https://github.com/custom-components/alexa_media_player/commit/09b0b81a44bcfea1f3103c513a424332faffef64))

* Merge pull request #13 from keatontaylor/license-fix

migrate to apache 2.0 ([`945649c`](https://github.com/custom-components/alexa_media_player/commit/945649c7e759e75ba66d308205aaa8c739afdd0d))

* migrate to apache 2.0 ([`ab5ccde`](https://github.com/custom-components/alexa_media_player/commit/ab5ccdec12496210dc873291f26ca172453ba63b))

* Addressing requested on line length and removing lock ([`b80c1d6`](https://github.com/custom-components/alexa_media_player/commit/b80c1d67827374571b78b7027c89403326283f74))

* Merge branch &#39;cookie&#39; ([`9dd771b`](https://github.com/custom-components/alexa_media_player/commit/9dd771bb907c39bf7e0e47ccd461d13090d4aab7))

* Merge branch &#39;configurator&#39; ([`49da51f`](https://github.com/custom-components/alexa_media_player/commit/49da51f4da51a399a36b69924636352d461ca3ae))

* Adding cookie support for persistent logins ([`f32ad03`](https://github.com/custom-components/alexa_media_player/commit/f32ad0384bd738c33b8542a8d0d0595eed591b8d))

* Adding failure notification to configurator ([`94b7f7e`](https://github.com/custom-components/alexa_media_player/commit/94b7f7ef357e1f8bb9890e749cf3f754d1dece14))

* Adding check for mediaArt url ([`190997f`](https://github.com/custom-components/alexa_media_player/commit/190997fe34dc2245dec627fddcab62a5f377d041))

* Fixing log-in test to properly check for json using exceptions ([`dd1ff8b`](https://github.com/custom-components/alexa_media_player/commit/dd1ff8be82c651587e3d4d2be5b2495b93ca5753))

* Fixing typo of captcha ([`36f0ef8`](https://github.com/custom-components/alexa_media_player/commit/36f0ef8ea0e0c250a7fb7e15578088d5ab6bcfc1))

* Updating requirements for lxml ([`feeff0b`](https://github.com/custom-components/alexa_media_player/commit/feeff0b08bfee8716674ee38864a90083a4b4d3a))

* Merge pull request #8 from keatontaylor/login

potential fix for the login issues in other locales ([`d78c4a4`](https://github.com/custom-components/alexa_media_player/commit/d78c4a4a141069da76427c573be2a3356cdbaade))

* Merge branch &#39;master&#39; into login ([`00cbb72`](https://github.com/custom-components/alexa_media_player/commit/00cbb725c65662109f6424dbefdcd6622e585c47))

* Merge pull request #7 from keatontaylor/play_media

Play media ([`8ae4d6e`](https://github.com/custom-components/alexa_media_player/commit/8ae4d6ed1c9b967a04f87bac2d49f9a43b9594eb))

* potential fix for the login issues in other locales ([`9ae79b7`](https://github.com/custom-components/alexa_media_player/commit/9ae79b768bef97db36a4c407f93f47d9edb6e629))

* bump version ([`cdb0687`](https://github.com/custom-components/alexa_media_player/commit/cdb0687ffc61339fc843d207dca2ba74c678295d))

* play media support ([`ec9fc9b`](https://github.com/custom-components/alexa_media_player/commit/ec9fc9b9d652e87acaea744227005b12ac2df2c1))

* Merge pull request #5 from keatontaylor/addon-removal

Addon removal ([`1580d05`](https://github.com/custom-components/alexa_media_player/commit/1580d050150714784dff4c5feb0b6d226901de25))

* bump version ([`81da223`](https://github.com/custom-components/alexa_media_player/commit/81da22379fd040fede23a2d7241e6f711d351bcd))

* fix for bs4 dependency installation ([`60d1862`](https://github.com/custom-components/alexa_media_player/commit/60d186291b876bd75874b31403ab8f2cfcad89c6))

* Merge pull request #4 from keatontaylor/addon-removal

remove dsstore ([`f14a1d6`](https://github.com/custom-components/alexa_media_player/commit/f14a1d65a9a2f50d6cc3923b4ea9a8f657b7f90f))

* remove dsstore ([`1cf87ea`](https://github.com/custom-components/alexa_media_player/commit/1cf87eaeb98fcc1bea36f391c73feca3d5d49614))

* Merge pull request #3 from keatontaylor/addon-removal

code to completely remove the need for the add-on ([`61bcdb2`](https://github.com/custom-components/alexa_media_player/commit/61bcdb2820ab18280ccae4a73fd1617bbf85e274))

* code to completely remove the need for the add-on ([`27ed6dc`](https://github.com/custom-components/alexa_media_player/commit/27ed6dc4addfe3d5ef9389154ccb990bb559892b))

* Merge pull request #2 from keatontaylor/bluetooth

Bluetooth ([`1685b12`](https://github.com/custom-components/alexa_media_player/commit/1685b1239c0b106643300a9ee31d83f8a9485c1d))

* Add bluetooth disconnect controls. ([`6cc8331`](https://github.com/custom-components/alexa_media_player/commit/6cc83310f7ca5c68df695f452ea7189c53f901d9))

* Requests wrapper and additions for selecting a bluetooth device from the source selection box ([`259b5d8`](https://github.com/custom-components/alexa_media_player/commit/259b5d854c5223373c1d4bc9bc192db143c5fd9f))

* Changed endpoint for media to allow support for getting playback information for other music services like spotify and tune-in ([`2cb9d12`](https://github.com/custom-components/alexa_media_player/commit/2cb9d12153bcd4e64b45e0973e259828cfd27c19))

* Adding host config for non hassio users ([`9ee84f8`](https://github.com/custom-components/alexa_media_player/commit/9ee84f8b0bb2ad53ec77c7bb66757360aad05393))

* inital commit of custom component ([`45c7309`](https://github.com/custom-components/alexa_media_player/commit/45c7309221e8fe5a2bd60c58dea201fad3676001))

* Initial commit ([`027f1bc`](https://github.com/custom-components/alexa_media_player/commit/027f1bc9fb38ab944037c5c83aa123fe61503be5))
