from __future__ import annotations

from decimal import Decimal

import httpx
import pytest
import respx
from django.contrib.auth.models import Permission, User
from django.core.cache import cache
from django.urls import reverse

from django_openrouter.models import (
    OpenRouterModel,
    OpenRouterSettings,
    RequestLog,
    UsageProfile,
    UsageProfileFallback,
)

pytestmark = pytest.mark.django_db

MODELS_URL = "https://openrouter.ai/api/v1/models"


def _catalog_item(
    model_id: str,
    name: str,
    *,
    prompt: str = "0.001",
    completion: str = "0.002",
) -> dict:
    return {
        "id": model_id,
        "name": name,
        "context_length": 8192,
        "pricing": {"prompt": prompt, "completion": completion},
        "architecture": {"modality": "text->text"},
        "supported_parameters": ["temperature"],
    }


def _mock_endpoints(respx_mock: respx.MockRouter, handler=None) -> respx.Route:
    route = respx_mock.get(url__regex=r"https://openrouter\.ai/api/v1/models/.+/endpoints")
    if handler is not None:
        return route.mock(side_effect=handler)
    return route.mock(
        return_value=httpx.Response(
            200,
            json={
                "data": {
                    "endpoints": [
                        {
                            "latency_last_30m": {"p50": 0.25},
                            "throughput_last_30m": {"p50": 40.0},
                        }
                    ]
                }
            },
        )
    )


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


def test_openrouter_model_change_is_readonly(admin_client, paid_model: OpenRouterModel) -> None:
    from django_openrouter.config import mark_catalog_fresh

    mark_catalog_fresh()
    url = reverse("admin:django_openrouter_openroutermodel_change", args=[paid_model.pk])
    response = admin_client.get(url)
    assert response.status_code == 200
    post = admin_client.post(url, {"name": "hacked", "is_active": False})
    assert post.status_code in {403, 302}
    paid_model.refresh_from_db()
    assert paid_model.name == "Claude 3.5 Sonnet"
    assert paid_model.is_active is True
    add_url = reverse("admin:django_openrouter_openroutermodel_add")
    assert admin_client.get(add_url).status_code == 403


@respx.mock
def test_model_admin_sync_action(
    respx_mock: respx.MockRouter,
    admin_client,
    or_settings: OpenRouterSettings,
) -> None:
    cache.clear()
    respx_mock.get(MODELS_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    _catalog_item("openai/gpt-4", "GPT-4", prompt="0.03", completion="0.06")
                ]
            },
        )
    )
    _mock_endpoints(respx_mock)
    dummy = OpenRouterModel.objects.create(model_id="dummy/keep", name="dummy")
    url = reverse("admin:django_openrouter_openroutermodel_changelist")
    response = admin_client.post(
        url,
        {"action": "sync_with_openrouter", "_selected_action": [str(dummy.pk)]},
        follow=True,
    )
    assert response.status_code == 200
    gpt = OpenRouterModel.objects.get(model_id="openai/gpt-4")
    assert gpt.prompt_price == Decimal("0.03")
    assert gpt.latency_ms == pytest.approx(250.0)


