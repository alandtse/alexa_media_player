"""Exercise attribution with the actual pinned PSR renderer and release command."""

import importlib.util
from pathlib import Path
import re
from types import SimpleNamespace
from unittest.mock import Mock

from click.testing import CliRunner
from git import Actor, Git, Repo
import pytest
import requests
from semantic_release.changelog.release_history import ReleaseHistory
from semantic_release.cli.commands.main import main as semantic_release
from semantic_release.cli.config import (
    GlobalCommandLineOptions,
    RawConfig,
    RuntimeContext,
)
from semantic_release.cli.util import load_raw_config_file
from semantic_release.gitproject import GitProject
from semantic_release.hvcs import Github

spec = importlib.util.spec_from_file_location(
    "prepare", Path(__file__).parents[1] / "scripts/prepare-release-notes.py"
)
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


def user(login):
    """Return valid GitHub user metadata."""
    return {"login": login, "html_url": f"https://github.com/{login}"}


def client_for(users):
    """Mock PR lookups for the supplied author records."""
    client = Mock()

    def get(url, timeout):
        """Return the configured response for a PR lookup."""
        assert timeout == 30
        number = int(url.rsplit("/", 1)[1])
        value = users[number]
        response = Mock(status_code=200)
        if isinstance(value, Exception):
            response.raise_for_status.side_effect = value
        elif value == 404:
            response.status_code = 404
        else:
            response.json.return_value = {"user": value}
        return response

    client.get.side_effect = get
    return client


def history_for(*references):
    """Build unreleased parsed commits for lookup tests."""
    return SimpleNamespace(
        unreleased={
            "fix": [
                SimpleNamespace(hexsha=str(i), linked_merge_request=reference)
                for i, reference in enumerate(references)
            ]
        }
    )


def test_actual_pr_author_cache_direct_commits_and_missing_users():
    """Verify actual pr author cache direct commits and missing users."""
    history = history_for("#10", "#10", "", "#11", "#12", "!13", "#0")
    client = client_for({10: user("alice"), 11: None, 12: 404})
    authors = prepare.collect_authors(history, client, "owner", "repo")
    assert authors == {
        "0#10": " by [@alice](https://github.com/alice)",
        "1#10": " by [@alice](https://github.com/alice)",
    }
    assert client.get.call_count == 3
    assert all(
        "/repos/owner/repo/pulls/" in c.args[0] for c in client.get.call_args_list
    )


def test_same_sha_distinct_prs_keep_separate_authors():
    """One squash commit parsed into multiple records must credit each PR author.

    PSR 10.2.0 can emit several parsed records that share a commit SHA but carry
    different linked PR references. Keying the snapshot by SHA alone let the last
    record overwrite earlier ones, so every PR link showed the same author.
    """
    shared_sha = "abcdef1234567890"
    history = SimpleNamespace(
        unreleased={
            "fix": [
                SimpleNamespace(hexsha=shared_sha, linked_merge_request="#10"),
                SimpleNamespace(hexsha=shared_sha, linked_merge_request="#11"),
            ]
        }
    )
    client = client_for({10: user("alice"), 11: user("bob")})
    authors = prepare.collect_authors(history, client, "owner", "repo")
    assert authors == {
        f"{shared_sha}#10": " by [@alice](https://github.com/alice)",
        f"{shared_sha}#11": " by [@bob](https://github.com/bob)",
    }


@pytest.mark.parametrize(
    "metadata",
    [
        None,
        {},
        user("bad](link)"),
        {"login": "alice", "html_url": "https://example.com/alice"},
        {"login": "alice", "html_url": "https://github.com/someone-else"},
        {"login": [], "html_url": None},
        {"login": "alice", "html_url": "https://github.com/alice?x=y"},
    ],
)
def test_invalid_metadata(metadata):
    """Verify invalid metadata."""
    assert prepare.author_link(metadata) == ""


def test_bots():
    """Verify bots."""
    assert (
        prepare.author_link(
            {
                "login": "dependabot[bot]",
                "html_url": "https://github.com/apps/dependabot",
            }
        )
        == " by [@dependabot\\[bot\\]](https://github.com/apps/dependabot)"
    )


