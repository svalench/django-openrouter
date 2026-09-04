from django.db import migrations, models
import django.db.models.deletion


def _copy_primary_into_chain(apps, schema_editor):
    """Primary FK становится первой строкой цепочки (order=0), без дублей."""
    UsageProfile = apps.get_model("django_openrouter", "UsageProfile")
    UsageProfileFallback = apps.get_model("django_openrouter", "UsageProfileFallback")
    for profile in UsageProfile.objects.all():
        if not profile.model_id:
            continue
        links = list(
            UsageProfileFallback.objects.filter(profile_id=profile.pk).order_by("order", "id")
        )
        primary_link = next((link for link in links if link.model_id == profile.model_id), None)
        if primary_link is None:
            primary_link = UsageProfileFallback.objects.create(
                profile_id=profile.pk,
                model_id=profile.model_id,
                order=0,
            )
        others = [link for link in links if link.model_id != profile.model_id]
        for index, link in enumerate([primary_link, *others]):
            if link.order != index:
                link.order = index
                link.save(update_fields=["order"])


class Migration(migrations.Migration):
    dependencies = [
        ("django_openrouter", "0002_openroutermodel_catalog_stats"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usageprofile",
            name="model",
            field=models.ForeignKey(
                blank=True,
                help_text="Первая модель цепочки (синхронизируется из списка).",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="profiles",
                to="django_openrouter.openroutermodel",
            ),
        ),
        migrations.AlterModelOptions(
            name="usageprofilefallback",
            options={
                "ordering": ["order", "id"],
                "verbose_name": "Profile model",
                "verbose_name_plural": "Profile models",
            },
        ),
        migrations.RunPython(_copy_primary_into_chain, migrations.RunPython.noop),
    ]
