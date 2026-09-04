from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("django_openrouter", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="openroutermodel",
            name="prompt_price",
            field=models.DecimalField(
                blank=True,
                decimal_places=12,
                help_text="Цена prompt за токен из каталога, для сортировки в админке.",
                max_digits=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="openroutermodel",
            name="completion_price",
            field=models.DecimalField(
                blank=True,
                decimal_places=12,
                help_text="Цена completion за токен из каталога, для сортировки в админке.",
                max_digits=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="openroutermodel",
            name="latency_ms",
            field=models.FloatField(
                blank=True,
                help_text="p50 TTFT по лучшему endpoint, миллисекунды.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="openroutermodel",
            name="throughput",
            field=models.FloatField(
                blank=True,
                help_text="p50 throughput (tok/s) по лучшему endpoint — нагрузка.",
                null=True,
            ),
        ),
    ]