@pytest.mark.parametrize(
    "error",
    [
        requests.HTTPError(response=Mock(status_code=status))
        for status in [401, 403, 422, 429, 500, 502, 503, 504]
    ]
    + [
        requests.ConnectionError("offline"),
        requests.Timeout("timed out"),
        requests.exceptions.RetryError("retries exhausted"),
    ],
)
def test_api_failure_discards_partial_authors(error, capsys):
    """Warn and discard the whole snapshot when any lookup fails."""
    client = client_for({10: user("alice"), 11: error, 12: user("bob")})
    assert (
        prepare.collect_authors(
            history_for("#10", "#11", "#12"), client, "owner", "repo"
        )
        == {}
    )
    assert client.get.call_count == 2
    assert "::warning::PR #11: author lookup failed" in capsys.readouterr().out


@pytest.mark.parametrize("payload", [None, [], "unexpected", 123])
def test_non_object_response_falls_back(payload, capsys):
    """Treat malformed API payloads as cosmetic lookup failures."""
    client = Mock()
    response = Mock(status_code=200)
    response.json.return_value = payload
    client.get.return_value = response
    assert prepare.collect_authors(history_for("#10"), client, "owner", "repo") == {}
    assert "::warning::PR #10: author lookup failed" in capsys.readouterr().out


def test_invalid_json_falls_back(capsys):
    """Continue without attribution when GitHub returns invalid JSON."""
    client = Mock()
    response = Mock(status_code=200)
    response.json.side_effect = requests.exceptions.JSONDecodeError(
        "Invalid JSON", "bad", 0
    )
    client.get.return_value = response
    assert prepare.collect_authors(history_for("#10"), client, "owner", "repo") == {}
    assert "::warning::PR #10: author lookup failed" in capsys.readouterr().out


@pytest.fixture
def project(tmp_path, monkeypatch):
    """Create a temporary release repository with representative commits."""
    monkeypatch.chdir(tmp_path)
    repo = Repo.init(tmp_path, initial_branch="master")
    repo.create_remote("origin", "https://github.com/alandtse/alexa_media_player.git")
    with repo.config_writer() as config:
        config.set_value("user", "name", "Release tester")
        config.set_value("user", "email", "tester@example.com")
    Path("pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "1.0.0"\n'
        '[tool.semantic_release]\nversion_toml = ["pyproject.toml:project.version"]\n'
        '[tool.semantic_release.changelog]\ntemplate_dir = ".github/.release-templates"\n'
        "[tool.semantic_release.changelog.environment]\nautoescape = false\n"
    )
    old = "# CHANGELOG\n\n<!-- version list -->\n\n## v1.0.0 (2020-01-01)\n\n- Historical text.\n"
    Path("CHANGELOG.md").write_text(old, newline="\n")
    repo.index.add(["pyproject.toml", "CHANGELOG.md"])
    repo.index.commit("chore: initial")
    repo.create_tag("v1.0.0")
    commits = []
    for message in [
        "fix: repair playback (#10)",
        "feat(audio): support groups (#11)\n\nNOTICE: Restart once.",
        "fix: another playback fix (#10)",
        "docs: improve guide & examples (#12)",
        "fix: direct commit",
    ]:
        Path("example.txt").write_text(message)
        repo.index.add(["example.txt"])
        commits.append(
            repo.index.commit(message, author=Actor("Merger", "merge@example.com"))
        )
    return repo, old, commits


def runtime_and_history(repo):
    """Load the configured PSR runtime and parsed release history."""
    runtime = RuntimeContext.from_raw_config(
        RawConfig.model_validate(load_raw_config_file(Path("pyproject.toml"))),
        GlobalCommandLineOptions(),
    )
    history = ReleaseHistory.from_git_history(
        repo,
        runtime.version_translator,
        runtime.commit_parser,
        runtime.changelog_excluded_commit_patterns,
    )
    return runtime, history


def run_release(monkeypatch):
    """Run PSR locally while capturing remote pushes and publication."""
    published = []
    pushes = []
    monkeypatch.setattr(
        GitProject, "git_push_branch", lambda *a, **kw: pushes.append(kw)
    )
    monkeypatch.setattr(GitProject, "git_push_tag", lambda *a, **kw: pushes.append(kw))
    monkeypatch.setattr(Github, "create_release", lambda *a, **kw: published.append(kw))
    result = CliRunner().invoke(semantic_release, ["version", "--skip-build"])
    assert result.exit_code == 0, result.output + repr(result.exception)
    return published, pushes


def normalize(text):
    """Collapse wrapping differences for content comparisons."""
    return " ".join(text.split())


