"""Prepare PSR 10.2.0 templates with a shared snapshot of GitHub PR authors."""

from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import shutil

from git import Repo
import requests
from requests.adapters import HTTPAdapter
from semantic_release.changelog.release_history import ReleaseHistory
from semantic_release.cli.changelog_writer import get_default_tpl_dir
from semantic_release.cli.config import (
    GlobalCommandLineOptions,
    RawConfig,
    RuntimeContext,
)
from semantic_release.cli.util import load_raw_config_file
from urllib3.util.retry import Retry

TEMPLATE_DIR = Path(".github/.release-templates")
PR_LINK = """                commit.linked_merge_request
              )"""


def author_link(user):
    """Validate API metadata before inserting a linked username into Markdown."""
    if not isinstance(user, dict):
        return ""
    login = user.get("login", "")
    url = user.get("html_url", "")
    if not isinstance(login, str) or not isinstance(url, str):
        return ""
    if not re.fullmatch(r"[a-z\d-]+(?:\[bot\])?", login, re.I):
        return ""
    # Bots have /apps/name profiles; normal accounts must link to their login.
    profile = f"apps/{login[:-5]}" if login.endswith("[bot]") else login
    if url.lower() != f"https://github.com/{profile}".lower():
        return ""
    label = login.replace("[", r"\[").replace("]", r"\]")
    return f" by [@{label}]({url})"


def collect_authors(history, client, owner, repo):
    """Fetch each unreleased PR once, crediting pull.user rather than commit author."""
    authors = {}
    cache = {}
    for commits in history.unreleased.values():
        for commit in commits:
            reference = getattr(commit, "linked_merge_request", "")
            if not re.fullmatch(r"#[1-9]\d*", reference):
                continue
            number = int(reference[1:])
            if number not in cache:
                response = client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}",
                    timeout=30,
                )
                # A deleted/inaccessible PR has no available attribution. Other
                # failures abort before PSR can commit or publish inconsistent notes.
                if response.status_code == 404:
                    print(
                        f"::warning::PR #{number} is unavailable; leaving it uncredited"
                    )
                    cache[number] = ""
                else:
                    response.raise_for_status()
                    cache[number] = author_link(response.json().get("user"))
            if cache[number]:
                authors[commit.hexsha] = cache[number]
    return authors


def prepare_templates(destination, authors):
    """Copy the pinned upstream templates and change only PR-link formatting."""
    if version("python-semantic-release") != "10.2.0":
        raise RuntimeError(
            "Attribution templates require python-semantic-release==10.2.0"
        )
    shutil.copytree(
        get_default_tpl_dir("conventional", "md"), destination, dirs_exist_ok=True
    )
    macro_file = destination / ".components/macros.md.j2"
    macro = macro_file.read_text(encoding="utf-8")
    if macro.count(PR_LINK) != 1:
        raise RuntimeError(
            "PSR PR-link template has changed; review attribution integration"
        )
    macro = '{% from ".authors.j2" import pr_authors %}' + macro.replace(
        PR_LINK, PR_LINK + ' ~ pr_authors.get(commit.hexsha, "")'
    )
    macro_file.write_text(macro, encoding="utf-8")
    # JSON string escaping also prevents author metadata from becoming Jinja code.
    (destination / ".components/.authors.j2").write_text(
        "{% set pr_authors = " + json.dumps(authors, sort_keys=True) + " %}",
        encoding="utf-8",
    )


def main():
    """Use the same parser, tags and exclusions as the following PSR action."""
    raw = RawConfig.model_validate(load_raw_config_file(Path("pyproject.toml")))
    runtime = RuntimeContext.from_raw_config(raw, GlobalCommandLineOptions())
    with Repo(runtime.repo_dir) as repo:
        history = ReleaseHistory.from_git_history(
            repo=repo,
            translator=runtime.version_translator,
            commit_parser=runtime.commit_parser,
            exclude_commit_patterns=runtime.changelog_excluded_commit_patterns,
        )
    with requests.Session() as client:
        client.headers.update(
            {
                "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        client.mount(
            "https://",
            HTTPAdapter(
                max_retries=Retry(
                    total=3,
                    backoff_factor=1,
                    status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["GET"],
                    respect_retry_after_header=False,
                )
            ),
        )
        authors = collect_authors(
            history, client, runtime.hvcs_client.owner, runtime.hvcs_client.repo_name
        )
    prepare_templates(TEMPLATE_DIR, authors)


if __name__ == "__main__":
    main()
