# Release note contributor acknowledgments

The release workflow uses Python Semantic Release (PSR) v10.2.0. Its default
release notes do not credit authors. The custom `.release_notes.md.j2` keeps
that version's default Markdown output and appends a Contributors section.
It uses Git author names and `Co-authored-by` trailers, deduplicated without
case sensitivity. It does not publish email addresses or infer GitHub handles.
Names come from the commits PSR includes in the release history, including
unclassified commits; excluded commits are outside this scope. Names are
deduplicated by display name, so distinct people with the same name appear once.

The upstream templates and macros are inlined so this remains the only `.j2`
file in the template directory. In PSR v10.2.0, additional template files would
disable the built-in changelog fallback. Keep documentation and tests outside
that directory. The upstream MIT license is retained in the template comment.

When updating PSR, compare its default templates and run the regression check:

```sh
python -m pip install python-semantic-release==10.2.0
python .github/tests/test_release_notes.py
```

The check renders notes through PSR itself, verifies that the original release
notes are preserved, and checks contributor deduplication, coauthors, escaping,
unclassified commits, initial and empty releases, and default changelog dispatch.
It uses a temporary Git repository and makes no network or publishing calls.

Release branching, version selection, release assets, and publishing remain in
the existing workflow. The credits apply to future releases after this change
reaches `master`; existing GitHub release bodies are not edited.
