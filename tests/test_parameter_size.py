from __future__ import annotations

from django_openrouter.parameter_size import (
    format_parameter_count,
    parse_parameter_size,
)


def test_parse_billions_from_slug() -> None:
    size = parse_parameter_size("meta-llama/llama-3.1-70b-instruct", "Llama 3.1 70B")
    assert size is not None
    assert size.label == "70B"
    assert size.count == 70_000_000_000


def test_parse_fractional_billions() -> None:
    size = parse_parameter_size("microsoft/phi-3-mini-3.8b")
    assert size is not None
    assert size.label == "3.8B"


def test_parse_millions() -> None:
    size = parse_parameter_size("vendor/tiny-340m-chat")
    assert size is not None
    assert size.label == "340M"
    assert size.count == 340_000_000


def test_parse_moe() -> None:
    size = parse_parameter_size("mistralai/mixtral-8x7b-instruct")
    assert size is not None
    assert size.label == "8x7B"
    assert size.count == 56_000_000_000


def test_parse_picks_largest() -> None:
    size = parse_parameter_size("something-8b-also-70b")
    assert size is not None
    assert size.label == "70B"


def test_parse_ignores_version_without_unit() -> None:
    assert parse_parameter_size("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet") is None


def test_parse_empty() -> None:
    assert parse_parameter_size("", None) is None


def test_format_parameter_count_units() -> None:
    assert format_parameter_count(70_000_000_000) == "70B"
    assert format_parameter_count(340_000_000) == "340M"
    assert format_parameter_count(1_800_000_000) == "1.8B"