def test_real_release_commits_changelog_and_publishes_same_authors(
    project, monkeypatch
):
    """Verify real release commits changelog and publishes same authors."""
    repo, old, commits = project
    _, history = runtime_and_history(repo)
    client = client_for({10: user("alice"), 11: user("bob"), 12: None})
    authors = prepare.collect_authors(history, client, "alandtse", "alexa_media_player")
    prepare.prepare_templates(prepare.TEMPLATE_DIR, authors)
    # Preparing twice overwrites the snapshot; it cannot duplicate attribution.
    prepare.prepare_templates(prepare.TEMPLATE_DIR, authors)
    published, pushes = run_release(monkeypatch)
    assert len(published) == 1
    assert published[0]["tag"] == "v1.1.0"
    assert published[0]["assets"] == []
    assert len(pushes) == 2
    assert repo.tags["v1.1.0"].commit == repo.head.commit
    changelog = (repo.head.commit.tree / "CHANGELOG.md").data_stream.read().decode()
    assert changelog == Path("CHANGELOG.md").read_text()
    notes = published[0]["release_notes"]
    for text in map(normalize, [changelog, notes]):
        assert text.count("by [@alice](https://github.com/alice)") == 2
        assert text.count("by [@bob](https://github.com/bob)") == 1
        assert "Merger" not in text
        assert "### Bug Fixes" in text and "### Features" in text
        assert "### Documentation" in text
        assert "Restart once." in text
        assert "Improve guide & examples" in text
        for commit in commits:
            assert f"/commit/{commit.hexsha}" in text
        assert "/pull/12" in text
    assert old.split("<!-- version list -->")[1].strip() in changelog
    assert "**Detailed Changes**" in notes
    assert "v1.0.0...v1.1.0" in notes
    assert 'version = "1.1.0"' in Path("pyproject.toml").read_text()
    # Generated metadata and component templates are never staged as assets.
    assert ".github" not in repo.head.commit.tree
    # A repeated PSR run finds the tag and makes no duplicate commit/release.
    head = repo.head.commit.hexsha
    published_again, _ = run_release(monkeypatch)
    assert published_again == []
    assert repo.head.commit.hexsha == head


