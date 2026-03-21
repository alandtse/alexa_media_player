# Alexa Media Player Custom Component

Alexa Media Player is a Python-based Home Assistant custom component that enables control of Amazon Alexa devices through the unofficial Alexa API. It provides media player functionality, notifications, and device control integration within Home Assistant.

**Project Scale**: ~8,500 lines of Python code across 15 component files, with translations in 19+ languages.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Initial Setup

- Install Python 3.13 (REQUIRED): `sudo apt install -y software-properties-common && sudo add-apt-repository -y ppa:deadsnakes/ppa && sudo apt update && sudo apt install -y python3.13 python3.13-venv python3.13-dev`
  - **FALLBACK for Python 3.12**: If Python 3.13 unavailable, temporarily modify `pyproject.toml` to change `python = ">=3.13,<4.0"` to `python = ">=3.12,<4.0"`, but REVERT this before committing
- Install Poetry: `pip3 install poetry`
- Add Poetry to PATH: `export PATH="$HOME/.local/bin:$PATH"`

### Dependencies and Build

- **PREFERRED**: Use Poetry for full dependency management:
  - `poetry install` -- takes 2-3 minutes on first run. NEVER CANCEL. Set timeout to 10+ minutes.
  - If Poetry fails due to version conflicts: `poetry lock --no-update` first, then `poetry install`
- **FALLBACK**: Install core dependencies manually if Poetry fails:
  - `pip3 install alexapy==1.29.19 packaging wrapt async_timeout aiohttp`
  - This allows basic functionality but may miss dev dependencies

### Linting and Code Quality (ALWAYS run before committing)

- **CRITICAL**: Run ALL linting tools before any commit - CI will fail otherwise
- Black formatting: `black --check .` (takes ~1 second) or `black .` to fix
- Import sorting: `isort --check .` (takes ~0.2 seconds) or `isort .` to fix
- YAML linting: `yamllint .` (takes ~0.1 seconds)
- Spell checking: `codespell` (takes ~0.2 seconds) - will find real spelling errors in CHANGELOG.md
- Pre-commit hooks: `pre-commit run --all-files` (takes 30-60 seconds) - comprehensive check
- **NEVER CANCEL**: Pre-commit may take 60+ seconds on first run, up to 10 minutes with network issues. Set timeout to 15+ minutes.
- **NETWORK DEPENDENCY**: Pre-commit downloads and installs tools from internet - may fail in restricted environments

### Testing

- Run test setup: `bash tests/setup.sh` (creates symlinks)
- **LIMITATION**: Full test suite requires Home Assistant installation which is complex
- Test collection only: `python3 -m pytest tests/ --collect-only`
- **CI Testing**: Tests in GitHub Actions use `pytest --timeout=9 --durations=10 -n auto --cov`
- **NEVER CANCEL**: Test runs can take 5-10 minutes in CI. Local testing may be limited due to HA dependency.

### Development Workflow

- Always work in the Poetry virtual environment: `poetry shell` or prefix commands with `poetry run`
- **CRITICAL**: The component integrates with Home Assistant - changes must be compatible with HA 2025.2.0+
- Component code is in `custom_components/alexa_media/`
- Test any changes with a real Home Assistant instance if possible
- Validate with HACS: Component must pass HACS validation for integration repository

## Validation Steps

### Before Every Commit

1. `black --check . && isort --check .` (formatting)
2. `yamllint .` (YAML validation)
3. `codespell` (spell check - expect some false positives in CHANGELOG.md)
4. `poetry run pytest --collect-only` (test structure validation)
5. Ensure no temporary changes to pyproject.toml for Python version
6. **PREFERRED**: `pre-commit run --all-files` (comprehensive check)
7. **FALLBACK if pre-commit fails**: Run individual tools above manually

### CI/CD Validation

- GitHub Actions runs: validate.yaml (HACS + hassfest), test.yml (pytest), pre-commit.yml
- **NEVER CANCEL**: CI builds can take 10-15 minutes total across all workflows
- hassfest validates Home Assistant integration requirements
- HACS validation ensures component meets HACS repository standards

## Common Tasks and Timing

### Repository Exploration

```bash
# View repository root (key files)
ls -la
# Shows: .github/, custom_components/, tests/, pyproject.toml, README.md, hacs.json

# Key component files
ls -la custom_components/alexa_media/
# Shows: __init__.py, manifest.json, const.py, media_player.py, config_flow.py, etc.

# Configuration files
cat pyproject.toml        # Poetry configuration and dependencies
cat hacs.json            # HACS integration settings
cat custom_components/alexa_media/manifest.json  # HA integration manifest
```

### Version Management

- Version is managed in multiple places via semantic-release:
  - `pyproject.toml:tool.poetry.version`
  - `custom_components/alexa_media/const.py:VERSION`
  - `custom_components/alexa_media/manifest.json:version`
- **NEVER** manually update versions - let semantic-release handle this

### Common File Locations

- **Integration code**: `custom_components/alexa_media/`
- **Media player**: `custom_components/alexa_media/media_player.py`
- **Configuration**: `custom_components/alexa_media/config_flow.py`
- **Constants**: `custom_components/alexa_media/const.py`
- **Services**: `custom_components/alexa_media/services.py`
- **Tests**: `tests/test_helpers.py` (limited test coverage)
- **Translations**: `custom_components/alexa_media/translations/`

### Dependency Management

- **Core dependencies**: alexapy==1.29.19, aiohttp>=3.8.1, packaging>=20.3, wrapt>=1.12.1
- **Dev dependencies**: homeassistant>=2025.2.0, pytest-homeassistant-custom-component>=0.13.107
- Add new dependencies to `pyproject.toml` then run `poetry lock`
- **NEVER CANCEL**: `poetry lock` can take 60+ seconds. Set timeout to 10+ minutes.

### Home Assistant Integration

- This is a **custom component** - not part of core Home Assistant
- Installed via HACS (Home Assistant Community Store) or manual installation
- Configuration through Home Assistant UI (config_flow.py)
- Creates media_player entities, notification services, and sensor entities
- **TESTING LIMITATION**: Full integration testing requires a Home Assistant instance

### Network and API Dependencies

- **WARNING**: Component relies on unofficial Amazon Alexa API
- **authcaptureproxy** handles authentication challenges
- Component may break if Amazon changes their API
- Rate limiting and authentication errors are common issues

## Troubleshooting Common Issues

### Python Version Conflicts

- **Root cause**: Project requires Python 3.13, many environments have 3.12
- **Solution**: Install Python 3.13 OR temporarily modify pyproject.toml for development (but revert before commit)

### Poetry Installation Failures

- **Fallback**: Use pip to install core dependencies individually
- **Network issues**: Poetry may timeout on slow connections - increase timeout values
- **Pre-commit network dependency**: Pre-commit hooks require internet access to download tools - may fail in restricted environments

### Test Failures

- Many tests require Home Assistant installation
- **Limitation**: Full test validation may not be possible in all environments
- Focus on linting validation which catches most issues

### CI/CD Failures

- **Most common**: Linting failures (black, isort, yamllint, codespell)
- **Solution**: Always run all linting tools before committing
- Pre-commit hooks prevent most issues if configured properly

**CRITICAL REMINDERS**:

- **NEVER CANCEL** long-running commands (poetry lock, poetry install, CI builds)
- **ALWAYS** run complete linting suite before committing
- **REVERT** any temporary Python version changes before committing
- Set timeouts of 10+ minutes for Poetry operations, 5+ minutes for pre-commit
