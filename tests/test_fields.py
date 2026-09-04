from __future__ import annotations

from django_openrouter.fields import EncryptedTextField


def test_encrypted_field_none_and_plaintext() -> None:
    field = EncryptedTextField()
    assert field.to_python(None) == ""
    assert field.get_prep_value(None) == ""
    assert field.to_python("plain") == "plain"
    encrypted = field.get_prep_value("secret")
    assert encrypted.startswith("or1:")
    assert field.to_python(encrypted) == "secret"
    assert field.get_prep_value(encrypted) == encrypted


def test_encrypted_field_bad_signature() -> None:
    field = EncryptedTextField()
    assert field.to_python("or1:not-a-valid-signature") == ""
    assert field.from_db_value("", None, None) == ""
