# Release note PR author attribution

Python Semantic Release v10.2.0 generates release notes using its built-in
templates. Its template context has commit metadata and PR references, but no
GitHub PR authors. After a new release, a GitHub Script step looks up each linked
PR and adds its author's linked username beside the PR reference:

```markdown
- Fix a bug ([#123](https://github.com/alandtse/alexa_media_player/pull/123) by [@username](https://github.com/username), [`abcdef0`](commit-url))
```

The script reads `pull.user` from GitHub's API, crediting the PR author rather
than the commit author or merger. Each PR is fetched once. Existing categories,
text, commit links, notices and comparison links are preserved. There is no
Contributors section.

Only PR links for the current repository are enriched. Entries without a PR,
deleted authors and unsuccessful lookups retain their original text. Attribution
is optional: release read/write errors remain visible in Actions but do not stop
asset upload and branch synchronization. Reprocessing the same body does not
duplicate attribution.

The step uses the existing `GH_TOKEN`, gated on PSR's `released` output, targeting
its exact `tag` output. Versioning, release selection, assets and branch strategy
are unchanged. The checked-in changelog keeps PSR's default output. Only future
GitHub release bodies are enriched; historical releases are not edited by this PR.

Run the mocked API regression tests with Node.js 20 or newer:

```sh
node --test .github/tests/attribute-release-notes.test.cjs
```

These tests also run in the Release note attribution tests workflow.
