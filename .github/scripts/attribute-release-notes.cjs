// Enrich PSR's PR references without replacing its release-note rendering.
module.exports = async ({ github, context, core, tag }) => {
  const repo = context.repo;
  const { data: release } = await github.rest.repos.getReleaseByTag({
    ...repo,
    tag,
  });
  const original = release.body || "";
  const authors = new Map();
  const references = /\[#(\d+)\]\((https:\/\/github\.com\/[^\s)]+)\)/g;
  let body = "";
  let cursor = 0;
  for (const match of original.matchAll(references)) {
    body += original.slice(cursor, match.index) + match[0];
    cursor = match.index + match[0].length;
    const url = new URL(match[2]);
    const expected = `/${repo.owner}/${repo.repo}/pull/${match[1]}`;
    if (
      url.pathname.toLowerCase() !== expected.toLowerCase() ||
      url.search ||
      url.hash ||
      original.slice(cursor).startsWith(" by [@")
    ) {
      continue;
    }
    const number = Number(match[1]);
    if (!authors.has(number)) {
      authors.set(number, null);
      try {
        const { data: pull } = await github.rest.pulls.get({
          ...repo,
          pull_number: number,
        });
        const user = pull.user;
        if (
          user &&
          /^[a-z\d-]+(?:\[bot\])?$/i.test(user.login) &&
          /^https:\/\/github\.com\/[a-z\d/-]+$/i.test(user.html_url)
        ) {
          const label = user.login.replace(/([\[\]])/g, "\\$1");
          authors.set(number, ` by [@${label}](${user.html_url})`);
        }
      } catch (error) {
        core.warning(`Could not attribute PR #${number}: ${error.message}`);
      }
    }
    body += authors.get(number) || "";
  }
  body += original.slice(cursor);
  if (body !== original) {
    await github.rest.repos.updateRelease({
      ...repo,
      release_id: release.id,
      body,
    });
  }
  return body;
};
