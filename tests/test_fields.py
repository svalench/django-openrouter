from __future__ import annotations

import pytest
from django.core import signing
from django.db import connection

from django_openrouter.fields import EncryptedTextField
from django_openrouter.models import OpenRouterSettings

pytestmark = pytest.mark.django_db

_SALT = "django_openrouter.api_key"


def test_encrypted_field_none_and_plaintext() -> None:
    field = EncryptedTextField()
    assert field.to_python(None) == ""
    assert field.get_prep_value(None) == ""
    assert field.to_python("plain") == "plain"
    encrypted = field.get_prep_value("secret")
    assert encrypted.startswith("or2:")
    assert "secret" not in encrypted
    assert field.to_python(encrypted) == "secret"
    assert field.get_prep_value(encrypted) == encrypted


def test_encrypted_field_bad_signature() -> None:
    field = EncryptedTextField()
    assert field.to_python("or2:not-a-valid-token") == ""
    assert field.to_python("or1:not-a-valid-signature") == ""
    assert field.from_db_value("", None, None) == ""


def test_encrypted_field_migrates_legacy_signing() -> None:
    field = EncryptedTextField()
    legacy = "or1:" + signing.dumps("old-secret", salt=_SALT)
    assert field.to_python(legacy) == "old-secret"
    migrated = field.get_prep_value(legacy)
    assert migrated.startswith("or2:")
    assert field.to_python(migrated) == "old-secret"
    assert field.get_prep_value("or1:not-a-valid-signature") == ""


def test_encrypted_field_value_to_string_is_ciphertext() -> None:
    obj = OpenRouterSettings.load()
    obj.api_key = "sk-dump-secret"
    obj.save()
    field = OpenRouterSettings._meta.get_field("api_key")
    dumped = field.value_to_string(obj)
    assert dumped.startswith("or2:")
    assert "sk-dump-secret" not in dumped


def test_api_key_column_is_ciphertext() -> None:
    obj = OpenRouterSettings.load()
    obj.api_key = "sk-secret-value"
    obj.save()
    with connection.cursor() as cursor:
        cursor.execute("SELECT api_key FROM django_openrouter_openroutersettings WHERE id = 1")
        raw = cursor.fetchone()[0]
    assert raw.startswith("or2:")
    assert "sk-secret-value" not in raw
    loaded = OpenRouterSettings.objects.get(pk=1)
    assert loaded.api_key == "sk-secret-value"
