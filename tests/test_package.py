from __future__ import annotations

import pytest

pytestmark = pytest.mark.django_db


def test_lazy_package_exports() -> None:
    import django_openrouter as pkg

    assert pkg.__version__ == "0.1.1"
    assert callable(pkg.chat)
    assert pkg.OpenRouterClient is not None
    assert pkg.AsyncOpenRouterClient is not None
    assert pkg.ChatResult is not None
    assert callable(pkg.achat)
    assert callable(pkg.stream)
    assert callable(pkg.astream)
    assert pkg.ChatChunk is not None
    with pytest.raises(AttributeError, match="no attribute"):
        pkg.__getattr__("not_a_real_export")
