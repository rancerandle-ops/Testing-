"""
Populate the database with sample data for testing.

Usage:
    python manage.py seed_demo_data
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from actions.models import ActionItem, ActionResponse, Category, TeamMember


class Command(BaseCommand):
    help = "Seed database with demo categories, team members, and action items"

    def handle(self, *args, **options):
        # Categories
        categories = [
            ("Engineering", "#6366f1"),
            ("Design", "#ec4899"),
            ("Marketing", "#f59e0b"),
            ("Operations", "#10b981"),
            ("Product", "#8b5cf6"),
        ]
        cat_objects = {}
        for name, color in categories:
            obj, created = Category.objects.get_or_create(
                name=name, defaults={"color": color}
            )
            cat_objects[name] = obj
            status = "created" if created else "exists"
            self.stdout.write(f"  Category '{name}' - {status}")

        # Team members
        members = [
            ("Alice Chen", "alice@example.com"),
            ("Bob Martinez", "bob@example.com"),
            ("Carol Johnson", "carol@example.com"),
            ("David Kim", "david@example.com"),
        ]
        member_objects = {}
        for name, email in members:
            obj, created = TeamMember.objects.get_or_create(
                email=email, defaults={"name": name}
            )
            member_objects[name] = obj
            status = "created" if created else "exists"
            self.stdout.write(f"  Member '{name}' - {status}")

        # Admin user
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", "admin")
            self.stdout.write("  Superuser 'admin' created (password: admin)")
        else:
            self.stdout.write("  Superuser 'admin' already exists")

        # Sample action items
        now = timezone.now()
        week = now.isocalendar()[1]
        year = now.year

        sample_items = [
            ("Set up CI/CD pipeline for staging", "Engineering", "Alice Chen", "high", "open"),
            ("Design new onboarding flow mockups", "Design", "Bob Martinez", "medium", "in_progress"),
            ("Write Q1 blog post", "Marketing", "Carol Johnson", "medium", "open"),
            ("Migrate database to new cluster", "Operations", "David Kim", "urgent", "blocked"),
            ("Review API rate limiting strategy", "Engineering", "Alice Chen", "high", "open"),
            ("Update brand guidelines document", "Design", "Bob Martinez", "low", "completed"),
            ("Plan sprint retro for next week", "Product", "Carol Johnson", "medium", "open"),
        ]

        for title, cat, owner, priority, status in sample_items:
            item, created = ActionItem.objects.get_or_create(
                title=title,
                defaults={
                    "category": cat_objects[cat],
                    "owner": member_objects[owner],
                    "priority": priority,
                    "status": status,
                    "week_number": week,
                    "year": year,
                },
            )
            if created:
                self.stdout.write(f"  Item '{title}' - created")
                # Add a sample response to some items
                if status == "in_progress":
                    ActionResponse.objects.create(
                        action_item=item,
                        author=member_objects[owner],
                        body="Working on this — initial draft should be ready by EOD.",
                    )
            else:
                self.stdout.write(f"  Item '{title}' - exists")

        self.stdout.write(self.style.SUCCESS("\nDemo data seeded successfully."))
