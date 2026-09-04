from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


def test_makemigrations_check_clean() -> None:
    out = StringIO()
    try:
        call_command(
            "makemigrations",
            "django_openrouter",
            check=True,
            dry_run=True,
            stdout=out,
            stderr=StringIO(),
        )
    except SystemExit as exc:  # Django exits 1 when unmigrated changes exist
        pytest.fail(f"Pending migrations: {out.getvalue()} ({exc})")
