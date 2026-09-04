from __future__ import annotations

from decimal import Decimal

import httpx
import pytest
import respx
from django.contrib.auth.models import Permission, User
from django.urls import reverse

from django_openrouter.models import (
    OpenRouterModel,
    OpenRouterSettings,
    RequestLog,
    UsageProfile,
    UsageProfileFallback,
)

pytestmark = pytest.mark.django_db


def test_settings_changelist_redirects_to_singleton(admin_client) -> None:
    url = reverse("admin:django_openrouter_openroutersettings_changelist")
    response = admin_client.get(url)
    assert response.status_code == 302
    obj = OpenRouterSettings.load()
    assert str(obj.pk) in response["Location"]


def test_request_log_superuser_sees_changelist(
    admin_client, profile: UsageProfile, paid_model: OpenRouterModel
) -> None:
    RequestLog.objects.create(
        profile=profile,
        model=paid_model,
        status_code=200,
        cost_usd=Decimal("1.50"),
    )
    url = reverse("admin:django_openrouter_requestlog_changelist")
    response = admin_client.get(url)
    assert response.status_code == 200
    assert b"Total requests" in response.content
    assert b"1.50" in response.content or b"1.5" in response.content


def test_request_log_staff_without_perm_denied(client) -> None:
    user = User.objects.create_user("staff", password="x", is_staff=True)
    client.force_login(user)
    url = reverse("admin:django_openrouter_requestlog_changelist")
    response = client.get(url)
    assert response.status_code == 403


def test_request_log_staff_with_custom_perm(client) -> None:
    user = User.objects.create_user("logger", password="x", is_staff=True)
    perm = Permission.objects.get(
        codename="view_usage_logs",
        content_type__app_label="django_openrouter",
    )
    user.user_permissions.add(perm)
    client.force_login(user)
    url = reverse("admin:django_openrouter_requestlog_changelist")
    response = client.get(url)
    assert response.status_code == 200


def test_request_log_is_readonly(admin_client, profile: UsageProfile, paid_model) -> None:
    log = RequestLog.objects.create(
        profile=profile,
        model=paid_model,
        status_code=200,
        cost_usd=Decimal("0.1"),
    )
    url = reverse("admin:django_openrouter_requestlog_change", args=[log.pk])
    response = admin_client.get(url)
    # view_permission да, change_permission нет — Django показывает readonly.
    assert response.status_code == 200
    post = admin_client.post(url, {"status_code": 500})
    assert post.status_code in {403, 302}
    log.refresh_from_db()
    assert log.status_code == 200


@respx.mock
def test_model_admin_sync_action(
    respx_mock: respx.MockRouter,
    admin_client,
    or_settings: OpenRouterSettings,
) -> None:
    respx_mock.get("https://openrouter.ai/api/v1/models").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "openai/gpt-4",
                        "name": "GPT-4",
                        "context_length": 8192,
                        "pricing": {"prompt": "0.03", "completion": "0.06"},
                        "architecture": {"modality": "text->text"},
                        "supported_parameters": ["temperature"],
                    }
                ]
            },
        )
    )
    dummy = OpenRouterModel.objects.create(model_id="dummy/keep", name="dummy")
    url = reverse("admin:django_openrouter_openroutermodel_changelist")
    response = admin_client.post(
        url,
        {"action": "sync_with_openrouter", "_selected_action": [str(dummy.pk)]},
        follow=True,
    )
    assert response.status_code == 200
    assert OpenRouterModel.objects.filter(model_id="openai/gpt-4").exists()


def test_settings_form_keeps_blank_api_key(or_settings: OpenRouterSettings) -> None:
    from django_openrouter.admin import OpenRouterSettingsForm

    form = OpenRouterSettingsForm(
        data={
            "api_key": "",
            "base_url": or_settings.base_url,
            "request_timeout": 60,
            "max_retries": 0,
            "enabled": True,
        },
        instance=or_settings,
    )
    assert form.is_valid(), form.errors
    saved = form.save()
    assert saved.api_key == "sk-test"


def test_settings_form_replaces_api_key(or_settings: OpenRouterSettings) -> None:
    from django_openrouter.admin import OpenRouterSettingsForm

    form = OpenRouterSettingsForm(
        data={
            "api_key": "sk-new-key",
            "base_url": or_settings.base_url,
            "request_timeout": 60,
            "max_retries": 0,
            "enabled": True,
        },
        instance=or_settings,
    )
    assert form.is_valid(), form.errors
    saved = form.save()
    assert saved.api_key == "sk-new-key"


