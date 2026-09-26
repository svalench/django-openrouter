"""Кастомные поля моделей."""

from __future__ import annotations

import base64
import hashlib
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings as django_settings
from django.core import signing
from django.db import models

logger = logging.getLogger("django_openrouter")

_PREFIX_V1 = "or1:"
_PREFIX_V2 = "or2:"
_SALT = "django_openrouter.api_key"


def _key_for(secret: str) -> Fernet:
    """Fernet-ключ из SHA-256(secret) — 32 байта в urlsafe-base64."""
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


@lru_cache(maxsize=4)
def _fernet_for(secrets: tuple[str, ...]) -> MultiFernet:
    """Шифрует первым ключом, расшифровывает любым (SECRET_KEY + SECRET_KEY_FALLBACKS)."""
    return MultiFernet([_key_for(secret) for secret in secrets])


def _secrets() -> tuple[str, ...]:
    fallbacks = django_settings.SECRET_KEY_FALLBACKS or []
    return (str(django_settings.SECRET_KEY), *(str(item) for item in fallbacks))


def _fernet() -> MultiFernet:
    return _fernet_for(_secrets())


def _primary_fernet() -> MultiFernet:
    return _fernet_for(_secrets()[:1])


class EncryptedTextField(models.TextField):
    """
    Хранит значение в БД зашифрованным (Fernet / AES).

    В ORM после чтения — plaintext (нужен клиенту). В колонке БД — or2:<token>.
    Старые значения or1: (django.core.signing) читаются и при следующем save
    перешифровываются в or2:. Токены, зашифрованные ключом из
    SECRET_KEY_FALLBACKS, при save перешифровываются текущим SECRET_KEY.
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
            return self._rotate(value)
        if value.startswith(_PREFIX_V1):
            value = self._decrypt(value)
            if not value:
                return ""
        token = _fernet().encrypt(value.encode("utf-8")).decode("ascii")
        return _PREFIX_V2 + token

    def _rotate(self, value: str) -> str:
        payload = value[len(_PREFIX_V2) :].encode("ascii")
        try:
            _primary_fernet().decrypt(payload)
            return value
        except (InvalidToken, ValueError, TypeError):
            pass
        try:
            return _PREFIX_V2 + _fernet().rotate(payload).decode("ascii")
        except (InvalidToken, ValueError, TypeError):
            # Не расшифровывается ни одним ключом — не трогаем, чтобы не потерять данные.
            return value

    def _decrypt(self, value: str | None) -> str:
        if not value:
            return ""
        if value.startswith(_PREFIX_V2):
            try:
                payload = value[len(_PREFIX_V2) :].encode("ascii")
                return _fernet().decrypt(payload).decode("utf-8")
            except (InvalidToken, ValueError, TypeError):
                logger.warning(
                    "Cannot decrypt %s: SECRET_KEY changed without SECRET_KEY_FALLBACKS "
                    "or the value is corrupted. Treating it as empty.",
                    self.name or "EncryptedTextField",
                )
                return ""
        if value.startswith(_PREFIX_V1):
            try:
                loaded = signing.loads(value[len(_PREFIX_V1) :], salt=_SALT)
            except signing.BadSignature:
                logger.warning("Cannot verify legacy or1: value; treating it as empty.")
                return ""
            return str(loaded)
        return value
