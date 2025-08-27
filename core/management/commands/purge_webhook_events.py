# -*- coding: utf-8 -*-
"""
Created on Sun Aug 17 01:38:22 2025

@author: Home
"""

# core/management/commands/purge_webhook_events.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import WebhookEvent

class Command(BaseCommand):
    help = "Purge old WebhookEvent rows to keep the table lean."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=90, help="Delete events older than N days (default: 90)")
        parser.add_argument("--dry-run", action="store_true", help="Show how many would be deleted without deleting")

    def handle(self, *args, **opts):
        days = opts["days"]
        cutoff = timezone.now() - timedelta(days=days)
        qs = WebhookEvent.objects.filter(received_at__lt=cutoff)
        count = qs.count()
        if opts["dry_run"]:
            self.stdout.write(self.style.WARNING(f"[Dry-run] Would delete {count} events older than {days} days"))
            return
        deleted = qs.delete()[0]
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} WebhookEvent rows older than {days} days"))