def test_settings_form_clears_api_key(or_settings: OpenRouterSettings) -> None:
    from django_openrouter.admin import OpenRouterSettingsForm

    form = OpenRouterSettingsForm(
        data={
            "api_key": "",
            "clear_api_key": True,
            "base_url": or_settings.base_url,
            "request_timeout": 60,
            "max_retries": 0,
            "enabled": True,
        },
        instance=or_settings,
    )
    assert form.is_valid(), form.errors
    saved = form.save()
    assert saved.api_key == ""


def test_settings_admin_does_not_render_stored_api_key(
    admin_client, or_settings: OpenRouterSettings
) -> None:
    or_settings.api_key = "sk-super-secret-should-not-leak"
    or_settings.save()
    url = reverse("admin:django_openrouter_openroutersettings_change", args=[or_settings.pk])
    response = admin_client.get(url)
    assert response.status_code == 200
    assert b"sk-super-secret-should-not-leak" not in response.content
    assert b"Stored (encrypted, not visible)" in response.content


def test_settings_form_empty_key_is_write_only() -> None:
    from django_openrouter.admin import OpenRouterSettingsForm

    obj = OpenRouterSettings.load()
    obj.api_key = ""
    obj.save()
    form = OpenRouterSettingsForm(instance=obj)
    assert form.initial["api_key"] == ""
    assert form.fields["clear_api_key"].disabled is True
    assert "cannot be viewed again" in str(form.fields["api_key"].help_text)


def test_usage_profile_form_rejects_inactive(paid_model: OpenRouterModel) -> None:
    from django_openrouter.admin import UsageProfileForm

    paid_model.is_active = False
    paid_model.save()
    form = UsageProfileForm(
        data={
            "name": "bad",
            "model": paid_model.pk,
            "is_active": True,
            "only_free_models": False,
        }
    )
    assert form.is_valid() is False
    assert "model" in form.errors


def test_usage_profile_form_only_free(paid_model: OpenRouterModel) -> None:
    from django_openrouter.admin import UsageProfileForm

    form = UsageProfileForm(
        data={
            "name": "free-only",
            "model": paid_model.pk,
            "is_active": True,
            "only_free_models": True,
        }
    )
    assert form.is_valid() is False


def test_fallback_form_rejects_inactive(
    profile: UsageProfile, fallback_model: OpenRouterModel
) -> None:
    from django_openrouter.admin import UsageProfileFallbackForm

    fallback_model.is_active = False
    fallback_model.save()
    form = UsageProfileFallbackForm(data={"model": fallback_model.pk, "order": 0})
    assert form.is_valid() is False


def test_fallback_formset_only_free(
    free_model: OpenRouterModel, paid_model: OpenRouterModel
) -> None:
    from django.forms.models import inlineformset_factory

    from django_openrouter.admin import (
        UsageProfileFallbackForm,
        UsageProfileFallbackInlineFormSet,
    )

    profile = UsageProfile.objects.create(
        name="free-pack",
        model=free_model,
        only_free_models=True,
    )
    formset_cls = inlineformset_factory(
        UsageProfile,
        UsageProfileFallback,
        form=UsageProfileFallbackForm,
        formset=UsageProfileFallbackInlineFormSet,
        fields=("model", "order"),
        extra=1,
    )
    prefix = "fallback"
    data = {
        f"{prefix}-TOTAL_FORMS": "1",
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
        f"{prefix}-0-model": str(paid_model.pk),
        f"{prefix}-0-order": "0",
    }
    formset = formset_cls(data, instance=profile, prefix=prefix)
    assert formset.is_valid() is False


def test_sync_action_reports_error(admin_client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    settings_obj = OpenRouterSettings.load()
    settings_obj.api_key = ""
    settings_obj.save()
    dummy = OpenRouterModel.objects.create(model_id="dummy/x", name="dummy")
    url = reverse("admin:django_openrouter_openroutermodel_changelist")
    response = admin_client.post(
        url,
        {"action": "sync_with_openrouter", "_selected_action": [str(dummy.pk)]},
        follow=True,
    )
    assert response.status_code == 200
    assert b"API key" in response.content


def test_settings_admin_status_not_set(admin_client) -> None:
    obj = OpenRouterSettings.load()
    obj.api_key = ""
    obj.save()
    url = reverse("admin:django_openrouter_openroutersettings_change", args=[obj.pk])
    response = admin_client.get(url)
    assert response.status_code == 200
    assert b"Not set" in response.content


def test_settings_has_no_add_when_exists(admin_client, or_settings: OpenRouterSettings) -> None:
    url = reverse("admin:django_openrouter_openroutersettings_add")
    response = admin_client.get(url)
    assert response.status_code == 403
