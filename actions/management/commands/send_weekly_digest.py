"""
Management command to send the weekly digest email to all active team members.

Usage:
    python manage.py send_weekly_digest             # sends for current week
    python manage.py send_weekly_digest --week 5 --year 2026
"""

from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone

from actions.models import ActionItem, TeamMember


class Command(BaseCommand):
    help = "Send weekly digest email to all active team members"

    def add_arguments(self, parser):
        parser.add_argument("--week", type=int, help="ISO week number (default: current)")
        parser.add_argument("--year", type=int, help="Year (default: current)")
        parser.add_argument("--dry-run", action="store_true", help="Print output without sending")

    def handle(self, *args, **options):
        now = timezone.now()
        week = options["week"] or now.isocalendar()[1]
        year = options["year"] or now.year

        items = ActionItem.objects.filter(
            year=year, week_number=week,
        ).select_related("category", "owner")

        if not items.exists():
            self.stdout.write(f"No action items for week {week}, {year}. Skipping.")
            return

        total = items.count()
        open_count = items.filter(status__in=["open", "in_progress", "blocked"]).count()
        completed_count = items.filter(status="completed").count()

        by_owner = {}
        for item in items:
            owner_name = item.owner.name if item.owner else "Unassigned"
            by_owner.setdefault(owner_name, []).append(item)

        context = {
            "week": week,
            "year": year,
            "total": total,
            "open_count": open_count,
            "completed_count": completed_count,
            "by_owner": by_owner,
        }

        html_body = render_to_string("email/weekly_digest.html", context)
        text_body = render_to_string("email/weekly_digest.txt", context)

        recipients = list(
            TeamMember.objects.filter(is_active=True).values_list("email", flat=True)
        )

        if not recipients:
            self.stdout.write("No active team members to send digest to.")
            return

        subject = f"Action Tracker - Weekly Digest (Week {week}, {year})"

        if options["dry_run"]:
            self.stdout.write(f"DRY RUN - Would send to: {', '.join(recipients)}")
            self.stdout.write(f"Subject: {subject}")
            self.stdout.write(text_body)
            return

        send_mail(
            subject=subject,
            message=text_body,
            html_message=html_body,
            from_email=None,  # uses DEFAULT_FROM_EMAIL
            recipient_list=recipients,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Digest sent to {len(recipients)} recipients for week {week}, {year}."
            )
        )
