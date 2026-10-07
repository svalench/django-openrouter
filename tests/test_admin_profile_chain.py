from __future__ import annotations

import pytest
from django.urls import reverse

from django_openrouter.models import OpenRouterModel, UsageProfile, UsageProfileFallback

pytestmark = pytest.mark.django_db


def _change_data(profile: UsageProfile, model: OpenRouterModel) -> dict[str, str]:
    link = profile.fallback_links.get()
    return {
        "name": profile.name,
        "temperature": "0.4",
        "is_active": "on",
        "fallback_links-TOTAL_FORMS": "1",
        "fallback_links-INITIAL_FORMS": "1",
        "fallback_links-MIN_NUM_FORMS": "0",
        "fallback_links-MAX_NUM_FORMS": "1000",
        "fallback_links-0-id": str(link.pk),
        "fallback_links-0-profile": str(profile.pk),
        "fallback_links-0-model": str(model.pk),
        "fallback_links-0-order": "0",
        "_save": "Save",
    }


@pytest.mark.parametrize("active", [False, True])
def test_change_replaces_primary_from_inline(
    admin_client,
    profile: UsageProfile,
    paid_model: OpenRouterModel,
    free_model: OpenRouterModel,
    active: bool,
) -> None:
    paid_model.is_active = active
    paid_model.save(update_fields=["is_active"])
    url = reverse("admin:django_openrouter_usageprofile_change", args=[profile.pk])

    response = admin_client.post(url, _change_data(profile, free_model))

    assert response.status_code == 302
    profile.refresh_from_db()
    assert profile.model_id == free_model.pk
    assert profile.ordered_models() == [free_model]


def test_change_enables_free_only_while_replacing_paid_primary(
    admin_client,
    profile: UsageProfile,
    free_model: OpenRouterModel,
) -> None:
    data = _change_data(profile, free_model)
    data["only_free_models"] = "on"
    url = reverse("admin:django_openrouter_usageprofile_change", args=[profile.pk])

    response = admin_client.post(url, data)

    assert response.status_code == 302
    profile.refresh_from_db()
    assert profile.only_free_models
    assert profile.model_id == free_model.pk
    assert profile.ordered_models() == [free_model]


@pytest.mark.parametrize("inactive", [False, True])
def test_invalid_chain_shows_errors_without_changing_profile(
    admin_client,
    profile: UsageProfile,
    paid_model: OpenRouterModel,
    fallback_model: OpenRouterModel,
    inactive: bool,
) -> None:
    # Start with a stale, inactive primary in both cases. The submitted model
    # either is inactive or violates the newly enabled free-only restriction.
    paid_model.is_active = False
    paid_model.save(update_fields=["is_active"])
    fallback_model.is_active = not inactive
    fallback_model.save(update_fields=["is_active"])
    data = _change_data(profile, fallback_model)
    if not inactive:
        data["only_free_models"] = "on"
    url = reverse("admin:django_openrouter_usageprofile_change", args=[profile.pk])

    response = admin_client.post(url, data)

    assert response.status_code == 200
    formset = response.context["inline_admin_formsets"][0].formset
    assert "model" in formset.forms[0].errors
    profile.refresh_from_db()
    assert not profile.only_free_models
    assert profile.model_id == paid_model.pk
    assert profile.ordered_models() == [paid_model]


def test_change_preserves_temperature_validation(
    admin_client,
    profile: UsageProfile,
    paid_model: OpenRouterModel,
    free_model: OpenRouterModel,
) -> None:
    data = _change_data(profile, free_model)
    data["temperature"] = "3"
    url = reverse("admin:django_openrouter_usageprofile_change", args=[profile.pk])

    response = admin_client.post(url, data)

    assert response.status_code == 200
    assert "temperature" in response.context["adminform"].form.errors
    profile.refresh_from_db()
    assert profile.temperature is None
    assert profile.model_id == paid_model.pk


@pytest.mark.parametrize("active", [False, True])
def test_change_deletes_last_model_and_clears_primary(
    admin_client,
    profile: UsageProfile,
    paid_model: OpenRouterModel,
    active: bool,
) -> None:
    paid_model.is_active = active
    paid_model.save(update_fields=["is_active"])
    data = _change_data(profile, paid_model)
    data["fallback_links-0-DELETE"] = "on"
    url = reverse("admin:django_openrouter_usageprofile_change", args=[profile.pk])

    response = admin_client.post(url, data)

    assert response.status_code == 302
    profile.refresh_from_db()
    assert profile.model_id is None
    assert profile.ordered_models() == []
    assert not profile.fallback_links.exists()


@pytest.mark.parametrize("delete_primary", [False, True])
def test_change_syncs_primary_from_remaining_chain_order(
    admin_client,
    profile: UsageProfile,
    paid_model: OpenRouterModel,
    fallback_model: OpenRouterModel,
    delete_primary: bool,
) -> None:
    data = _change_data(profile, paid_model)
    second = UsageProfileFallback.objects.create(profile=profile, model=fallback_model, order=1)
    data.update(
        {
            "fallback_links-TOTAL_FORMS": "2",
            "fallback_links-INITIAL_FORMS": "2",
            "fallback_links-0-order": "10",
            "fallback_links-1-id": str(second.pk),
            "fallback_links-1-profile": str(profile.pk),
            "fallback_links-1-model": str(fallback_model.pk),
            "fallback_links-1-order": "5",
        }
    )
    if delete_primary:
        data["fallback_links-0-DELETE"] = "on"
    url = reverse("admin:django_openrouter_usageprofile_change", args=[profile.pk])

    response = admin_client.post(url, data)

    assert response.status_code == 302
    profile.refresh_from_db()
    assert profile.model_id == fallback_model.pk
    expected = [fallback_model] if delete_primary else [fallback_model, paid_model]
    assert profile.ordered_models() == expected
    orders = list(profile.fallback_links.values_list("order", flat=True))
    assert orders == list(range(len(expected)))


def test_change_saves_settings_with_unchanged_chain(
    admin_client,
    profile: UsageProfile,
    paid_model: OpenRouterModel,
) -> None:
    url = reverse("admin:django_openrouter_usageprofile_change", args=[profile.pk])

    response = admin_client.post(url, _change_data(profile, paid_model))

    assert response.status_code == 302
    profile.refresh_from_db()
    assert profile.model_id == paid_model.pk
    assert profile.ordered_models() == [paid_model]
    assert profile.temperature == 0.4
