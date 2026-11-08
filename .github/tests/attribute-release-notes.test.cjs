const assert = require("node:assert/strict");
const { test } = require("node:test");
const attribute = require("../scripts/attribute-release-notes.cjs");
const repo = { owner: "alandtse", repo: "alexa_media_player" };
const pr = (n) =>
  `[#${n}](https://github.com/alandtse/alexa_media_player/pull/${n})`;
const author = (login) => ({ login, html_url: `https://github.com/${login}` });
function fixture(body, users = {}) {
  const calls = { pulls: [], updates: [], warnings: [] };
  const args = {
    context: { repo },
    core: { warning: (message) => calls.warnings.push(message) },
    tag: "v5.20.0",
    github: {
      rest: {
        repos: {
          getReleaseByTag: async (input) => {
            assert.deepEqual(input, { ...repo, tag: "v5.20.0" });
            return { data: { id: 123, body } };
          },
          updateRelease: async (input) => calls.updates.push(input),
        },
        pulls: {
          get: async (input) => {
            calls.pulls.push(input);
            const value = users[input.pull_number];
            if (value instanceof Error) throw value;
            return { data: { user: value } };
          },
        },
      },
    },
  };
  return { args, calls };
}
test("attributes PR authors and preserves all other Markdown", async () => {
  const original = `## v5.20.0\n\n### Features\n\n- Feature (${pr(3678)}, [\`abc1234\`](commit-url)).\n\n### Bug Fixes\n\n- Bug (${pr(3665)}).\n\n### Breaking Changes\n\n- Migrate setting.\n\n---\n\n**Detailed Changes**: comparison\n`;
  const { args, calls } = fixture(original, {
    3678: author("danielbrunt57"),
    3665: author("another-author"),
  });
  const actual = await attribute(args);
  assert.equal(
    actual,
    original
      .replace(
        pr(3678),
        `${pr(3678)} by [@danielbrunt57](https://github.com/danielbrunt57)`,
      )
      .replace(
        pr(3665),
        `${pr(3665)} by [@another-author](https://github.com/another-author)`,
      ),
  );
  assert.deepEqual(calls.updates, [{ ...repo, release_id: 123, body: actual }]);
  assert.ok(!actual.includes("Contributors"));
});
test("caches repeated PRs and is idempotent", async () => {
  const { args, calls } = fixture(`${pr(10)}\n${pr(10)}`, {
    10: author("alice"),
  });
  const actual = await attribute(args);
  assert.equal(calls.pulls.length, 1);
  assert.equal(actual.split(" by [@alice]").length, 3);
  const repeated = fixture(actual);
  assert.equal(await attribute(repeated.args), actual);
  assert.equal(repeated.calls.pulls.length, 0);
  assert.equal(repeated.calls.updates.length, 0);
});
test("leaves direct commits, foreign links and empty notes unchanged", async () => {
  for (const body of [
    null,
    "",
    "- Direct commit (`abcdef0`)",
    "[#10](https://github.com/other/project/pull/10)",
    `${pr(10).slice(0, -1)}?query=true)`,
  ]) {
    const { args, calls } = fixture(body);
    assert.equal(await attribute(args), body || "");
    assert.equal(calls.pulls.length, 0);
    assert.equal(calls.updates.length, 0);
  }
});
test("failed lookups and deleted users do not prevent other attribution", async () => {
  const original = `${pr(1)}\n${pr(1)}\n${pr(2)}\n${pr(3)}`;
  const { args, calls } = fixture(original, {
    1: new Error("API unavailable"),
    2: null,
    3: author("bob"),
  });
  assert.equal(
    await attribute(args),
    original.replace(pr(3), `${pr(3)} by [@bob](https://github.com/bob)`),
  );
  assert.equal(calls.pulls.length, 3);
  assert.equal(calls.warnings.length, 1);
});
test("supports bots and rejects unsafe profile metadata", async () => {
  const { args } = fixture(pr(1), {
    1: {
      login: "dependabot[bot]",
      html_url: "https://github.com/apps/dependabot",
    },
  });
  assert.equal(
    await attribute(args),
    `${pr(1)} by [@dependabot\\[bot\\]](https://github.com/apps/dependabot)`,
  );
  for (const user of [
    author("bad](link)"),
    { login: "alice", html_url: "https://example.com/alice" },
  ]) {
    const invalid = fixture(pr(1), { 1: user });
    assert.equal(await attribute(invalid.args), pr(1));
    assert.equal(invalid.calls.updates.length, 0);
  }
});
test("read/write errors surface to the optional workflow step", async () => {
  const read = fixture(pr(1));
  read.args.github.rest.repos.getReleaseByTag = async () => {
    throw new Error("read failed");
  };
  await assert.rejects(attribute(read.args), /read failed/);
  const write = fixture(pr(1), { 1: author("alice") });
  write.args.github.rest.repos.updateRelease = async () => {
    throw new Error("write failed");
  };
  await assert.rejects(attribute(write.args), /write failed/);
});