def test_settings_form_keeps_blank_api_key(or_settings: OpenRouterSettings) -> None:
    from django_openrouter.admin import OpenRouterSettingsForm

    form = OpenRouterSettingsForm(
        data={
            "api_key": "",
            "base_url": or_settings.base_url,
            "request_timeout": 60,
            "max_retries": 0,
            "max_parallel_requests": 10,
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
            "max_parallel_requests": 10,
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
            "max_parallel_requests": 10,
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


def test_usage_profile_form_hides_model_field() -> None:
    from django_openrouter.admin import UsageProfileForm

    form = UsageProfileForm()
    assert "model" not in form.fields


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


def test_fallback_formset_allows_empty_chain(free_model: OpenRouterModel) -> None:
    from django.forms.models import inlineformset_factory

    from django_openrouter.admin import (
        UsageProfileFallbackForm,
        UsageProfileFallbackInlineFormSet,
    )

    profile = UsageProfile.objects.create(name="empty-chain", model=free_model)
    UsageProfileFallback.objects.filter(profile=profile).delete()
    profile.refresh_from_db()
    formset_cls = inlineformset_factory(
        UsageProfile,
        UsageProfileFallback,
        form=UsageProfileFallbackForm,
        formset=UsageProfileFallbackInlineFormSet,
        fields=("model", "order"),
        extra=1,
        min_num=0,
        validate_min=False,
    )
    prefix = "fallback"
    data = {
        f"{prefix}-TOTAL_FORMS": "1",
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
        f"{prefix}-0-model": "",
        f"{prefix}-0-order": "0",
    }
    formset = formset_cls(data, instance=profile, prefix=prefix)
    assert formset.is_valid(), formset.errors


def test_admin_add_profile_without_models(admin_client) -> None:
    url = reverse("admin:django_openrouter_usageprofile_add")
    prefix = "fallback_links"
    response = admin_client.post(
        url,
        {
            "name": "nomodels",
            "is_active": "on",
            f"{prefix}-TOTAL_FORMS": "1",
            f"{prefix}-INITIAL_FORMS": "0",
            f"{prefix}-MIN_NUM_FORMS": "0",
            f"{prefix}-MAX_NUM_FORMS": "1000",
            f"{prefix}-0-model": "",
            f"{prefix}-0-order": "0",
        },
        follow=True,
    )
    assert response.status_code == 200
    created = UsageProfile.objects.get(name="nomodels")
    assert created.model_id is None
    assert created.ordered_models() == []


def test_admin_add_profile_syncs_primary(
    admin_client, paid_model: OpenRouterModel, fallback_model: OpenRouterModel
) -> None:
    url = reverse("admin:django_openrouter_usageprofile_add")
    prefix = "fallback_links"
    response = admin_client.post(
        url,
        {
            "name": "pack",
            "is_active": "on",
            f"{prefix}-TOTAL_FORMS": "2",
            f"{prefix}-INITIAL_FORMS": "0",
            f"{prefix}-MIN_NUM_FORMS": "1",
            f"{prefix}-MAX_NUM_FORMS": "1000",
            f"{prefix}-0-id": "",
            f"{prefix}-0-model": str(fallback_model.pk),
            f"{prefix}-0-order": "5",
            f"{prefix}-1-id": "",
            f"{prefix}-1-model": str(paid_model.pk),
            f"{prefix}-1-order": "1",
        },
        follow=True,
    )
    assert response.status_code == 200
    created = UsageProfile.objects.get(name="pack")
    assert created.model_id == paid_model.pk
    assert [item.model_id for item in created.ordered_models()] == [
        paid_model.model_id,
        fallback_model.model_id,
    ]


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


@respx.mock
def test_model_changelist_fetches_and_caches(
    respx_mock: respx.MockRouter,
    admin_client,
    or_settings: OpenRouterSettings,
) -> None:
    cache.clear()
    models_route = respx_mock.get(MODELS_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    _catalog_item("openai/gpt-4", "GPT-4", prompt="0.03", completion="0.06")
                ]
            },
        )
    )
    _mock_endpoints(respx_mock)
    url = reverse("admin:django_openrouter_openroutermodel_changelist")
    first = admin_client.get(url)
    assert first.status_code == 200
    assert b"GPT-4" in first.content
    assert b"$30000" in first.content
    assert models_route.call_count == 1
    second = admin_client.get(url)
    assert second.status_code == 200
    assert models_route.call_count == 1
    model = OpenRouterModel.objects.get(model_id="openai/gpt-4")
    assert model.latency_ms == pytest.approx(250.0)
    assert model.throughput == pytest.approx(40.0)


@respx.mock
def test_model_changelist_sorts_by_metrics(admin_client) -> None:
    cache.clear()
    OpenRouterModel.objects.create(
        model_id="vendor/slow-m",
        name="Slow Model",
        latency_ms=1000.0,
        throughput=10.0,
        prompt_price=Decimal("0.03"),
        completion_price=Decimal("0.06"),
    )
    OpenRouterModel.objects.create(
        model_id="vendor/fast-m",
        name="Fast Model",
        latency_ms=100.0,
        throughput=80.0,
        prompt_price=Decimal("0.001"),
        completion_price=Decimal("0.002"),
    )
    from django_openrouter.config import mark_catalog_fresh

    mark_catalog_fresh()
    url = reverse("admin:django_openrouter_openroutermodel_changelist")

    # list_display: checkbox, name, latency_ms, throughput, price, params, is_active
    latency_asc = admin_client.get(url, {"o": "2"})
    names = [obj.model_id for obj in latency_asc.context["cl"].result_list]
    assert names[0] == "vendor/fast-m"
    assert names[1] == "vendor/slow-m"

    throughput_desc = admin_client.get(url, {"o": "-3"})
    names = [obj.model_id for obj in throughput_desc.context["cl"].result_list]
    assert names[0] == "vendor/fast-m"

    price_asc = admin_client.get(url, {"o": "4"})
    names = [obj.model_id for obj in price_asc.context["cl"].result_list]
    assert names[0] == "vendor/fast-m"


