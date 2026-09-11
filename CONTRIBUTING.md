# Contributing to django-openrouter

## Local setup

Use Python 3.11 or newer. The following setup uses Django 5.2; the supported
Python/Django combinations are listed in `tox.ini` and `.github/workflows/ci.yml`.

```bash
git clone https://github.com/svalench/django-openrouter.git
cd django-openrouter
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]" "Django==5.2.*"
```

On Windows, activate with `.venv\Scripts\activate` instead.

## Test without an OpenRouter account

The suite uses a local SQLite test database and mocked HTTP responses.
Do not supply a real API key or run model catalog synchronization to test.
Dependency installation requires internet access; these tests do not need a
live provider.

```bash
# Focused walkthrough: chat, fallback, and a budget rejection before HTTP.
pytest tests/test_client.py -k "chat_success_logs_and_cost or fallback_on_429 or budget_exceeded_stops_before_http"

# Same coverage gate as CI.
pytest --cov=django_openrouter --cov-report=term-missing --cov-fail-under=85
ruff check src tests
mypy src/django_openrouter
```

Add a regression test for behavior changes. Keep provider responses mocked with
`respx`, including failure and streaming cases.

## Check distributions before release

```bash
python -m pip install build twine
python -m build
python -m twine check --strict dist/*
```

`python -m build` creates the sdist first, then builds the wheel from that sdist.
The CI build job also installs the wheel in a clean environment and checks its
type marker, migrations, templates, static files, and compiled translations.
Building or checking locally does not publish anything to PyPI.

## Documentation and pull requests

- Keep the README quickstart aligned with the public API and its tests.
- `docs/` contains screenshots and supporting documentation; `site/` is the
  authored React/TypeScript documentation application, not vendored Python code.
- Include the problem, scope, and exact checks performed in the PR description.
- Use synthetic data in issues and tests. Do not include API keys, private chat
  content, customer data, or production database exports.
