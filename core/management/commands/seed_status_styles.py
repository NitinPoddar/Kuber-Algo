# -*- coding: utf-8 -*-
"""
Created on Sun Aug 10 13:58:48 2025

@author: Home
"""

# core/management/commands/seed_status_styles.py
from django.core.management.base import BaseCommand
from core.models import AlgoStatusStyle

DEFAULTS = [
  dict(key='unregistered', label='Unregistered', bulma_bg_class='has-background-light',   dot_hex='#dcdcdc', order=10),
  dict(key='paper_ready',  label='Paper Ready',  bulma_bg_class='has-background-link-light',   dot_hex='#cfe8ff', order=20),
  dict(key='live_ready',   label='Live Ready',   bulma_bg_class='has-background-warning-light',dot_hex='#fff3cd', order=30),
  dict(key='running',      label='Running',      bulma_bg_class='has-background-success-light',dot_hex='#d4edda', order=40),
  dict(key='paused',       label='Paused',       bulma_bg_class='has-background-warning-light',dot_hex='#ffeeba', order=50),
  dict(key='stopped',      label='Stopped',      bulma_bg_class='has-background-light',   dot_hex='#eaeaea', order=60),
  dict(key='error',        label='Error',        bulma_bg_class='has-background-danger-light', dot_hex='#f8d7da', order=70),
]

class Command(BaseCommand):
    help = "Seed global AlgoStatusStyle defaults"

    def handle(self, *args, **kwargs):
        created = 0
        for row in DEFAULTS:
            obj, was_created = AlgoStatusStyle.objects.get_or_create(user=None, key=row['key'], defaults=row)
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} styles (global)."))
