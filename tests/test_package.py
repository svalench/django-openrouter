from __future__ import annotations

import pytest

pytestmark = pytest.mark.django_db


def test_lazy_package_exports() -> None:
    import django_openrouter as pkg

    assert pkg.__version__ == "0.7.1"
    assert callable(pkg.chat)
    assert callable(pkg.generate_image)
    assert callable(pkg.agenerate_image)
    assert pkg.GeneratedImage is not None
    assert pkg.OpenRouterTimeout is not None
    assert callable(pkg.transcribe)
    assert callable(pkg.atranscribe)
    assert pkg.TranscriptionResult is not None
    assert pkg.OpenRouterClient is not None
    assert pkg.AsyncOpenRouterClient is not None
    assert pkg.ChatResult is not None
    assert callable(pkg.achat)
    assert callable(pkg.stream)
    assert callable(pkg.astream)
    assert pkg.ChatChunk is not None
    with pytest.raises(AttributeError, match="no attribute"):
        pkg.__getattr__("not_a_real_export")


def test_pydantic_ai_extra_is_slim_without_openai() -> None:
    from importlib.metadata import requires

    extra = [
        req
        for req in requires("django-openrouter") or []
        if 'extra == "pydantic-ai"' in req or "extra == 'pydantic-ai'" in req
    ]
    names = [req.split(";", 1)[0].strip() for req in extra]
    assert names == ["pydantic-ai-slim>=2.64"]
    assert all(not name.startswith("openai") for name in names)
