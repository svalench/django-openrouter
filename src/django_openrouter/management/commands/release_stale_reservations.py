from argparse import ArgumentParser
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.translation import gettext as _

from django_openrouter.models import (
    CLIENT_CLOSED_STATUS,
    RESERVATION_PENDING_MESSAGE,
    RESERVATION_RELEASED_MESSAGE,
    RequestLog,
)


class Command(BaseCommand):
    help = _(
        "Release budget reservations left pending by crashed workers. "
        "Reservations for responses without usage are kept."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--minutes",
            type=int,
            default=60,
            help=_("Release reservations older than N minutes."),
        )
        parser.add_argument(
            "--dry-run", action="store_true", help=_("Only print how many rows match.")
        )

    def handle(self, *args: object, **options: object) -> None:
        minutes = int(str(options["minutes"]))
        if minutes < 1:
            raise CommandError(_("--minutes must be a positive integer."))
        # Живая попытка не длится дольше request_timeout × (retries + 1): порог с запасом.
        stale = RequestLog.objects.filter(
            status_code=0,
            error_message=RESERVATION_PENDING_MESSAGE,
            created_at__lt=timezone.now() - timedelta(minutes=minutes),
        )
        if options["dry_run"]:
            self.stdout.write(_("stale=%(count)s") % {"count": stale.count()})
            return
        released = stale.update(
            status_code=CLIENT_CLOSED_STATUS,
            cost_usd=Decimal("0"),
            error_message=RESERVATION_RELEASED_MESSAGE,
        )
        self.stdout.write(self.style.SUCCESS(_("released=%(count)s") % {"count": released}))
