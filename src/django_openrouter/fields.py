"""Кастомные поля моделей."""

from __future__ import annotations

from django.core import signing
from django.db import models

_PREFIX = "or1:"
_SALT = "django_openrouter.api_key"


class EncryptedTextField(models.TextField):
    """Хранит значение в БД через django.core.signing (ключ — SECRET_KEY)."""

    def from_db_value(
        self,
        value: str | None,
        expression: object,
        connection: object,
    ) -> str:
        return self._decrypt(value)

    def to_python(self, value: object) -> str:
        if value is None:
            return ""
        return self._decrypt(str(value))

    def get_prep_value(self, value: object) -> str:
        prepared = super().get_prep_value(value)
        if prepared is None:
            return ""
        return self._encrypt(str(prepared))

    def _encrypt(self, value: str) -> str:
        if not value or value.startswith(_PREFIX):
            return value
        return _PREFIX + signing.dumps(value, salt=_SALT)

    def _decrypt(self, value: str | None) -> str:
        if not value:
            return ""
        if not value.startswith(_PREFIX):
            return value
        try:
            loaded = signing.loads(value[len(_PREFIX) :], salt=_SALT)
        except signing.BadSignature:
            # SECRET_KEY сменился или данные повреждены — считаем ключ пустым.
            return ""
        return str(loaded)
