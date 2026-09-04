"""Кастомные поля моделей."""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings as django_settings
from django.core import signing
from django.db import models

_PREFIX_V1 = "or1:"
_PREFIX_V2 = "or2:"
_SALT = "django_openrouter.api_key"


@lru_cache(maxsize=4)
def _fernet_for(secret: str) -> Fernet:
    """Fernet-ключ из SHA-256(SECRET_KEY) — 32 байта в urlsafe-base64."""
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _fernet() -> Fernet:
    return _fernet_for(str(django_settings.SECRET_KEY))


class EncryptedTextField(models.TextField):
    """
    Хранит значение в БД зашифрованным (Fernet / AES).

    В ORM после чтения — plaintext (нужен клиенту). В колонке БД — or2:<token>.
    Старые значения or1: (django.core.signing) читаются и при следующем save
    перешифровываются в or2:.
    """

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
        # Не вызываем super()/to_python: иначе or2:-токен расшифруется
        # и Fernet выдаст новый ciphertext при каждом save.
        if value is None:
            return ""
        return self._encrypt(str(value))

    def value_to_string(self, obj: models.Model) -> str:
        # dumpdata должен писать ciphertext, а не ключ в открытом виде.
        raw = self.value_from_object(obj)
        return self.get_prep_value(raw) or ""

    def _encrypt(self, value: str) -> str:
        if not value:
            return ""
        if value.startswith(_PREFIX_V2):
            return value
        if value.startswith(_PREFIX_V1):
            value = self._decrypt(value)
            if not value:
                return ""
        token = _fernet().encrypt(value.encode("utf-8")).decode("ascii")
        return _PREFIX_V2 + token

    def _decrypt(self, value: str | None) -> str:
        if not value:
            return ""
        if value.startswith(_PREFIX_V2):
            try:
                payload = value[len(_PREFIX_V2) :].encode("ascii")
                return _fernet().decrypt(payload).decode("utf-8")
            except (InvalidToken, ValueError, TypeError):
                # SECRET_KEY сменился или данные повреждены — считаем ключ пустым.
                return ""
        if value.startswith(_PREFIX_V1):
            try:
                loaded = signing.loads(value[len(_PREFIX_V1) :], salt=_SALT)
            except signing.BadSignature:
                return ""
            return str(loaded)
        return value