@respx.mock
def test_model_changelist_api_error_keeps_page(
    respx_mock: respx.MockRouter,
    admin_client,
    or_settings: OpenRouterSettings,
) -> None:
    cache.clear()
    OpenRouterModel.objects.create(model_id="local/kept", name="Kept Local")
    respx_mock.get(MODELS_URL).mock(return_value=httpx.Response(500, json={"error": "nope"}))
    url = reverse("admin:django_openrouter_openroutermodel_changelist")
    response = admin_client.get(url)
    assert response.status_code == 200
    assert b"Kept Local" in response.content


def test_model_changelist_shows_parameter_size(
    admin_client, paid_model: OpenRouterModel
) -> None:
    from django_openrouter.config import mark_catalog_fresh

    paid_model.model_id = "meta-llama/llama-3.1-70b-instruct"
    paid_model.name = "Llama 3.1 70B Instruct"
    paid_model.parameter_label = "70B"
    paid_model.parameter_count = 70_000_000_000
    paid_model.save()
    OpenRouterModel.objects.create(
        model_id="openai/gpt-4",
        name="GPT-4",
        parameter_label="",
        parameter_count=None,
    )
    mark_catalog_fresh()
    url = reverse("admin:django_openrouter_openroutermodel_changelist")
    response = admin_client.get(url)
    assert response.status_code == 200
    content = response.content.decode()
    assert "70B" in content
    assert "—" in content


@respx.mock
def test_manual_sync_hits_api_even_if_cache_fresh(
    respx_mock: respx.MockRouter,
    admin_client,
    or_settings: OpenRouterSettings,
) -> None:
    cache.clear()
    models_route = respx_mock.get(MODELS_URL).mock(
        return_value=httpx.Response(200, json={"data": [_catalog_item("openai/gpt-4", "GPT-4")]})
    )
    _mock_endpoints(respx_mock)
    url = reverse("admin:django_openrouter_openroutermodel_changelist")
    admin_client.get(url)
    assert models_route.call_count == 1
    dummy = OpenRouterModel.objects.get(model_id="openai/gpt-4")
    admin_client.post(
        url,
        {"action": "sync_with_openrouter", "_selected_action": [str(dummy.pk)]},
    )
    assert models_route.call_count == 2


def _autocomplete_params(**extra: str) -> dict[str, str]:
    params = {
        "app_label": "django_openrouter",
        "model_name": "usageprofilefallback",
        "field_name": "model",
        "term": "",
    }
    params.update(extra)
    return params


def test_format_model_choice_label_includes_metrics(paid_model: OpenRouterModel) -> None:
    from django_openrouter.admin import format_model_choice_label

    paid_model.latency_ms = 250.0
    paid_model.throughput = 40.0
    paid_model.prompt_price = Decimal("0.000003")
    paid_model.completion_price = Decimal("0.000015")
    label = format_model_choice_label(paid_model)
    assert "Claude 3.5 Sonnet" in label
    assert "$3" in label
    assert "$15" in label
    assert "250 ms" in label
    assert "40 tok/s" in label


