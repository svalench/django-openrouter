# django-openrouter API key encryption

## Done
- EncryptedTextField: Fernet (`or2:`), ключ из SHA-256(SECRET_KEY)
- legacy `or1:` (signing) читается и при save мигрирует в `or2:`
- dumpdata пишет ciphertext (`value_to_string`)
- Admin write-only: ключ не рендерится, статус Stored/Not set, blank = keep, clear checkbox
- pytest 88 passed, coverage 91%, ruff + mypy clean

DONE
