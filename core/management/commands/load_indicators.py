from django.core.management.base import BaseCommand
from core.models import TechnicalIndicator

class Command(BaseCommand):
    help = 'Load default technical indicators'

    def handle(self, *args, **kwargs):
        default_indicators = [
            {
                "name": "supertrend",
                "display_name": "Supertrend",
                "function_code": "supertrend(close, period=10, multiplier=3)",
                "default_params": {"period": 10, "multiplier": 3},
                "description": "Trend indicator using ATR"
            },
            {
                "name": "rsi",
                "display_name": "RSI",
                "function_code": "rsi(close, period=14)",
                "default_params": {"period": 14},
                "description": "Relative Strength Index"
            },
            {
                "name": "highest_high",
                "display_name": "Highest High",
                "function_code": "highest(high, period=20)",
                "default_params": {"period": 20},
                "description": "Highest high over last N candles"
            }
        ]

        for item in default_indicators:
            obj, created = TechnicalIndicator.objects.update_or_create(
                name=item['name'],
                defaults=item
            )
            status = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{status}: {item['display_name']}"))
