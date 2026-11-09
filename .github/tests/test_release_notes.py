"""Exercise attribution with the actual pinned PSR renderer and release command."""

import importlib.util
from pathlib import Path
import re
from types import SimpleNamespace
from unittest.mock import Mock

from click.testing import CliRunner
from git import Actor, Repo
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
        "0": " by [@alice](https://github.com/alice)",
        "1": " by [@alice](https://github.com/alice)",
    }
    assert client.get.call_count == 3
    assert all(
        "/repos/owner/repo/pulls/" in c.args[0] for c in client.get.call_args_list
    )


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


def test_api_failure_aborts_preparation():
    """Verify api failure aborts preparation."""
    client = client_for({10: requests.HTTPError("unavailable")})
    with pytest.raises(requests.HTTPError):
        prepare.collect_authors(history_for("#10"), client, "owner", "repo")


@pytest.mark.parametrize("payload", [None, [], "unexpected", 123])
def test_non_object_response_identifies_pr(payload):
    """Reject non-object API responses with the affected PR number."""
    client = client_for({10: None})
    response = Mock(status_code=200)
    response.json.return_value = payload
    client.get.side_effect = None
    client.get.return_value = response
    with pytest.raises(ValueError, match=r"PR #10: expected a JSON object"):
        prepare.collect_authors(history_for("#10"), client, "owner", "repo")


def test_invalid_json_identifies_pr_and_preserves_cause():
    """Contextualize decoding failures without swallowing unrelated errors."""
    client = client_for({10: None})
    response = Mock(status_code=200)
    error = requests.exceptions.JSONDecodeError("Invalid JSON", "bad", 0)
    response.json.side_effect = error
    client.get.side_effect = None
    client.get.return_value = response
    with pytest.raises(
        ValueError, match=r"PR #10: response is not valid JSON"
    ) as caught:
        prepare.collect_authors(history_for("#10"), client, "owner", "repo")
    assert caught.value.__cause__ is error


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
    from semantic_release.cli.changelog_writer import (
        generate_release_notes,
        write_changelog_files,
    )

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
    default_notes = generate_release_notes(
        runtime.hvcs_client, release, Path("missing"), history, "conventional", True
    )
    write_changelog_files(runtime, history, runtime.hvcs_client)
    default_changelog = Path("CHANGELOG.md").read_text()
    Path("CHANGELOG.md").write_text(old, newline="\n")
    prepare.prepare_templates(prepare.TEMPLATE_DIR, {})
    write_changelog_files(runtime, history, runtime.hvcs_client)
    assert Path("CHANGELOG.md").read_text() == default_changelog
    assert (
        generate_release_notes(
            runtime.hvcs_client,
            release,
            prepare.TEMPLATE_DIR,
            history,
            "conventional",
            True,
        )
        == default_notes
    )
    authors = {c.hexsha: " by [@alice](https://github.com/alice)" for c in project[2]}
    Path("CHANGELOG.md").write_text(old, newline="\n")
    prepare.prepare_templates(prepare.TEMPLATE_DIR, authors)
    write_changelog_files(runtime, history, runtime.hvcs_client)
    enriched = Path("CHANGELOG.md").read_text()
    assert normalize(
        re.sub(r" by \[@alice\]\(https://github.com/alice\)", "", normalize(enriched))
    ) == normalize(default_changelog)
    enriched_notes = generate_release_notes(
        runtime.hvcs_client,
        release,
        prepare.TEMPLATE_DIR,
        history,
        "conventional",
        True,
    )
    assert normalize(
        re.sub(
            r" by \[@alice\]\(https://github.com/alice\)", "", normalize(enriched_notes)
        )
    ) == normalize(default_notes)


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


def test_preparation_failure_writes_no_templates(project, monkeypatch):
    """Verify preparation failure writes no templates."""
    session = requests.Session()
    monkeypatch.setattr(
        session, "get", Mock(side_effect=requests.ConnectionError("offline"))
    )
    monkeypatch.setattr(prepare.requests, "Session", lambda: session)
    monkeypatch.setenv("GH_TOKEN", "test-token")
    with pytest.raises(requests.ConnectionError):
        prepare.main()
    assert not prepare.TEMPLATE_DIR.exists()
    assert "v1.1.0" not in project[0].tags


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
