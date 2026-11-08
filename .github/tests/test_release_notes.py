from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import tomllib
from types import SimpleNamespace
from unittest.mock import patch

from git import Actor, Repo
from semantic_release.changelog.release_history import ReleaseHistory
from semantic_release.cli.changelog_writer import (
    generate_release_notes,
    write_changelog_files,
)
from semantic_release.cli.config import ChangelogMode
from semantic_release.commit_parser.conventional import ConventionalCommitParser
from semantic_release.hvcs.github import Github
from semantic_release.version.version import Version

repo_path = Path(__file__).resolve().parents[2]
template_dir = repo_path / ".github/release-templates"
client = Github("https://github.com/alandtse/alexa_media_player.git")
parser = ConventionalCommitParser()
with TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    repo = Repo.init(tmp)

    def commit(message, name):
        return repo.index.commit(message, author=Actor(name, "test@example.invalid"))

    old = Version.parse("1.0.0")
    new = Version.parse("1.1.0")
    elements = defaultdict(list)
    for msg, author in [
        (
            "fix: correct a bug (#123)\n\nCo-authored-by: Carol <carol@example.invalid>",
            "Alice",
        ),
        (
            "feat(player)!: add a feature (#124)\n\nBREAKING CHANGE: remove old setting\n\nNOTICE: migrate settings",
            "Bob",
        ),
        ("fix: another bug", "Alice"),
        ("unclassified contribution", "Dave"),
        (
            "docs: escape author\n\nCo-authored-by: &danger; <test@example.invalid>",
            "Eve",
        ),
    ]:
        parsed = parser.parse(commit(msg, author))
        for item in parsed if isinstance(parsed, list) else [parsed]:
            elements[getattr(item, "type", "unknown")].append(item)
    actor = Actor("Release Bot", "bot@example.invalid")
    history = ReleaseHistory(unreleased=elements, released={}).release(
        old, actor, actor, datetime.now(timezone.utc)
    )
    history = ReleaseHistory(unreleased=elements, released=history.released).release(
        new, actor, actor, datetime.now(timezone.utc)
    )
    release = history.released[new]

    def render(template_dir, release=release, history=history, mask=True):
        return generate_release_notes(
            client, release, template_dir, history, "conventional", mask, "Apache-2.0"
        ).replace("\r\n", "\n")

    baseline = render(Path(tmp) / "absent")
    actual = render(template_dir)
    prefix, credits = actual.split("### Contributors", 1)
    assert prefix.rstrip() == baseline.rstrip()
    for name in ["Alice", "Bob", "Carol", "Dave"]:
        assert credits.count("- " + name) == 1, credits
    assert "<script>" not in credits
    assert "&amp;danger;" in credits
    assert "@example.invalid" not in credits
    assert "Release Bot" not in credits
    assert "Breaking Changes" in prefix and "Additional Release Information" in prefix
    assert "/pull/123" in prefix and "**Detailed Changes**" in prefix
    first = render(template_dir, history.released[old])
    assert "- Initial Release" in first and "### Contributors" in first
    empty = ReleaseHistory(unreleased={}, released={}).release(
        old, actor, actor, datetime.now(timezone.utc)
    )
    assert "### Contributors" not in render(template_dir, empty.released[old], empty)
    with (repo_path / "pyproject.toml").open("rb") as f:
        config = tomllib.load(f)
    assert (
        config["tool"]["semantic_release"]["changelog"]["template_dir"]
        == ".github/release-templates"
    )
    runtime = SimpleNamespace(
        repo_dir=tmp,
        template_dir=template_dir,
        changelog_mode=ChangelogMode.UPDATE,
        changelog_insertion_flag="<!-- version list -->",
        changelog_file=Path(tmp) / "CHANGELOG.md",
        changelog_mask_initial_release=True,
        changelog_output_format="md",
        changelog_style="conventional",
    )
    with patch(
        "semantic_release.cli.changelog_writer.write_default_changelog",
        return_value="CHANGELOG.md",
    ) as default_writer:
        assert write_changelog_files(runtime, history, client) == ["CHANGELOG.md"]
        default_writer.assert_called_once()
    repo.close()
    print(
        "PASS: default notes preserved; unique authors/coauthors; unknown commits; escaping; no emails; initial/empty release; default changelog dispatch; configured template path"
    )
