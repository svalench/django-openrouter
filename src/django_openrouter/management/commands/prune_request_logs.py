from argparse import ArgumentParser
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.translation import gettext as _

from django_openrouter.models import RequestLog, _period_start

_BATCH_SIZE = 5000


class Command(BaseCommand):
    help = _(
        "Delete RequestLog rows older than N days. "
        "The current month is always kept: monthly limits are computed from it."
    )

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--days", type=int, default=90, help=_("Keep logs for N days."))
        parser.add_argument(
            "--dry-run", action="store_true", help=_("Only print how many rows match.")
        )

    def handle(self, *args: object, **options: object) -> None:
        days = int(str(options["days"]))
        if days < 1:
            raise CommandError(_("--days must be a positive integer."))
        # Не трогаем текущий месяц, иначе месячные лимиты и бюджеты обнулятся.
        cutoff = min(timezone.now() - timedelta(days=days), _period_start("month"))
        old = RequestLog.objects.filter(created_at__lt=cutoff)
        if options["dry_run"]:
            self.stdout.write(_("old=%(old)s") % {"old": old.count()})
            return
        self.stdout.write(
            self.style.SUCCESS(_("deleted old=%(old)s") % {"old": _delete_in_batches(old)})
        )


def _delete_in_batches(queryset: QuerySet[RequestLog]) -> int:
    # Пачками, чтобы не держать огромную транзакцию и блокировки на таблице логов.
    total = 0
    while True:
        ids = list(queryset.values_list("pk", flat=True)[:_BATCH_SIZE])
        if not ids:
            return total
        deleted, _details = RequestLog.objects.filter(pk__in=ids).delete()
        total += deleted