def test_autocomplete_text_includes_price_and_speed(
    admin_client, paid_model: OpenRouterModel
) -> None:
    paid_model.latency_ms = 250.0
    paid_model.throughput = 40.0
    paid_model.prompt_price = Decimal("0.000003")
    paid_model.completion_price = Decimal("0.000015")
    paid_model.save()
    response = admin_client.get(
        reverse("admin:autocomplete"),
        _autocomplete_params(term="claude"),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["results"]
    text = payload["results"][0]["text"]
    assert "250 ms" in text
    assert "$3" in text


def test_autocomplete_price_and_speed_filters(
    admin_client, paid_model: OpenRouterModel, free_model: OpenRouterModel
) -> None:
    paid_model.prompt_price = Decimal("0.000003")
    paid_model.latency_ms = 900.0
    paid_model.save()
    free_model.prompt_price = Decimal("0")
    free_model.latency_ms = 100.0
    free_model.save()
    url = reverse("admin:autocomplete")
    free = admin_client.get(url, _autocomplete_params(price="free"))
    ids = {item["id"] for item in free.json()["results"]}
    assert str(free_model.pk) in ids
    assert str(paid_model.pk) not in ids
    fast = admin_client.get(url, _autocomplete_params(speed="fast"))
    ids = {item["id"] for item in fast.json()["results"]}
    assert str(free_model.pk) in ids
    assert str(paid_model.pk) not in ids


def test_model_changelist_price_speed_sidebar(admin_client) -> None:
    from django_openrouter.config import mark_catalog_fresh

    cache.clear()
    mark_catalog_fresh()
    OpenRouterModel.objects.create(
        model_id="vendor/free-fast",
        name="Free Fast",
        prompt_price=Decimal("0"),
        latency_ms=80.0,
        is_active=True,
    )
    OpenRouterModel.objects.create(
        model_id="vendor/exp-slow",
        name="Expensive Slow",
        prompt_price=Decimal("0.00002"),
        latency_ms=2000.0,
        is_active=True,
    )
    url = reverse("admin:django_openrouter_openroutermodel_changelist")
    response = admin_client.get(url)
    assert response.status_code == 200
    assert b"Cheap" in response.content
    assert b"Fast" in response.content
    free_page = admin_client.get(url, {"price": "free"})
    ids = [obj.model_id for obj in free_page.context["cl"].result_list]
    assert ids == ["vendor/free-fast"]
    slow_page = admin_client.get(url, {"speed": "slow"})
    ids = [obj.model_id for obj in slow_page.context["cl"].result_list]
    assert ids == ["vendor/exp-slow"]


def test_profile_form_includes_filter_media(admin_client, profile: UsageProfile) -> None:
    url = reverse("admin:django_openrouter_usageprofile_change", args=[profile.pk])
    response = admin_client.get(url)
    assert response.status_code == 200
    assert b"model_choice_filters.js" in response.content
    assert b"model_choice_filters.css" in response.content



def _assign_action(
    admin_client,
    pks: list[str],
    extra: dict | None = None,
    follow: bool = False,
):
    payload = {"action": "assign_to_profile", "_selected_action": pks}
    payload.update(extra or {})
    return admin_client.post(
        reverse("admin:django_openrouter_openroutermodel_changelist"),
        payload,
        follow=follow,
    )


def test_assign_action_shows_intermediate_page(
    admin_client,
    profile: UsageProfile,
    paid_model: OpenRouterModel,
    fallback_model: OpenRouterModel,
) -> None:
    from django_openrouter.config import mark_catalog_fresh

    mark_catalog_fresh()
    response = _assign_action(
        admin_client, [str(paid_model.pk), str(fallback_model.pk)]
    )
    assert response.status_code == 200
    content = response.content.decode()
    assert "Usage profile" in content  # поле выбора профиля
    assert "anthropic/claude-3.5-sonnet" in content  # список выбранных моделей
    # Сигнал ensure_primary_in_chain уже прописал primary; экшен ничего не трогал.
    assert list(UsageProfileFallback.objects.values_list("model_id", "order")) == [
        (paid_model.pk, 0)
    ]


def test_assign_action_appends_models_to_chain(
    admin_client,
    profile: UsageProfile,
    paid_model: OpenRouterModel,
    fallback_model: OpenRouterModel,
) -> None:
    from django_openrouter.config import mark_catalog_fresh

    mark_catalog_fresh()
    response = _assign_action(
        admin_client,
        [str(fallback_model.pk)],
        extra={"apply": "", "profile": str(profile.pk)},
    )
    assert response.status_code == 302
    # Сигнал уже прописал primary первой строкой; назначенная модель — после.
    links = list(UsageProfileFallback.objects.order_by("order", "id"))
    assert [(link.model_id, link.order) for link in links] == [
        (paid_model.pk, 0),
        (fallback_model.pk, 1),
    ]
    assert profile.ordered_models() == [paid_model, fallback_model]
    profile.refresh_from_db()
    assert profile.model_id == paid_model.pk  # primary не затёрт


def test_assign_action_keeps_chain_order_and_skips_duplicates(
    admin_client,
    profile: UsageProfile,
    paid_model: OpenRouterModel,
    fallback_model: OpenRouterModel,
    free_model: OpenRouterModel,
) -> None:
    from django_openrouter.config import mark_catalog_fresh

    mark_catalog_fresh()
    # Сигнал ensure_primary_in_chain уже создал (paid_model, order=0).
    UsageProfileFallback.objects.create(profile=profile, model=fallback_model, order=1)
    response = _assign_action(
        admin_client,
        [str(paid_model.pk), str(free_model.pk)],  # paid уже в цепочке
        extra={"apply": "", "profile": str(profile.pk)},
        follow=True,
    )
    assert response.status_code == 200
    links = list(UsageProfileFallback.objects.order_by("order", "id"))
    assert [(link.model_id, link.order) for link in links] == [
        (paid_model.pk, 0),
        (fallback_model.pk, 1),
        (free_model.pk, 2),
    ]
    assert "already in the chain" in response.content.decode()


def test_assign_action_skips_inactive_and_not_free(
    admin_client,
    profile: UsageProfile,
    paid_model: OpenRouterModel,
    free_model: OpenRouterModel,
) -> None:
    from django_openrouter.config import mark_catalog_fresh

    mark_catalog_fresh()
    inactive = OpenRouterModel.objects.create(
        model_id="vendor/off", name="Off", is_active=False
    )
    free_profile = UsageProfile.objects.create(
        name="freep", model=free_model, only_free_models=True
    )
    response = _assign_action(
        admin_client,
        [str(inactive.pk), str(paid_model.pk)],
        extra={"apply": "", "profile": str(free_profile.pk)},
        follow=True,
    )
    content = response.content.decode()
    assert "inactive" in content
    assert "not free" in content
    # В цепочку free-профиля попала только первичная free-модель.
    links = list(UsageProfileFallback.objects.filter(profile=free_profile))
    assert [(link.model_id, link.order) for link in links] == [(free_model.pk, 0)]


def test_assign_action_invalid_form_renders_page(
    admin_client,
    profile: UsageProfile,
    paid_model: OpenRouterModel,
) -> None:
    from django_openrouter.config import mark_catalog_fresh

    mark_catalog_fresh()
    response = _assign_action(
        admin_client,
        [str(paid_model.pk)],
        extra={"apply": ""},  # нет profile — форма невалидна
    )
    assert response.status_code == 200
    # Сигнал ensure_primary_in_chain прописал primary; форма не применялась.
    assert list(UsageProfileFallback.objects.values_list("model_id", "order")) == [
        (paid_model.pk, 0)
    ]


def test_profile_changelist_shows_usage_totals(
    admin_client,
    profile: UsageProfile,
    paid_model: OpenRouterModel,
) -> None:
    unused = UsageProfile.objects.create(name="idle", model=paid_model)
    RequestLog.objects.create(
        profile=profile,
        model=paid_model,
        status_code=200,
        latency_ms=100,
        cost_usd=Decimal("1.00"),
    )
    RequestLog.objects.create(
        profile=profile,
        model=paid_model,
        status_code=200,
        latency_ms=300,
        cost_usd=Decimal("3.00"),
    )
    url = reverse("admin:django_openrouter_usageprofile_changelist")
    response = admin_client.get(url)
    assert response.status_code == 200
    content = response.content.decode()
    assert "200 ms" in content
    assert "400 ms" in content
    assert "$2" in content
    assert "$4" in content
    assert unused.name in content
    assert "—" in content


def test_profile_changelist_unused_only_emdash(admin_client, profile: UsageProfile) -> None:
    url = reverse("admin:django_openrouter_usageprofile_changelist")
    response = admin_client.get(url)
    assert response.status_code == 200
    content = response.content.decode()
    assert profile.name in content
    assert "—" in content
    assert "200 ms" not in content
