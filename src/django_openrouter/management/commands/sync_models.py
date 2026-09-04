from argparse import ArgumentParser

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _

from django_openrouter.exceptions import OpenRouterError
from django_openrouter.sync import sync_openrouter_models


class Command(BaseCommand):
    help = _("Fetch GET /api/v1/models and upsert the local OpenRouter catalog.")

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--api-key",
            dest="api_key",
            default=None,
            help=_("Override API key for this run."),
        )

    def handle(self, *args: object, **options: object) -> None:
        api_key = options.get("api_key")
        key = str(api_key) if api_key else None
        try:
            summary = sync_openrouter_models(api_key=key)
        except (OpenRouterError, OSError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                _(
                    "created=%(created)s updated=%(updated)s "
                    "deactivated=%(deactivated)s remote=%(total)s"
                )
                % {
                    "created": summary.created,
                    "updated": summary.updated,
                    "deactivated": summary.deactivated,
                    "total": summary.total_remote,
                }
            )
        )