def test_empty_snapshot_matches_upstream_byte_for_byte(project, monkeypatch):
    """Verify empty snapshot matches upstream byte for byte."""
    from semantic_release.cli.changelog_writer import generate_release_notes

    repo, old, _ = project
    runtime, history = runtime_and_history(repo)
    version = runtime.version_translator.from_tag("v1.1.0")
    from datetime import datetime, timezone

    history = history.release(
        version,
        Actor("Test", "test@example.com"),
        Actor("Test", "test@example.com"),
        datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    release = history.released[version]

    # Build the attribution map from the parsed release elements (not raw git
    # commits) so keys match what the template looks up: hexsha ~ "#<number>".
    # The previous implementation keyed raw git commits (project[2]) which never
    # carry linked_merge_request, so attribution silently never ran and the
    # preservation assertions below passed vacuously.
    authors = {}
    for commits in release["elements"].values():
        for commit in commits:
            ref = getattr(commit, "linked_merge_request", "")
            if ref and re.fullmatch(r"#[1-9]\d*", ref):
                number = int(ref[1:])
                authors[f"{commit.hexsha}#{number}"] = (
                    " by [@alice](https://github.com/alice)"
                )
    # Guard against the map silently going empty (which would make the
    # preservation comparisons below pass without exercising attribution).
    assert authors, "expected at least one PR-linked commit to attribute"

    # Render the default (no-attribution) release notes using the upstream
    # template directory so we have a byte-for-byte baseline.
    default_notes = generate_release_notes(
        runtime.hvcs_client, release, Path("missing"), history, "conventional", True
    )

    # Render with empty authors — must match the default byte-for-byte.
    prepare.prepare_templates(prepare.TEMPLATE_DIR, {})
    empty_notes = generate_release_notes(
        runtime.hvcs_client,
        release,
        prepare.TEMPLATE_DIR,
        history,
        "conventional",
        True,
    )
    assert empty_notes == default_notes

    # Render with real authors — attribution must be present.
    prepare.prepare_templates(prepare.TEMPLATE_DIR, authors)
    enriched_notes = generate_release_notes(
        runtime.hvcs_client,
        release,
        prepare.TEMPLATE_DIR,
        history,
        "conventional",
        True,
    )
    # Attribution must actually be present before we strip it for comparison.
    assert " by [@alice](https://github.com/alice)" in enriched_notes
    assert normalize(
        re.sub(
            r" by \[@alice\]\(https://github.com/alice\)", "", normalize(enriched_notes)
        )
    ) == normalize(default_notes)


def test_same_sha_distinct_prs_render_through_templates(project, monkeypatch):
    """Two parsed PR records sharing one SHA must each credit their own author.

    This exercises the actual template rendering (not just the author map) for
    the squash-commit case from #3719: a single commit SHA parsed into two
    records with different linked PRs. Both the generated CHANGELOG and the
    published release notes must attribute each PR link to its respective
    author, and the existing changelog-preservation assertions must still hold.
    """
    from semantic_release.cli.changelog_writer import generate_release_notes

    repo, old, _ = project
    runtime, history = runtime_and_history(repo)
    version = runtime.version_translator.from_tag("v1.1.0")
    from datetime import datetime, timezone

    history = history.release(
        version,
        Actor("Test", "test@example.com"),
        Actor("Test", "test@example.com"),
        datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    release = history.released[version]

    # Find a SHA that was parsed into two records with distinct PR references.
    by_sha = {}
    for commits in release["elements"].values():
        for commit in commits:
            ref = getattr(commit, "linked_merge_request", "")
            if re.fullmatch(r"#[1-9]\d*", ref):
                by_sha.setdefault(commit.hexsha, []).append(int(ref[1:]))
    shared_sha, numbers = next(
        ((sha, refs) for sha, refs in by_sha.items() if len(set(refs)) >= 2),
        (None, None),
    )
    assert shared_sha is not None, "fixture must produce a shared-SHA, distinct-PR case"
    first, second = sorted(set(numbers))[:2]

    # Each PR link must resolve to a different author.
    authors = {
        f"{shared_sha}#{first}": " by [@alice](https://github.com/alice)",
        f"{shared_sha}#{second}": " by [@bob](https://github.com/bob)",
    }

    default_notes = generate_release_notes(
        runtime.hvcs_client, release, Path("missing"), history, "conventional", True
    )

    prepare.prepare_templates(prepare.TEMPLATE_DIR, authors)
    enriched_notes = generate_release_notes(
        runtime.hvcs_client, release, prepare.TEMPLATE_DIR, history, "conventional", True
    )

    # Both authors must appear in the rendered release notes.
    assert " by [@alice](https://github.com/alice)" in enriched_notes
    assert " by [@bob](https://github.com/bob)" in enriched_notes
    # Both PR links must be present and distinct.
    assert f"/pull/{first}" in enriched_notes
    assert f"/pull/{second}" in enriched_notes
    # Preservation: stripping attribution yields the default byte-for-byte.
    stripped = re.sub(
        r" by \[@(?:alice|bob)\]\(https://github\.com/(?:alice|bob)\)",
        "",
        normalize(enriched_notes),
    )
    assert normalize(stripped) == normalize(default_notes)


def test_main_prepares_snapshot_before_release(project, monkeypatch):
    """Verify main prepares snapshot before release."""
    session = requests.Session()
    mocked = client_for({10: user("alice"), 11: user("bob"), 12: None})
    monkeypatch.setattr(session, "get", mocked.get)
    monkeypatch.setattr(prepare.requests, "Session", lambda: session)
    monkeypatch.setenv("GH_TOKEN", "test-token")
    prepare.main()
    assert mocked.get.call_count == 3
    snapshot = (prepare.TEMPLATE_DIR / ".components/.authors.j2").read_text()
    assert "@alice" in snapshot and "@bob" in snapshot
    assert session.get_adapter("https://").max_retries.total == 3
    assert session.headers["Authorization"] == "Bearer test-token"


def test_breaking_change_and_bot_profile(project, monkeypatch):
    """Verify breaking change and bot profile."""
    repo, _, _ = project
    Path("example.txt").write_text("breaking")
    repo.index.add(["example.txt"])
    repo.index.commit(
        "feat!: migrate config (#13)\n\nBREAKING CHANGE: Replace the old setting."
    )
    _, history = runtime_and_history(repo)
    client = client_for(
        {
            10: None,
            11: None,
            12: None,
            13: {
                "login": "dependabot[bot]",
                "html_url": "https://github.com/apps/dependabot",
            },
        }
    )
    prepare.prepare_templates(
        prepare.TEMPLATE_DIR,
        prepare.collect_authors(history, client, "alandtse", "alexa_media_player"),
    )
    published, _ = run_release(monkeypatch)
    assert published[0]["tag"] == "v2.0.0"
    for text in [Path("CHANGELOG.md").read_text(), published[0]["release_notes"]]:
        assert "### Breaking Changes" in text
        assert "Replace the old setting." in text
        assert "[@dependabot\\[bot\\]](https://github.com/apps/dependabot)" in text


def test_preparation_failure_still_releases_without_authors(project, monkeypatch):
    """Complete both rendering paths with an empty map after a network failure."""
    session = requests.Session()
    monkeypatch.setattr(
        session, "get", Mock(side_effect=requests.ConnectionError("offline"))
    )
    monkeypatch.setattr(prepare.requests, "Session", lambda: session)
    monkeypatch.setenv("GH_TOKEN", "test-token")
    prepare.main()
    snapshot = (prepare.TEMPLATE_DIR / ".components/.authors.j2").read_text()
    assert snapshot == "{% set pr_authors = {} %}"
    published, _ = run_release(monkeypatch)
    assert published[0]["tag"] == "v1.1.0"
    for text in [Path("CHANGELOG.md").read_text(), published[0]["release_notes"]]:
        assert " by [@" not in text
        assert "/pull/10" in text


def test_version_pin_checked_before_template_generation(tmp_path, monkeypatch):
    """Verify version pin checked before template generation."""
    monkeypatch.setattr(prepare, "version", lambda _: "11.0.0")
    with pytest.raises(RuntimeError, match=re.escape("10.2.0")):
        prepare.prepare_templates(tmp_path / "templates", {})
    assert not (tmp_path / "templates").exists()


def test_excluded_commits_do_not_trigger_author_lookup(project):
    """Verify excluded commits do not trigger author lookup."""
    repo, _, _ = project
    config = Path("pyproject.toml")
    config.write_text(
        config.read_text().replace(
            "[tool.semantic_release.changelog]\n",
            '[tool.semantic_release.changelog]\nexclude_commit_patterns = ["^docs:"]\n',
        )
    )
    _, history = runtime_and_history(repo)
    client = client_for({10: user("alice"), 11: user("bob")})
    prepare.collect_authors(history, client, "alandtse", "alexa_media_player")
    assert client.get.call_count == 2


def test_first_release_stays_masked(project, monkeypatch):
    """Verify first release stays masked."""
    repo, _, _ = project
    repo.delete_tag("v1.0.0")
    Path("CHANGELOG.md").write_text("", newline="\n")
    _, history = runtime_and_history(repo)
    authors = prepare.collect_authors(
        history,
        client_for({10: user("alice"), 11: user("bob"), 12: None}),
        "alandtse",
        "alexa_media_player",
    )
    prepare.prepare_templates(prepare.TEMPLATE_DIR, authors)
    published, _ = run_release(monkeypatch)
    for text in [Path("CHANGELOG.md").read_text(), published[0]["release_notes"]]:
        assert "Initial Release" in text
        assert "@alice" not in text


def test_missing_template_directory_releases_with_defaults(project, monkeypatch):
    """Verify local releases work without the generated template directory."""
    assert not prepare.TEMPLATE_DIR.exists()
    published, _ = run_release(monkeypatch)
    assert published[0]["tag"] == "v1.1.0"
    for text in [Path("CHANGELOG.md").read_text(), published[0]["release_notes"]]:
        assert "Repair playback" in normalize(text)
        assert "/pull/10" in text
        assert " by [@" not in text
    assert not prepare.TEMPLATE_DIR.exists()


@pytest.mark.parametrize("prepared", [False, True])
def test_noop_release_has_no_side_effects(project, monkeypatch, prepared):
    """Exercise PSR no-op mode with both generated and absent templates."""
    repo, old, _ = project
    if prepared:
        _, history = runtime_and_history(repo)
        authors = prepare.collect_authors(
            history,
            client_for({10: user("alice"), 11: user("bob"), 12: None}),
            "alandtse",
            "alexa_media_player",
        )
        prepare.prepare_templates(prepare.TEMPLATE_DIR, authors)
    head = repo.head.commit.hexsha
    tags = [tag.name for tag in repo.tags]
    execute = Git.execute

    def reject_push(self, command, *args, **kwargs):
        """Allow PSR no-op reporting but reject an actual Git push."""
        assert "push" not in command
        return execute(self, command, *args, **kwargs)

    monkeypatch.setattr(Git, "execute", reject_push)
    monkeypatch.setattr(
        requests.Session, "send", Mock(side_effect=AssertionError("network request"))
    )
    result = CliRunner().invoke(semantic_release, ["--noop", "version", "--skip-build"])
    assert result.exit_code == 0, result.output + repr(result.exception)
    assert "1.1.0" in result.output
    assert repo.head.commit.hexsha == head
    assert [tag.name for tag in repo.tags] == tags
    assert Path("CHANGELOG.md").read_text() == old
    assert 'version = "1.0.0"' in Path("pyproject.toml").read_text()
