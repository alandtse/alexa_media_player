"""Regression tests for issue #3551: deprecated `via_device` parameter.

Home Assistant >= 2026.9 deprecates the ``via_device`` key in device info
dicts/``DeviceInfo`` because ``device_registry.async_get_or_create`` will
remove that kwarg in HA 2027.8 in favour of ``via_device_id``. The
AlexaMediaSwitch device_info() property referenced an (ALEXA_DOMAIN,
client_unique_id) tuple, which is a self-reference (the same tuple also
populates the ``identifiers`` set) — i.e. the call was a runtime no-op
and only existed to emit a deprecation report. Removing it eliminates the
warning without changing behaviour.

The test strategy is deliberately light: rather than standing up a full
Home Assistant runtime fixture for a single-key fix, the regression check
parses the switch module with ``ast`` to assert the ``device_info``
property body no longer contains the ``"via_device"`` dict key. A full
HA-runtime test of the warning would belong in the upstream HA test
harness and is out of scope for this package's test suite.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SWITCH_PY = ROOT / "custom_components" / "alexa_media" / "switch.py"
INTEGRATION_DIR = ROOT / "custom_components" / "alexa_media"


def _load_device_info_property() -> ast.FunctionDef:
    """Return the AST node for ``AlexaMediaSwitch.device_info``.

    The device_info is declared as a regular @property-style method; we
    locate it by class + name so the test does not break if other
    properties are added or reordered.
    """
    tree = ast.parse(SWITCH_PY.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "AlexaMediaSwitch":
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.FunctionDef) and stmt.name == "device_info":
                return stmt
    raise AssertionError("AlexaMediaSwitch.device_info not found in switch.py")


def _collect_dict_literal_source(func: ast.FunctionDef) -> str:
    """Return the source text of the dict literal returned by ``func``.

    The device_info body is ``return {"identifiers": ..., ("via_device": ...)}``
    so we grab the source segment of the first Dict literal found in the
    function body. Using ``ast.get_source_segment`` keeps the test resilient
    to whitespace/line-end changes.
    """
    source = SWITCH_PY.read_text(encoding="utf-8")
    for sub in ast.walk(func):
        if isinstance(sub, ast.Dict):
            segment = ast.get_source_segment(source, sub)
            if segment is not None:
                return segment
    raise AssertionError("No dict literal found in AlexaMediaSwitch.device_info")


def test_device_info_does_not_contain_deprecated_via_device_key():
    """``via_device`` is deprecated; device_info must not set it.

    Asserted by checking the dict literal returned by
    ``AlexaMediaSwitch.device_info`` has no ``"via_device"`` key. Any
    string occurrence of ``"via_device"`` in the literal counts as a
    violation — keys, values, or comments inside the dict would all be
    regressions.
    """
    func = _load_device_info_property()
    dict_source = _collect_dict_literal_source(func)
    assert '"via_device"' not in dict_source, (
        "device_info still references deprecated 'via_device' key; "
        "Home Assistant 2026.9+ reports a deprecation and 2027.8 will "
        "remove it (see issue #3551)."
    )


def test_device_info_still_exposes_identifiers_key():
    """Sanity guard: removing ``via_device`` must not delete ``identifiers``.

    ``identifiers`` carries the (DOMAIN, unique_id) tuple that ties the
    switch entity to its parent device in the registry; the deprecation
    fix must keep that.
    """
    func = _load_device_info_property()
    dict_source = _collect_dict_literal_source(func)
    assert '"identifiers"' in dict_source, (
        "device_info no longer declares 'identifiers'; the deprecation "
        "fix should only drop 'via_device', not the rest of the dict."
    )


@pytest.mark.parametrize("path", [INTEGRATION_DIR])
def test_via_device_key_removed_everywhere_in_integration(path: Path):
    """No stale ``"via_device"`` references should remain in the integration.

    ``diagnostics.py`` reads ``DeviceEntry.via_device_id`` (the new field)
    and passes this check because the quoted-literal pattern cannot match
    ``via_device_id``; no file in ``custom_components/alexa_media/`` may
    keep a literal ``"via_device"`` reference.
    """
    offenders: list[tuple[str, int, str]] = []
    for py_file in sorted(path.rglob("*.py")):
        for lineno, line in enumerate(
            py_file.read_text(encoding="utf-8").splitlines(), 1
        ):
            if '"via_device"' in line:
                offenders.append(
                    (str(py_file.relative_to(path.parent)), lineno, line.strip())
                )
    assert not offenders, (
        "Found lingering '\"via_device\"' literal references; the deprecated key should be fully removed:\n"
        + "\n".join(f"  {f}:{lno}: {snippet}" for f, lno, snippet in offenders)
    )
