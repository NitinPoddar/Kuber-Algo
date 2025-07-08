# -*- coding: utf-8 -*-
"""
Created on Fri Jun 20 23:09:14 2025

@author: Home
"""

from django.core.management.base import BaseCommand
from core.models import VariableCategory, VariableParameter, Variable

class Command(BaseCommand):
    help = 'Seed VariableCategory, VariableParameter, and Variable with standard algo design components'

    def handle(self, *args, **kwargs):
        # 1. Categories
        categories = {
            'Technical Indicators': VariableCategory.objects.get_or_create(name='Technical Indicators')[0],
            'Time Variables': VariableCategory.objects.get_or_create(name='Time Variables')[0],
            'Position Variables': VariableCategory.objects.get_or_create(name='Position Variables')[0],
            'Trade Variables': VariableCategory.objects.get_or_create(name='Trade Variables')[0],
            'User Defined': VariableCategory.objects.get_or_create(name='User Defined')[0],
        }

        # 2. Parameters
        parameters = {
            'symbol': VariableParameter.objects.get_or_create(
                name='symbol',
                defaults={'description': 'Underlying symbol', 'input_type': 'select', 'source_model': 'InstrumentList', 'source_field': 'symbol'}
            )[0],
            'period': VariableParameter.objects.get_or_create(
                name='period',
                defaults={'description': 'Lookback period', 'input_type': 'number', 'default_value': '14'}
            )[0],
            'lag': VariableParameter.objects.get_or_create(
                name='lag',
                defaults={'description': 'Lag in candles', 'input_type': 'number', 'default_value': '1'}
            )[0],
            'multiplier': VariableParameter.objects.get_or_create(
                name='multiplier',
                defaults={'description': 'Multiplier value', 'input_type': 'number', 'default_value': '3'}
            )[0],
            'constant': VariableParameter.objects.get_or_create(
                name='constant',
                defaults={'description': 'Fixed custom value', 'input_type': 'text', 'default_value': '0'}
            )[0],
            'option_type': VariableParameter.objects.get_or_create(
                name='option_type',
                defaults={'description': 'Call or Put option type', 'input_type': 'select', 'default_value': 'CE'}
            )[0],
            'candle_interval': VariableParameter.objects.get_or_create(
                name='candle_interval',
                defaults={'description': 'Candle interval (e.g. 1min, 5min)', 'input_type': 'select', 'default_value': '5min', 'source_model': 'CandleInterval', 'source_field': 'name'}
            )[0],
        }

        # 3. Variables
        Variable.objects.all().delete()  # Optional: Clear existing for clean load
        Variable.objects.bulk_create([
            # Technical Indicators
            Variable(name='ema', display_name='EMA', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='sma', display_name='SMA', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='wma', display_name='WMA', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='rsi', display_name='RSI', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='macd', display_name='MACD', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='macd_signal', display_name='MACD Signal', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='macd_hist', display_name='MACD Histogram', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='supertrend', display_name='Supertrend', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='adx', display_name='ADX', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='plus_di', display_name='+DI', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='minus_di', display_name='-DI', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='atr', display_name='ATR', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='bollinger_upper', display_name='Bollinger Upper', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='bollinger_middle', display_name='Bollinger Middle', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='bollinger_lower', display_name='Bollinger Lower', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='cci', display_name='CCI', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='roc', display_name='Rate of Change', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='momentum', display_name='Momentum', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='stochastic_k', display_name='Stochastic %K', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='stochastic_d', display_name='Stochastic %D', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='natr', display_name='Normalized ATR', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='obv', display_name='On-Balance Volume', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='mfi', display_name='Money Flow Index', category=categories['Technical Indicators'], parameter_required=True),
            Variable(name='accum_dist', display_name='Accumulation/Distribution', category=categories['Technical Indicators'], parameter_required=True),

            # Time
            Variable(name='market_open_time', display_name='Market Open Time', category=categories['Time Variables'], parameter_required=False),
            Variable(name='day_of_week', display_name='Day of Week', category=categories['Time Variables'], parameter_required=False),

            # Position
            Variable(name='pnl', display_name='P&L', category=categories['Position Variables'], parameter_required=True),
            Variable(name='unrealised_pnl', display_name='Unrealised P&L', category=categories['Position Variables'], parameter_required=True),

            # Trade
            Variable(name='entry_price', display_name='Entry Price', category=categories['Trade Variables'], parameter_required=True),
            Variable(name='is_in_position', display_name='Is In Position', category=categories['Trade Variables'], parameter_required=True),

            # User Defined
            Variable(name='alpha', display_name='Alpha', category=categories['User Defined'], parameter_required=True),
            Variable(name='beta', display_name='Beta', category=categories['User Defined'], parameter_required=True),
        ])

        # 4. Assign Parameters to Variables
        def assign(var_name, param_names):
            var = Variable.objects.get(name=var_name)
            for pname in param_names:
                var.parameters.add(parameters[pname])

        # Assign parameters to technical indicators
        assign('ema', ['symbol', 'period', 'lag', 'candle_interval'])
        assign('sma', ['symbol', 'period', 'candle_interval'])
        assign('wma', ['symbol', 'period', 'candle_interval'])
        assign('rsi', ['symbol', 'period', 'candle_interval'])
        assign('macd', ['symbol', 'candle_interval'])
        assign('macd_signal', ['symbol', 'candle_interval'])
        assign('macd_hist', ['symbol', 'candle_interval'])
        assign('supertrend', ['symbol', 'period', 'multiplier', 'candle_interval'])
        assign('adx', ['symbol', 'period', 'candle_interval'])
        assign('plus_di', ['symbol', 'period', 'candle_interval'])
        assign('minus_di', ['symbol', 'period', 'candle_interval'])
        assign('atr', ['symbol', 'period', 'candle_interval'])
        assign('bollinger_upper', ['symbol', 'period', 'candle_interval'])
        assign('bollinger_middle', ['symbol', 'period', 'candle_interval'])
        assign('bollinger_lower', ['symbol', 'period', 'candle_interval'])
        assign('cci', ['symbol', 'period', 'candle_interval'])
        assign('roc', ['symbol', 'period', 'candle_interval'])
        assign('momentum', ['symbol', 'period', 'candle_interval'])
        assign('stochastic_k', ['symbol', 'period', 'candle_interval'])
        assign('stochastic_d', ['symbol', 'period', 'candle_interval'])
        assign('natr', ['symbol', 'period', 'candle_interval'])
        assign('obv', ['symbol', 'candle_interval'])
        assign('mfi', ['symbol', 'period', 'candle_interval'])
        assign('accum_dist', ['symbol', 'candle_interval'])

        # Assign other variables
        assign('pnl', ['symbol'])
        assign('unrealised_pnl', ['symbol'])
        assign('entry_price', ['symbol'])
        assign('is_in_position', ['symbol'])
        assign('alpha', ['constant'])
        assign('beta', ['constant'])

        self.stdout.write(self.style.SUCCESS('✅ Variable system seeded successfully with all technical indicators and candle intervals.'))
