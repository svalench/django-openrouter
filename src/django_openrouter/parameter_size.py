"""Размер модели (миллионы / миллиарды параметров) из id/имени каталога.

OpenRouter не отдаёт отдельное поле; в slug обычно есть 70b / 8x7b / 340m.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_MILLION = 1_000_000
_BILLION = 1_000_000_000
_TRILLION = 1_000_000_000_000

# 8x7b / 8x7B — MoE (сначала, чтобы не схлопнуть в один 7B).
_MOE_RE = re.compile(
    r"(?i)(?<![a-z0-9.])(\d+(?:\.\d+)?)\s*[x\u00d7]\s*(\d+(?:\.\d+)?)\s*b\b",
)
_BILLION_RE = re.compile(r"(?i)(?<![a-z0-9.])(\d+(?:\.\d+)?)\s*b\b")
_MILLION_RE = re.compile(r"(?i)(?<![a-z0-9.])(\d+(?:\.\d+)?)\s*m\b")
_TRILLION_RE = re.compile(r"(?i)(?<![a-z0-9.])(\d+(?:\.\d+)?)\s*t\b")


@dataclass(frozen=True)
class ParameterSize:
    """count — для сортировки; label — «70B» / «340M» / «8x7B»."""

    count: int
    label: str


def _fmt_coeff(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def format_parameter_count(count: int) -> str:
    """Человекочитаемый размер: всегда суффикс M / B / T."""
    if count >= _TRILLION:
        return f"{_fmt_coeff(count / _TRILLION)}T"
    if count >= _BILLION:
        return f"{_fmt_coeff(count / _BILLION)}B"
    return f"{_fmt_coeff(count / _MILLION)}M"


def parse_parameter_size(*parts: object) -> ParameterSize | None:
    """Достаёт размер из строк каталога (id, name, description). Берёт наибольший."""
    blob = " ".join(str(part) for part in parts if part)
    if not blob:
        return None
    found: list[ParameterSize] = []
    for match in _MOE_RE.finditer(blob):
        experts = float(match.group(1))
        per_expert = float(match.group(2))
        count = int(experts * per_expert * _BILLION)
        found.append(
            ParameterSize(count=count, label=f"{_fmt_coeff(experts)}x{_fmt_coeff(per_expert)}B")
        )
    for match in _TRILLION_RE.finditer(blob):
        coeff = float(match.group(1))
        found.append(ParameterSize(count=int(coeff * _TRILLION), label=f"{_fmt_coeff(coeff)}T"))
    for match in _BILLION_RE.finditer(blob):
        coeff = float(match.group(1))
        found.append(ParameterSize(count=int(coeff * _BILLION), label=f"{_fmt_coeff(coeff)}B"))
    for match in _MILLION_RE.finditer(blob):
        coeff = float(match.group(1))
        found.append(ParameterSize(count=int(coeff * _MILLION), label=f"{_fmt_coeff(coeff)}M"))
    if not found:
        return None
    return max(found, key=lambda item: item.count)


def display_parameter_label(
    *,
    stored_label: str = "",
    model_id: str = "",
    name: str = "",
) -> str | None:
    """Готовая подпись для админки: сохранённая или разобранная на лету."""
    if stored_label:
        return stored_label
    parsed = parse_parameter_size(model_id, name)
    if parsed is None:
        return None
    return parsed.label
